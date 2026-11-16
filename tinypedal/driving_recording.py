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

"""驾驶记录的文件生命周期：持续写 CSV，结束后生成元数据和分析包。"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import os
import tempfile
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from .adapter._reader import APIDataReader
from .constant import API, APP
from .telemetry_sample import CHANNELS, sample_reader

logger = logging.getLogger(__name__)

RECORD_FIELDS = {
    "sample_index": ("index", "从 0 开始的已保存采样序号"),
    "recorded_utc": ("UTC", "本机接收时间，ISO 8601"),
    "elapsed_s": ("s", "本轮开始后的单调时钟时间，包含暂停及断流"),
    "source_time_s": ("s", "游戏提供的源时钟，不应直接跨重置求差"),
    "source_generation": ("index", "适配器重置计数"),
    "segment_index": ("index", "不连续记录段，从 0 开始"),
    "lap_segment": ("index", "本轮观察到的圈段，从 0 开始；LFS 为距离回绕推断"),
    "break_before": ("bool", "此前存在暂停、重置或超过 250ms 的采样间隔"),
}
FIELDS = (*RECORD_FIELDS, *CHANNELS)
MAX_SETUP_BYTES = 16 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: Path, value: dict):
    """同目录临时文件写完后替换，失败时保留之前的 JSON。"""
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path.parent),
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temp = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(str(temp), str(path))
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


@dataclass(frozen=True)
class RecordingStatus:
    active: bool = False
    folder: str = ""
    samples: int = 0
    reason: str = ""
    error: str = ""


class DrivingRecorder:
    """由应用创建，记录线程拥有输出文件；API 停止前由调用方结束记录。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._thread = None
        self._status = RecordingStatus()
        self._stop_reason = ""

    @property
    def status(self) -> RecordingStatus:
        with self._lock:
            return self._status

    def _update(self, **changes):
        with self._lock:
            self._status = replace(self._status, **changes)

    @staticmethod
    def _context(read: APIDataReader):
        return (read.session.track_name(), read.vehicle.vehicle_model(),
                read.vehicle.driver_name(), read.vehicle.player_index())

    def start(self, read: APIDataReader, game: str, folder: str, driver: str,
              comparison: str, notes: str, interval_ms: int = 20, setup_file: str = "",
              api_config: dict | None = None):
        """显式开始一轮记录；原始调教文件只读，可选复制到独立输出目录。"""
        if self._thread is not None and self._thread.is_alive():
            raise ValueError("A recording is already running")
        if not driver.strip():
            raise ValueError("Please enter a driver name")
        if not folder.strip():
            raise ValueError("Please choose an output folder")
        if not 10 <= interval_ms <= 1000:
            raise ValueError("Sampling interval must be 10..1000 ms")
        if sample_reader(read, game) is None:
            raise ValueError("No active telemetry. Start driving and check the API settings.")
        context = self._context(read)
        setup_data = None
        if setup_file:
            setup_path = Path(setup_file)
            if setup_path.suffix.lower() not in (".set", ".svm"):
                raise ValueError("Select a .set or .svm setup file")
            with setup_path.open("rb") as stream:
                setup_data = stream.read(MAX_SETUP_BYTES + 1)
            if len(setup_data) > MAX_SETUP_BYTES:
                raise ValueError("Setup file must be smaller than 16 MiB")
        parent = Path(folder).expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bundle = parent / ("drive_" + stamp + "_" + uuid.uuid4().hex[:8])
        bundle.mkdir()
        metadata = {
            "schema_version": 1, "app_version": APP.VERSION, "game": game,
            "api_version": read.state.version(),
            "started_utc": utc_now(), "ended_utc": None, "status": "recording",
            "driver": driver.strip(), "comparison_label": comparison.strip(), "notes": notes,
            "track": context[0], "vehicle": context[1], "game_driver": context[2],
            "player_index": context[3], "requested_interval_ms": interval_ms,
            "session_type": read.session.session_type() if game != API.NAME_LFS else None,
            "session_identifier_at_start": list(read.session.identifier()) if game != API.NAME_LFS else None,
            "wheel_order": ["fl", "fr", "rl", "rr"],
            "lap_source": "distance_wrap_inferred" if game == API.NAME_LFS else "game_lap_counter",
            "fields": {name: {"unit": unit, "description": description}
                       for name, (unit, description) in {**RECORD_FIELDS, **CHANNELS}.items()},
            "capture_consistency": "atomic_physics_snapshot" if read.capture else "sequential_adapter_reads",
            "setup_file": None,
            "manual_lfs_settings": {
                key: api_config[key] for key in
                ("track_name", "driver_name", "track_length", "steering_range", "engine_rpm_max", "fuel_capacity")
                if game == API.NAME_LFS and api_config is not None and key in api_config
            },
        }
        if setup_data is not None:
            setup_name = "setup" + Path(setup_file).suffix.lower()
            (bundle / setup_name).write_bytes(setup_data)
            metadata["setup_file"] = {
                "name": setup_name, "sha256": hashlib.sha256(setup_data).hexdigest(),
                "bytes": len(setup_data),
            }
        save_json(bundle / "metadata.json", metadata)
        (bundle / "README.txt").write_text(BUNDLE_README, encoding="utf-8")
        self._event.clear()
        self._stop_reason = ""
        self._update(active=True, folder=str(bundle), samples=0, reason="", error="")
        self._thread = threading.Thread(
            target=self._record, args=(read, game, bundle, metadata, context, interval_ms / 1000),
            name="Driving recorder", daemon=True)
        try:
            self._thread.start()
        except RuntimeError as error:
            self._thread = None
            metadata.update(status="failed", error=str(error), ended_utc=utc_now())
            self._update(active=False, error=str(error), reason="failed")
            save_json(bundle / "metadata.json", metadata)
            raise

    def stop(self, reason: str = "user_stopped"):
        """等待文件关闭后返回；不持有状态锁等待接收线程。"""
        if self._thread is not None:
            self._stop_reason = reason
            self._event.set()
            self._thread.join()
            self._thread = None

    def _record(self, read, game, bundle, metadata, initial_context, interval):
        started = time.monotonic()
        last_wall = last_source = last_generation = None
        last_distance = last_lap = None
        segment = lap_segment = 0
        count = duplicate_count = 0
        pending_break = True
        inactive = False
        availability = {key: 0 for key in CHANNELS}
        extrema = {}
        reason, error_text = "user_stopped", ""
        last_flush = started
        try:
            with (bundle / "samples.csv").open("w", encoding="utf-8-sig", newline="") as samples, (
                bundle / "events.jsonl"
            ).open("w", encoding="utf-8") as events:
                writer = csv.DictWriter(samples, fieldnames=FIELDS)
                writer.writeheader()

                def event(kind, **details):
                    json.dump({"elapsed_s": time.monotonic() - started, "utc": utc_now(),
                               "type": kind, **details}, events, ensure_ascii=False, allow_nan=False)
                    events.write("\n")
                    events.flush()

                event("started")
                while not self._event.wait(interval):
                    poll_time = time.monotonic()
                    if poll_time - last_flush >= 1:
                        samples.flush()
                        last_flush = poll_time
                    frame = sample_reader(read, game)
                    if frame is None:
                        if not inactive:
                            inactive = True
                            event("telemetry_unavailable")
                        pending_break = True
                        continue
                    context = self._context(read)
                    # 短暂丢失仪表时 LFS 无法确认车型，不据此推断换车。
                    if (context[0] != initial_context[0] or
                        context[2:] != initial_context[2:] or
                        (context[1] != initial_context[1] and context[1] not in ("", "LFS", "Unknown"))):
                        reason = "context_changed"
                        event(reason, track=context[0], vehicle=context[1], driver=context[2])
                        break
                    source = frame.source_time_s
                    if not isinstance(source, (int, float)) or not math.isfinite(source):
                        raise ValueError("Source telemetry clock is invalid")
                    if source == last_source and frame.generation == last_generation:
                        duplicate_count += 1
                        continue
                    now = time.monotonic()
                    if inactive:
                        event("telemetry_resumed")
                        inactive = False
                    broken = (pending_break or last_wall is None or now - last_wall > 0.25 or
                              frame.generation != last_generation or
                              (last_source is not None and (source < last_source or source - last_source > 0.25)))
                    if broken and count:
                        segment += 1
                        event("discontinuity", segment_index=segment)
                    values = {key: self._clean(frame.channels.get(key)) for key in CHANNELS}
                    distance, lap = values["lap_distance_m"], values["lap_completed"]
                    if count and broken:
                        lap_segment += 1
                    elif count:
                        if lap is not None and last_lap is not None and lap != last_lap:
                            lap_segment += 1
                        elif game == API.NAME_LFS and not broken and distance is not None and last_distance is not None:
                            length = metadata["manual_lfs_settings"].get("track_length", 0)
                            if ((length > 0 and last_distance > length * 0.8 and distance < length * 0.2) or
                                (length <= 0 and last_distance > 100 and distance < 50)):
                                lap_segment += 1
                                event("inferred_lap_boundary", lap_segment=lap_segment)
                    row = {
                        "sample_index": count, "recorded_utc": utc_now(), "elapsed_s": now - started,
                        "source_time_s": source, "source_generation": frame.generation,
                        "segment_index": segment, "lap_segment": lap_segment, "break_before": broken,
                        **values,
                    }
                    writer.writerow(row)
                    count += 1
                    for key, value in values.items():
                        if value is not None:
                            availability[key] += 1
                            low, high = extrema.get(key, (value, value))
                            extrema[key] = (min(low, value), max(high, value))
                    self._update(samples=count)
                    last_wall, last_source, last_generation = now, source, frame.generation
                    last_distance, last_lap = distance, lap
                    pending_break = False
                if self._event.is_set():
                    reason = self._stop_reason or "user_stopped"
                event("stopped", reason=reason)
        except Exception as error:
            reason, error_text = "failed", str(error)
            logger.exception("Driving recording failed; partial files kept in %s", bundle)
        finally:
            metadata.update(ended_utc=utc_now(), status="failed" if error_text else "completed",
                            stop_reason=reason, error=error_text, sample_count=count,
                            elapsed_s=time.monotonic() - started)
            try:
                save_json(bundle / "summary.json", {
                    "sample_count": count, "duplicate_polls_skipped": duplicate_count,
                    "segment_count": segment + 1 if count else 0,
                    "observed_lap_segments": lap_segment + 1 if count else 0,
                    "available_sample_counts": availability,
                    "ranges": {key: {"min": pair[0], "max": pair[1]} for key, pair in extrema.items()},
                })
                save_json(bundle / "metadata.json", metadata)
            except OSError as error:
                error_text = (error_text + "; " if error_text else "") + str(error)
                reason = "failed"
                logger.exception("Driving recording metadata could not be finalized")
            self._update(active=False, samples=count, reason=reason, error=error_text)

    @staticmethod
    def _clean(value):
        if value is None or (isinstance(value, (int, float)) and math.isfinite(value)):
            return value
        return None

    def export_zip(self, filename: str) -> str:
        """仅打包已结束的独立记录目录，不遍历任意用户目录。"""
        status = self.status
        if status.active or not status.folder:
            raise ValueError("Stop a recording before exporting")
        bundle = Path(status.folder)
        files = [path for path in bundle.iterdir() if path.is_file() and path.suffix.lower() in
                 (".csv", ".json", ".jsonl", ".txt", ".set", ".svm")]
        destination = Path(filename).resolve()
        if destination.suffix.lower() != ".zip":
            raise ValueError("Use a .zip filename")
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=str(destination.parent), suffix=".tmp", delete=False) as stream:
                temp = Path(stream.name)
            with zipfile.ZipFile(str(temp), "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in files:
                    archive.write(str(path), path.name)
            os.replace(str(temp), str(destination))
        finally:
            if temp is not None and temp.exists():
                temp.unlink()
        return str(destination)


BUNDLE_README = """TinyPedal 驾驶数据分析包 / Driving telemetry

samples.csv：UTF-8 BOM，固定英文字段、SI 单位或字段后缀所示单位。
metadata.json：驾驶者、游戏、赛道、车型、备注、可选调教文件摘要、字段解释与采样设置。
events.jsonl：开始、数据不可用/恢复、中断、LFS 推断圈界及停止原因。
summary.json：样本数、跳过的重复轮询数、有效值数量和范围。
setup.set / setup.svm：仅当用户选择时复制；原文件保持原样。

CSV 空值代表未提供、失效或非有限数值，数值 0 仍是有效值。
时间以 recorded_utc（UTC）和 elapsed_s（本机单调时钟）为准。
source_time_s 是游戏源时钟；暂停、重置及回放可能改变其含义。
break_before=True 或 segment_index 改变表示不连续，不能跨段插值或计算导数。
没有零填充、插值、平滑或自动评分；记录频率不代表设备/游戏实际报告率。
默认请求间隔 20ms，重复的源时间戳跳过，真实间隔请查看相邻行。

lap_segment 只是本次记录的圈段。LFS 没有 InSim 官方计时，
圈界由圈内距离回绕推断，传送、出站和倒车可能造成误判，不能据此确认有效完整圈。
其他游戏使用游戏圈数变化分段。每次记录的首尾圈均可能不完整。
LFS 支持固定 1ff 扩展或旧版 OutSim，其他掩码不会被猜测解码。
raw_* 列保留 LFS 协议轴；air_temperature 是胎内空气温度。
max_torque_at_rpm_nm 是最大可用扭矩，不是实际发动机扭矩。
各游戏坐标、转向和离合输入语义可能不同，优先比较相同游戏/车辆/赛道。
metadata 的人工设置和备注不是游戏自动测量值。

比较时保持游戏版本、车辆、赛道布局、天气、燃油和轮胎状态一致。
每次只改变一个调教参数，在 comparison_label 和 notes 中记录变化，
沿相同圈内距离对齐完整圈，跳过有中断、出入站和无效圈。
可将两份 ZIP 一起交给分析者；具体调教建议还需要当前设置、
轮胎状态、车辆和赛道信息，以及想改善的驾驶现象。
"""
