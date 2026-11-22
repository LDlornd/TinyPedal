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

"""通过统一读取接口准备驾驶记录；通道名携带单位，不依赖界面或计算模块。"""

from __future__ import annotations

import math

from .adapter._reader import APIDataReader, TelemetryFrame
from .constant import API, DATA

WHEELS = ("fl", "fr", "rl", "rr")

# 通道顺序同时用于 CSV 列和元数据，新增通道只需在此定义并接好采样。
CHANNELS = {
    "lap_completed": ("lap", "游戏报告的已完成圈数；LFS 来自 InSim"),
    "lap_time_s": ("s", "当前圈用时；LFS 通过 OutSim 过线定位估算"),
    "last_lap_time_s": ("s", "游戏上一圈用时；LFS 来自匹配过线的 InSim，负值表示无效圈"),
    "lap_distance_m": ("m", "圈内距离"),
    "lap_progress": ("fraction", "圈内进度，0..1"),
    "speed_m_s": ("m/s", "速度大小"),
    "gear": ("gear", "-1 倒挡，0 空挡，1 一挡"),
    "rpm": ("rpm", "发动机转速"),
    "throttle_raw": ("fraction", "油门输入，0..1"),
    "brake_raw": ("fraction", "刹车输入，0..1"),
    "clutch_raw": ("fraction", "离合输入，0..1，沿用各适配器语义"),
    "steering": ("fraction", "转向输入，沿用游戏适配器的正负方向"),
    "fuel_l": ("L", "燃油体积；LFS 仅在人工设置油箱容量后换算"),
    "fuel_fraction": ("fraction", "剩余燃油比例"),
    "brake_bias_front": ("fraction", "前刹车平衡；LFS 未提供"),
    "water_temperature_c": ("degC", "发动机水温"),
    "oil_temperature_c": ("degC", "发动机油温"),
    "yaw_rad": ("rad", "适配器航向角"),
    "map_x_m": ("m", "适配器地图横轴坐标"),
    "map_y_m": ("m", "适配器地图纵轴坐标"),
    "height_m": ("m", "世界坐标高度"),
    "accel_lateral_m_s2": ("m/s^2", "适配器横向加速度"),
    "accel_braking_m_s2": ("m/s^2", "适配器纵向加速度，制动方向为正"),
    "accel_vertical_m_s2": ("m/s^2", "适配器垂直加速度"),
    "handbrake": ("fraction", "LFS 扩展 OutSim 手刹输入"),
    "steering_torque_nm": ("N*m", "LFS 原始转向扭矩，不是标准化 FFB"),
    "max_torque_at_rpm_nm": ("N*m", "LFS 当前转速下的最大扭矩，不是实际发动机输出"),
    "indexed_distance_m": ("m", "LFS 原始索引距离"),
    "outsim_time_ms": ("ms", "LFS 原始物理时间戳"),
    "outgauge_time_ms": ("ms", "LFS 配对仪表时间戳"),
    "raw_heading_rad": ("rad", "LFS 原始航向"),
    "raw_pitch_rad": ("rad", "LFS 原始俯仰"),
    "raw_roll_rad": ("rad", "LFS 原始侧倾"),
}
for _axis in ("x", "y", "z"):
    for _field, _unit, _description in (
        ("position", "m", "LFS 原始世界位置"),
        ("velocity", "m_s", "LFS 原始速度分量"),
        ("acceleration", "m_s2", "LFS 原始加速度分量"),
        ("angular_velocity", "rad_s", "LFS 原始角速度分量"),
    ):
        CHANNELS[f"raw_{_field}_{_axis}_{_unit}"] = (
            {"m_s": "m/s", "m_s2": "m/s^2", "rad_s": "rad/s"}.get(_unit, _unit), _description)
for _wheel in WHEELS:
    for _field, _unit, _description in (
        ("suspension", "mm", "悬架压缩量，不是离地高度"),
        ("rotation", "rad_s", "适配器车轮角速度，向前滚动为负"),
        ("load", "n", "垂直轮胎载荷"),
        ("pressure", "kpa", "轮胎压力；LFS 未提供"),
        ("surface_temperature", "c", "胎面平均温度；LFS 未提供"),
        ("brake_temperature", "c", "刹车温度；LFS 未提供"),
        ("slip_angle", "rad", "轮胎滑移角"),
        ("air_temperature", "c", "LFS 胎内空气温度，不是胎面或胎体温度"),
        ("slip_ratio", "fraction", "LFS 原始滑移率"),
        ("slip_fraction", "fraction", "LFS 接地部分滑动比例"),
        ("touching", "bool", "LFS 车轮是否接地"),
        ("steer", "rad", "LFS 单轮实际转角，包含阿克曼及束角"),
        ("force_x", "n", "LFS 单轮横向力"),
        ("force_y", "n", "LFS 单轮纵向力"),
        ("lean", "rad", "LFS 车轮相对路面倾角，不是车身坐标外倾角"),
    ):
        CHANNELS[f"{_field}_{_wheel}_{_unit}"] = (
            {"rad_s": "rad/s", "n": "N", "kpa": "kPa", "c": "degC"}.get(_unit, _unit), _description)


def _number(value, temperature: bool = False):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    if temperature and value <= DATA.ABS_ZERO_CELSIUS:
        return None
    return value


def sample_reader(read: APIDataReader, game: str) -> TelemetryFrame | None:
    """优先使用适配器的完整快照；其余游戏复用现有读取方法。"""
    if read.capture is not None:
        return read.capture()
    if not read.state.active() or read.state.paused() or not read.vehicle.is_driving():
        return None
    values = {
        "lap_completed": read.lap.completed(),
        "lap_time_s": read.timing.current_laptime(),
        "last_lap_time_s": read.timing.last_laptime(),
        "lap_distance_m": read.lap.distance(),
        "lap_progress": read.lap.progress(),
        "speed_m_s": read.vehicle.speed(),
        "gear": read.engine.gear(),
        "rpm": read.engine.rpm(),
        "throttle_raw": read.inputs.throttle_raw(),
        "brake_raw": read.inputs.brake_raw(),
        "clutch_raw": read.inputs.clutch_raw(),
        "steering": read.inputs.steering(),
        "fuel_l": read.engine.fuel(),
        "fuel_fraction": read.engine.fuel_fraction(),
        "brake_bias_front": read.brake.bias_front(),
        "water_temperature_c": read.engine.water_temperature(),
        "oil_temperature_c": read.engine.oil_temperature(),
        "yaw_rad": read.vehicle.orientation_yaw(),
        "map_x_m": read.vehicle.position_lateral(),
        "map_y_m": read.vehicle.position_longitudinal(),
        "height_m": read.vehicle.position_vertical(),
        "accel_lateral_m_s2": read.vehicle.acceleration_lateral(),
        "accel_braking_m_s2": read.vehicle.acceleration_longitudinal(),
        "accel_vertical_m_s2": read.vehicle.acceleration_vertical(),
    }
    for name, unit, wheel_values in (
        ("suspension", "mm", read.wheel.suspension_deflection()),
        ("rotation", "rad_s", read.wheel.rotation()),
        ("load", "n", read.tyre.load()),
        ("pressure", "kpa", read.tyre.pressure()),
        ("surface_temperature", "c", read.tyre.surface_temperature_avg()),
        ("brake_temperature", "c", read.brake.temperature()),
        ("slip_angle", "rad", read.tyre.slip_angle()),
    ):
        for wheel, value in zip(WHEELS, wheel_values):
            values[f"{name}_{wheel}_{unit}"] = value
    if values["last_lap_time_s"] == 0:
        values["last_lap_time_s"] = None
    if read.lap.track_length() <= 0:
        values["lap_progress"] = None
    # ACC 适配器明确不提供轮胎载荷，兼容值 0 不作为真实测量导出。
    if game == API.NAME_ACC:
        for wheel in WHEELS:
            values[f"load_{wheel}_n"] = None
    values = {key: _number(value, "temperature" in key) for key, value in values.items()}
    return TelemetryFrame(read.timing.elapsed(), read.state.resets(), values)
