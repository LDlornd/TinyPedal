#  TinyPedal is an open-source overlay application for racing simulation.
#  Copyright (C) 2022-2026 TinyPedal developers, see contributors.md file
#  SPDX-License-Identifier: GPL-3.0-or-later

"""通过本机 InSim TCP 读取赛道、多车位置及本地驾驶者圈时。"""

from __future__ import annotations

import logging
import math
import re
import select
import socket
import struct
import threading
import time
from dataclasses import dataclass, replace
from typing import Callable

logger = logging.getLogger(__name__)

# InSim 9 起，包头的长度字节表示实际字节数 / 4。
INSIM_VERSION = 9
SUPPORTED_VERSIONS = (9, 10)
INITIALIZE = struct.Struct("<4BHHBBH16s16s")
REQUEST_STATE = bytes((1, 3, 1, 7))  # IS_TINY / TINY_SST
REQUEST_PLAYERS = bytes((1, 3, 1, 14))  # TINY_NPL
KEEP_ALIVE = bytes((1, 3, 0, 0))
RECONNECT_DELAY = 2.0
IO_TIMEOUT = 3.0
POLL_INTERVAL = 0.2
STATE_INTERVAL = 1.0
STATE_TIMEOUT = 5.0
# InSim 的 Interval 是整数毫秒，按 10ms 的步长请求；20ms 对应每秒 50 次。
MCI_INTERVAL_MS = 20
COMP_CAR = struct.Struct("<HH4BiiiHHHh")


@dataclass(frozen=True)
class CarState:
    """InSim 车辆位置，长度为米、朝向为弧度、速度为米每秒。"""

    player_id: int = 0
    driver_name: str = ""
    car: str = ""
    in_pits: bool = False
    in_garage: bool = False
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    heading: float = 0.0
    speed: float = 0.0
    received: float = 0.0


@dataclass(frozen=True)
class RaceState:
    """本地人类驾驶者的赛事状态；重置编号用于丢弃旧圈采样。"""

    generation: int = 0
    player_id: int = 0
    completed: int = 0
    lap_serial: int = 0
    last_laptime: float = 0.0
    best_laptime: float = 0.0
    sector_index: int = 0
    split_time: float = 0.0
    last_sector: float = 0.0
    in_pits: bool = False


def parse_track(packet: bytes) -> str:
    """读取 IS_STA.Track；游戏入口界面不沿用之前的赛道。"""
    if len(packet) != 28 or packet[:2] != bytes((7, 5)):
        raise ValueError("Expected 28 byte InSim IS_STA packet")
    flags = struct.unpack_from("<H", packet, 8)[0]
    track = packet[20:26].split(b"\0", 1)[0].decode("ascii")
    if track and re.fullmatch(r"[A-Z]{2}[1-9][0-9]?[RXY]?", track) is None:
        raise ValueError("Invalid InSim track code")
    return "" if flags & 256 else track  # ISS_FRONT_END


class TrackReader:
    """拥有 TCP 连接和线程，将赛道或连接失败交给调用方发布。"""

    def __init__(self, publish: Callable[[str, str], None],
                 publish_race: Callable[[RaceState], None],
                 publish_cars: Callable[[tuple[CarState, ...]], None]):
        self._publish = publish
        self._publish_race = publish_race
        self._publish_cars = publish_cars
        self._cars: dict[int, CarState] = {}
        self._pending_cars: dict[int, CarState] | None = None
        self._race = RaceState()
        self._stop = threading.Event()
        self._thread = None

    def start(self, port: int):
        self.stop()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._receive, args=(port,), name="LFS InSim", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _receive(self, port: int):
        last_error = ""
        while not self._stop.is_set():
            phase = "connect"
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
                    # 连接和发送使用独立时限，接收轮询另由 select 控制。
                    connection.settimeout(IO_TIMEOUT)
                    connection.connect(("127.0.0.1", port))
                    phase = "initialize"
                    connection.sendall(INITIALIZE.pack(
                        INITIALIZE.size // 4, 1, 1, 0, 0, 4 | 32,
                        INSIM_VERSION, 0, MCI_INTERVAL_MS, b"", b"TinyPedal"))
                    phase = "read state"
                    self._read_connection(connection)
            except (OSError, ValueError, struct.error) as error:
                message = f"{phase}: {error}"
                self._reset_cars()
                self._publish("", message)
                if not self._stop.is_set() and message != last_error:
                    logger.warning("LFS InSim: %s", message)
                last_error = message
            if self._stop.wait(RECONNECT_DELAY):
                break

    def _read_connection(self, connection: socket.socket):
        buffer = bytearray()
        last_state = time.monotonic()
        next_request = 0.0
        last_track = None
        self._publish("", "waiting for track")
        self._reset_cars()
        self._reset_race()
        connection.sendall(REQUEST_PLAYERS)
        while not self._stop.is_set():
            now = time.monotonic()
            if now - last_state > STATE_TIMEOUT:
                raise ValueError("InSim state timed out")
            if now >= next_request:
                connection.sendall(REQUEST_STATE)
                next_request = now + STATE_INTERVAL
            ready, _, _ = select.select((connection,), (), (), POLL_INTERVAL)
            if not ready:
                continue
            data = connection.recv(4096)
            if not data:
                raise ConnectionError("InSim connection closed")
            buffer.extend(data)
            while len(buffer) >= 4:
                size = buffer[0] * 4
                if size < 4:
                    raise ValueError("Invalid InSim packet size")
                if len(buffer) < size:
                    break
                packet = bytes(buffer[:size])
                del buffer[:size]
                if packet[1] == 2:  # IS_VER
                    if size != 20:
                        raise ValueError(f"Invalid IS_VER size: {size} bytes (expected 20)")
                    reported_version = packet[18]
                    # 此处使用的赛道和圈时报文在 InSim 9/10 中格式相同。
                    if reported_version not in SUPPORTED_VERSIONS:
                        raise ValueError(
                            f"Unsupported InSim version: {reported_version} (expected 9 or 10)")
                    game_version = packet[4:12].split(b"\0", 1)[0].decode("ascii", errors="replace")
                    logger.info("LFS InSim connected: LFS %s, requested %s, reported %s",
                                game_version, INSIM_VERSION, reported_version)
                elif packet[1] == 3 and packet[3] == 0:  # TINY_NONE
                    connection.sendall(KEEP_ALIVE)
                elif packet[1] == 5:  # IS_STA
                    track = parse_track(packet)
                    last_state = time.monotonic()
                    if track != last_track:
                        last_track = track
                        self._reset_cars()
                        self._reset_race()
                        connection.sendall(REQUEST_PLAYERS)
                    self._publish(track, "" if track else "waiting for track")
                else:
                    self._read_race(packet)

    def _reset_race(self, player_id: int = 0, in_pits: bool = False):
        self._race = RaceState(generation=self._race.generation + 1,
                               player_id=player_id, in_pits=in_pits)
        self._publish_race(self._race)

    def _reset_cars(self):
        self._cars.clear()
        self._pending_cars = None
        self._publish_cars(())

    def _read_cars(self, packet: bytes):
        """按 PLID 合并车辆信息；多包 MCI 收齐后一次发布，避免丢掉第 17 辆车。"""
        kind = packet[1]
        player_id = packet[3]
        if kind == 3 and packet[3] in (11, 12):
            self._reset_cars()
            return
        if kind == 17 and packet[2] == 0:
            self._pending_cars = None
            self._cars = {key: replace(car, received=0.0) for key, car in self._cars.items()}
            self._publish_cars(())
            return
        if kind == 21:  # IS_NPL
            raw_car = packet[40:44]
            car = raw_car.rstrip(b"\0").decode("ascii", errors="replace")
            if re.fullmatch(r"[A-Z0-9]{3}", car) is None:
                car = format(int.from_bytes(raw_car, "little"), "06x") if any(raw_car) else ""
            # LFS 名称允许代码页和颜色标记；这里只去掉颜色，无法解码的字节保留替代符。
            name = packet[8:32].split(b"\0", 1)[0].decode("cp1252", errors="replace")
            name = re.sub(r"\^[0-9]", "", name)
            self._cars[player_id] = CarState(
                player_id=player_id, driver_name=name, car=car,
                in_pits=bool(struct.unpack_from("<H", packet, 6)[0] & 256))
            if self._pending_cars is not None:
                self._pending_cars.pop(player_id, None)
        elif kind in (22, 23, 41):  # pits, spectate, reset: wait for a new position
            if kind == 23:
                self._cars.pop(player_id, None)
            elif player_id in self._cars:
                car = self._cars[player_id]
                self._cars[player_id] = replace(
                    car, received=0.0, in_garage=kind == 22 or car.in_garage)
            if self._pending_cars is not None:
                self._pending_cars.pop(player_id, None)
        elif kind == 28 and player_id in self._cars:
            self._cars[player_id] = replace(self._cars[player_id], in_pits=packet[4] != 0)
        elif kind == 33 and player_id in self._cars:
            flags = struct.unpack_from("<H", packet, 4)[0]
            self._cars[player_id] = replace(self._cars[player_id], in_pits=bool(flags & 256))
        elif kind == 38:  # IS_MCI
            count = packet[3]
            if count > 16 or len(packet) != 4 + count * COMP_CAR.size:
                raise ValueError("Invalid InSim MCI packet size")
            if not count:
                self._pending_cars = None
                self._cars = {key: replace(car, received=0.0) for key, car in self._cars.items()}
                self._publish_cars(())
                return
            now = time.monotonic()
            for fields in COMP_CAR.iter_unpack(packet[4:]):
                _, _, player_id, _, info, _, x, y, z, speed, _, heading, _ = fields
                if info & 64:  # CCI_FIRST: start a complete set, possibly spanning packets
                    self._pending_cars = {}
                if self._pending_cars is None:
                    continue
                car = self._cars.get(player_id, CarState(player_id=player_id))
                if not info & 32 and not car.in_garage:
                    self._pending_cars[player_id] = replace(
                        car, position=(x / 65536, y / 65536, z / 65536),
                        speed=speed * 100 / 32768, heading=heading * math.tau / 65536,
                        received=now)
                if info & 128:  # CCI_LAST
                    self._cars = {key: replace(car, received=0.0) for key, car in self._cars.items()}
                    self._cars.update(self._pending_cars)
                    self._publish_cars(tuple(self._pending_cars.values()))
                    self._pending_cars = None
            return
        else:
            return
        self._publish_cars(tuple(car for car in self._cars.values() if car.received))

    def _read_race(self, packet: bytes):
        """只处理本地人类车辆，避免 AI 或远端车辆的成绩混入本车。"""
        kind = packet[1]
        sizes = {17: 28, 21: 76, 22: 4, 23: 4, 24: 20, 25: 16, 28: 8, 33: 8, 41: 4}
        if kind in sizes and len(packet) != sizes[kind]:
            raise ValueError(f"Invalid InSim race packet {kind}: {len(packet)} bytes")
        self._read_cars(packet)
        if kind == 3 and packet[3] in (11, 12):  # TINY_REN / TINY_CLR
            self._reset_race()
        elif kind == 17 and packet[2] == 0:  # IS_RST, unsolicited race restart
            self._reset_race(self._race.player_id)
        elif kind == 21 and not packet[5] & 6:  # IS_NPL: neither AI nor remote
            in_pits = bool(struct.unpack_from("<H", packet, 6)[0] & 256)
            if packet[3] != self._race.player_id or packet[2] == 0:
                self._reset_race(packet[3], in_pits)
        elif self._race.player_id and packet[3] == self._race.player_id:
            race = self._race
            if kind in (22, 23, 41):  # pits, spectate, reset car
                self._reset_race(0 if kind == 23 else race.player_id, kind == 22)
                return
            if kind == 24:  # IS_LAP: registered timing, not HLVC certification
                laptime = struct.unpack_from("<I", packet, 4)[0] / 1000
                completed, flags = struct.unpack_from("<HH", packet, 12)
                if laptime <= 0:
                    return
                best = min(race.best_laptime, laptime) if race.best_laptime else laptime
                race = replace(race, completed=completed, lap_serial=race.lap_serial + 1,
                               last_laptime=laptime, best_laptime=best, sector_index=0,
                               last_sector=max(0.0, laptime - race.split_time),
                               split_time=0.0, in_pits=bool(flags & 256))
            elif kind == 25:  # IS_SPX, cumulative time at checkpoint
                # TinyPedal 的通用接口只有三段，多出的计时点合并到最后一段。
                if not 1 <= packet[12] <= 2:
                    return
                split_time = struct.unpack_from("<I", packet, 4)[0] / 1000
                race = replace(race, sector_index=packet[12],
                               last_sector=max(0.0, split_time - race.split_time),
                               split_time=split_time)
            elif kind == 33:  # IS_PFL
                race = replace(race, in_pits=bool(struct.unpack_from("<H", packet, 4)[0] & 256))
            elif kind == 28:  # IS_PLA, zero means leaving pit lane
                race = replace(race, in_pits=packet[4] != 0)
            else:
                return
            self._race = race
            self._publish_race(race)
