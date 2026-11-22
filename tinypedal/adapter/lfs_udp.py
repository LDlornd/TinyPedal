#  TinyPedal is an open-source overlay application for racing simulation.
#  Copyright (C) 2022-2026 TinyPedal developers, see contributors.md file
#
#  This file is part of TinyPedal.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""只读 LFS 遥测：解码 UDP 数据包，并合并 InSim 赛道状态。"""

from __future__ import annotations

import logging
import math
import select
import socket
import struct
import threading
import time
from dataclasses import dataclass

from .lfs_insim import RaceState, TrackReader

logger = logging.getLogger(__name__)

LEGACY_SIM = struct.Struct("<I12f3i")
MAIN = struct.Struct("<12f3i")
WHEEL = struct.Struct("<7f4B2f")
GAUGE = struct.Struct("<I4sHBB7fII3f16s16s")
STOCK_CARS = frozenset((
    "UF1", "XFG", "XRG", "LX4", "LX6", "RB4", "FXO", "XRT", "RAC", "FZ5",
    "UFR", "XFR", "FXR", "XRR", "FZR", "MRT", "FBM", "FOX", "FO8", "BF1",
))


@dataclass(frozen=True)
class Wheel:
    """单轮数据，单位保持协议原值。"""

    suspension_m: float
    steer_rad: float
    force_x_n: float
    force_y_n: float
    load_n: float
    rotation_rad_s: float
    lean_rad: float
    air_temperature_c: int
    slip_fraction_byte: int
    touching: int
    spare: int
    slip_ratio: float
    tan_slip_angle: float


@dataclass(frozen=True)
class Physics:
    time_ms: int = 0
    angular_velocity: tuple = (0.0, 0.0, 0.0)
    heading: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    acceleration: tuple = (0.0, 0.0, 0.0)
    velocity: tuple = (0.0, 0.0, 0.0)
    position: tuple = (0.0, 0.0, 0.0)
    inputs: tuple | None = None
    gear: int | None = None
    engine_rad_s: float | None = None
    max_torque_nm: float | None = None
    lap_distance_m: float | None = None
    indexed_distance_m: float | None = None
    wheels: tuple[Wheel, ...] = ()
    steering_torque_nm: float | None = None
    packet_id: int | None = None


@dataclass(frozen=True)
class Dashboard:
    time_ms: int = 0
    car: str = ""
    flags: int = 0
    gear: int = 1
    player_id: int = 0
    speed_m_s: float = 0.0
    rpm: float = 0.0
    turbo_bar: float = 0.0
    water_c: float = 0.0
    fuel_fraction: float = 0.0
    oil_pressure_bar: float = 0.0
    oil_c: float = 0.0
    dash_lights: int = 0
    show_lights: int = 0
    throttle: float = 0.0
    brake: float = 0.0
    clutch: float = 0.0
    packet_id: int | None = None


@dataclass(frozen=True)
class Snapshot:
    physics: Physics | None
    dashboard: Dashboard | None
    generation: int
    received: float
    track_name: str
    track_error: str
    race: RaceState
    current_laptime: float
    last_laptime: float
    timed_laps: int
    timing_ready: bool
    track_length: float


def _finite(values):
    if not all(math.isfinite(value) for value in values):
        raise ValueError("LFS packet contains non-finite numbers")


def parse_physics(data: bytes) -> Physics:
    """支持旧格式 64/68 字节，以及固定 1ff 扩展格式 280 字节。"""
    extended = len(data) == 280
    if not extended and len(data) not in (64, 68):
        raise ValueError("Expected OutSim Opts 0 or 1ff (64/68/280 bytes)")
    if extended:
        packet_id, stamp = struct.unpack_from("<iI", data, 4)
        values = MAIN.unpack_from(data, 12)
    else:
        stamp, *values = LEGACY_SIM.unpack_from(data)
        packet_id = struct.unpack_from("<i", data, 64)[0] if len(data) == 68 else None
    _finite(values[:12])
    extra = {}
    if extended:
        inputs = struct.unpack_from("<5f", data, 72)
        gear, engine, torque = struct.unpack_from("<B3xff", data, 92)
        distance, indexed = struct.unpack_from("<2f", data, 104)
        wheels = tuple(Wheel(*WHEEL.unpack_from(data, 112 + index * 40)) for index in (2, 3, 0, 1))
        steering_torque = struct.unpack_from("<f", data, 272)[0]
        _finite((*inputs, engine, torque, distance, indexed, steering_torque))
        if any(value < -0.001 or value > 1.001 for value in (inputs[0], inputs[1], inputs[3], inputs[4])):
            raise ValueError("LFS pedal input outside 0..1")
        if not -1.001 <= inputs[2] <= 1.001:
            raise ValueError("LFS steering input outside -1..1")
        for wheel in wheels:
            _finite((wheel.suspension_m, wheel.steer_rad, wheel.force_x_n, wheel.force_y_n,
                     wheel.load_n, wheel.rotation_rad_s, wheel.lean_rad,
                     wheel.slip_ratio, wheel.tan_slip_angle))
            if wheel.touching not in (0, 1):
                raise ValueError("Invalid LFS wheel contact state")
        extra = dict(inputs=inputs, gear=gear - 1, engine_rad_s=engine,
                     max_torque_nm=torque, lap_distance_m=distance, indexed_distance_m=indexed,
                     wheels=wheels, steering_torque_nm=steering_torque)
    return Physics(
        time_ms=stamp, angular_velocity=tuple(values[:3]),
        heading=values[3], pitch=values[4], roll=values[5],
        acceleration=tuple(values[6:9]), velocity=tuple(values[9:12]),
        position=tuple(value / 65536 for value in values[12:15]),
        packet_id=packet_id, **extra,
    )


def parse_dashboard(data: bytes) -> Dashboard:
    """接收 92/96 字节 OutGauge，压缩 MOD ID 转为六位十六进制名称。"""
    if len(data) not in (92, 96):
        raise ValueError("Expected 92 or 96 byte OutGauge packet")
    values = GAUGE.unpack_from(data)
    _finite((*values[5:12], *values[14:17]))
    if any(value < -0.001 or value > 1.001 for value in (values[9], *values[14:17])):
        raise ValueError("LFS fuel/pedal input outside 0..1")
    raw_car = values[1]
    car = raw_car.rstrip(b"\x00").decode("ascii", errors="replace")
    if car not in STOCK_CARS:
        car = format(int.from_bytes(raw_car, "little"), "06x") if any(raw_car) else ""
    return Dashboard(
        values[0], car, *values[2:17],
        packet_id=struct.unpack_from("<i", data, 92)[0] if len(data) == 96 else None,
    )


class Telemetry:
    """管理两个 UDP socket 和 InSim 读取器，持锁发布不可变快照。"""

    def __init__(self):
        self.config = {}
        self.error = ""
        self.rejected_packets = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._sockets = {}
        self._physics = None
        self._dashboard = None
        self._sim_received = 0.0
        self._gauge_received = 0.0
        self._generation = 0
        self._track_name = ""
        self._track_error = "waiting for InSim"
        self._race = RaceState()
        self._lap_start_ms = None
        self._timed_laps = 0
        self._last_laptime = 0.0
        self._crossed_received = -float("inf")
        self._official_received = -float("inf")
        self._track_length = 0.0
        self._insim = TrackReader(self._set_track, self._set_race)

    def setup(self, config: dict):
        """应用现有预设中的端口及人工补充信息，不修改游戏配置。"""
        self.error = ""
        ports = (config["outsim_port"], config["outgauge_port"])
        if any(not isinstance(port, int) or not 1 <= port <= 65535 for port in ports) or ports[0] == ports[1]:
            raise ValueError("LFS UDP ports must be different integers in 1..65535")
        if not math.isfinite(config["connection_timeout"]) or config["connection_timeout"] <= 0:
            raise ValueError("LFS connection timeout must be positive")
        if config["enable_auto_track_name"]:
            port = config["insim_port"]
            if not isinstance(port, int) or not 1 <= port <= 65535:
                raise ValueError("LFS InSim port must be an integer in 1..65535")
        for key in ("track_length", "steering_range", "engine_rpm_max", "fuel_capacity"):
            if not math.isfinite(config[key]) or config[key] < 0:
                raise ValueError("Invalid LFS setting: " + key)
        self.config = config.copy()

    def start(self):
        self.stop()
        if self.error:
            return
        self.rejected_packets = 0
        self._stop.clear()
        try:
            for key in ("outsim_port", "outgauge_port"):
                receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._sockets[receiver] = key
                receiver.bind(("127.0.0.1", self.config[key]))
                receiver.setblocking(False)
        except OSError as error:
            self.error = str(error)
            logger.error("LFS UDP bind failed: %s", error)
            self.stop()
            return
        self._thread = threading.Thread(target=self._receive, name="LFS UDP", daemon=True)
        self._thread.start()
        if self.config["enable_auto_track_name"]:
            self._insim.start(self.config["insim_port"])

    def stop(self):
        self._stop.set()
        self._insim.stop()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        for receiver in self._sockets:
            receiver.close()
        self._sockets.clear()
        with self._lock:
            self._physics = self._dashboard = None
            self._sim_received = self._gauge_received = 0.0
            self._generation += 1
            self._track_name = ""
            self._track_error = "waiting for InSim"
            self._race = RaceState()
            self._reset_timing()
            self._track_length = 0.0

    def _reset_timing(self):
        """调用方须持锁；中断后等待再次过线，不拼接不完整圈。"""
        self._lap_start_ms = None
        self._timed_laps = 0
        self._last_laptime = 0.0
        self._crossed_received = self._official_received = -float("inf")

    def _set_race(self, race: RaceState):
        with self._lock:
            if race.generation != self._race.generation:
                self._reset_timing()
                self._physics = self._dashboard = None
                self._sim_received = self._gauge_received = 0.0
                self._generation += 1
            if race.lap_serial != self._race.lap_serial:
                self._official_received = time.monotonic()
                if abs(self._official_received - self._crossed_received) < 1.0:
                    self._last_laptime = race.last_laptime
            self._race = race


    def _update_timing(self, packet: Physics, now: float):
        """OutSim 过线定位当前圈时，InSim 完圈报文确认上一圈成绩。"""
        previous = self._physics
        if previous is None or packet.indexed_distance_m is None or previous.indexed_distance_m is None:
            return
        delta_ms = (packet.time_ms - previous.time_ms) % 2**32
        distance = packet.indexed_distance_m
        delta_distance = distance - previous.indexed_distance_m
        speed = math.sqrt(sum(value * value for value in packet.velocity))
        movement = math.dist(packet.position, previous.position)
        continuous = delta_ms < 1000 and movement <= max(20.0, speed * delta_ms / 500)
        crossing = previous.indexed_distance_m > 200 and 0 <= distance < 200 and delta_distance < -200
        if crossing and continuous and self._race.player_id:
            # 以当前速度补偿过线至收到样本的时间；精度受 OutSim 采样间隔影响。
            offset_ms = min(delta_ms, distance / speed * 1000) if speed > 1 else 0.0
            self._lap_start_ms = (packet.time_ms - offset_ms) % 2**32
            self._timed_laps += 1
            self._last_laptime = 0.0
            self._crossed_received = now
            if abs(now - self._official_received) < 1.0:
                self._last_laptime = self._race.last_laptime
            self._track_length = previous.indexed_distance_m + max(0.0, speed * delta_ms / 1000 - distance)
        elif not continuous or abs(delta_distance) > 100:
            self._reset_timing()
            self._generation += 1

    def _set_track(self, track_name: str, error: str):
        """换图或断开时丢弃旧快照，读取方统一使用新的赛道身份。"""
        with self._lock:
            if track_name != self._track_name:
                self._track_name = track_name
                self._physics = self._dashboard = None
                self._sim_received = self._gauge_received = 0.0
                self._generation += 1
                self._reset_timing()
                self._track_length = 0.0
                logger.info("LFS track: %s", track_name or "unavailable")
            self._track_error = error

    def snapshot(self) -> Snapshot:
        """过期数据返回 None；仪表与物理时间相差超过 250ms 时不合并。"""
        now = time.monotonic()
        timeout = self.config.get("connection_timeout", 1.0)
        with self._lock:
            physics = self._physics if not self.error and now - self._sim_received < timeout else None
            dashboard = self._dashboard if now - self._gauge_received < timeout else None
            if physics is not None and dashboard is not None:
                skew = (physics.time_ms - dashboard.time_ms + 2**31) % 2**32 - 2**31
                if abs(skew) > 250:
                    dashboard = None
            automatic = self.config.get("enable_auto_track_name", True)
            track_name = self._track_name if automatic else self.config.get("track_name", "").strip()
            track_error = self._track_error if automatic else ""
            timing_ready = physics is not None and self._lap_start_ms is not None
            current_laptime = ((physics.time_ms - self._lap_start_ms) % 2**32) / 1000 if timing_ready else 0.0
            track_length = self.config.get("track_length", 0.0) or self._track_length
            return Snapshot(physics, dashboard, self._generation, self._sim_received,
                            track_name, track_error, self._race, current_laptime,
                            self._last_laptime if timing_ready else 0.0,
                            self._timed_laps, timing_ready, track_length)

    def _receive(self):
        try:
            while not self._stop.is_set():
                ready, _, _ = select.select(tuple(self._sockets), (), (), 0.1)
                for receiver in ready:
                    data, address = receiver.recvfrom(4096)
                    if address[0] != "127.0.0.1":
                        continue
                    sim = self._sockets[receiver] == "outsim_port"
                    try:
                        packet = parse_physics(data) if sim else parse_dashboard(data)
                    except (ValueError, struct.error) as error:
                        self.rejected_packets += 1
                        if self.rejected_packets == 1:
                            logger.warning("Rejected LFS UDP packet: %s", error)
                        continue
                    now = time.monotonic()
                    with self._lock:
                        previous = self._physics if sim else self._dashboard
                        received = self._sim_received if sim else self._gauge_received
                        fresh = now - received < self.config["connection_timeout"]
                        if previous is not None and fresh:
                            delta = (packet.time_ms - previous.time_ms) % 2**32
                            if delta == 0 or delta >= 2**31:
                                continue
                        if sim:
                            if not fresh:
                                self._generation += 1
                                self._reset_timing()
                            else:
                                self._update_timing(packet, now)
                            self._physics, self._sim_received = packet, now
                        else:
                            if (previous is None or packet.player_id != previous.player_id
                                    or packet.car != previous.car):
                                # 首次确认车型或换车后，让参考圈重新使用正确的组合名称。
                                self._generation += 1
                                self._physics = None
                                self._reset_timing()
                            self._dashboard, self._gauge_received = packet, now
        except OSError as error:
            self.error = str(error)
            logger.exception("LFS UDP receive failed")
