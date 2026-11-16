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

"""LFS 本车遥测读取；未提供的通道沿用显示层约定的不可用值。

赛事圈时、排名、刹车温度及轮胎压力不由 OutSim/OutGauge 提供，
不要将显示兼容值用于数据分析；导出直接使用带缺失状态的原始快照。
"""

from __future__ import annotations

import math

from ..constant import DATA
from ..formatter import strip_invalid_char
from . import _reader
from .lfs_udp import Dashboard, Physics, Telemetry

EMPTY_PHYSICS = Physics()
EMPTY_DASHBOARD = Dashboard()


class DataAdapter:
    __slots__ = ("source",)

    def __init__(self, source: Telemetry):
        self.source = source

    @property
    def sim(self):
        return self.source.snapshot().physics or EMPTY_PHYSICS

    @property
    def gauge(self):
        return self.source.snapshot().dashboard or EMPTY_DASHBOARD

    def pedals(self):
        snapshot = self.source.snapshot()
        if snapshot.physics is not None and snapshot.physics.inputs is not None:
            inputs = snapshot.physics.inputs
            return inputs[0], inputs[1], inputs[3]
        gauge = snapshot.dashboard or EMPTY_DASHBOARD
        return gauge.throttle, gauge.brake, gauge.clutch

    def local_velocity(self):
        sim = self.sim
        x, y, z = sim.velocity
        return (x * math.cos(sim.heading) + y * math.sin(sim.heading),
                x * math.sin(sim.heading) - y * math.cos(sim.heading), z)

    def wheel_values(self, field: str, scale: float = 1):
        wheels = self.sim.wheels
        return tuple(getattr(wheel, field) * scale for wheel in wheels) if wheels else DATA.WHEELS_ZERO


class State(_reader.State, DataAdapter):
    __slots__ = ()

    def active(self) -> bool:
        return bool(self.source.config["track_name"]) and self.source.snapshot().physics is not None

    def paused(self) -> bool:
        return not self.active()

    def resets(self) -> int:
        return self.source.snapshot().generation

    def version(self) -> str:
        if self.source.error:
            return "LFS UDP: " + self.source.error
        snapshot = self.source.snapshot()
        if snapshot.physics is None:
            return "LFS UDP: waiting"
        if not self.source.config["track_name"]:
            return "LFS UDP: set track_name in API Options"
        return "OutSim 1ff" if snapshot.physics.inputs is not None else "OutSim legacy"


class Brake(_reader.Brake, DataAdapter):
    __slots__ = ()

    def compound_name(self, index: int | None = None) -> tuple[str, str]:
        return ("",) * 2

    def bias_front(self, index: int | None = None) -> float:
        return 0.0

    def migration(self, index: int | None = None) -> float:
        return 0.0

    def pressure(self, index: int | None = None, scale: float = 1) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def temperature(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.TYRE_AVERAGE_NA

    def wear(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO


class ElectricMotor(_reader.ElectricMotor, DataAdapter):
    __slots__ = ()

    def state(self, index: int | None = None) -> int:
        return 0

    def battery_charge(self, index: int | None = None) -> float:
        return 0.0

    def rpm(self, index: int | None = None) -> float:
        return 0.0

    def torque(self, index: int | None = None) -> float:
        return 0.0

    def motor_temperature(self, index: int | None = None) -> float:
        return DATA.ABS_ZERO_CELSIUS

    def water_temperature(self, index: int | None = None) -> float:
        return DATA.ABS_ZERO_CELSIUS

    def regeneration_level(self, index: int | None = None) -> float:
        return 0.0


class Engine(_reader.Engine, DataAdapter):
    __slots__ = ()

    def gear(self, index: int | None = None) -> int:
        return self.sim.gear if self.sim.gear is not None else self.gauge.gear - 1

    def gear_max(self, index: int | None = None) -> int:
        return 0

    def rpm(self, index: int | None = None) -> float:
        return self.sim.engine_rad_s * 30 / math.pi if self.sim.engine_rad_s is not None else self.gauge.rpm

    def rpm_max(self, index: int | None = None) -> float:
        return self.source.config["engine_rpm_max"]

    def torque(self, index: int | None = None) -> float:
        return 0.0

    def turbo(self, index: int | None = None) -> float:
        return self.gauge.turbo_bar * 100000

    def oil_temperature(self, index: int | None = None) -> float:
        return self.gauge.oil_c if self.source.snapshot().dashboard is not None else DATA.ABS_ZERO_CELSIUS

    def water_temperature(self, index: int | None = None) -> float:
        return self.gauge.water_c if self.source.snapshot().dashboard is not None else DATA.ABS_ZERO_CELSIUS

    def exhaust_temperature(self, index: int | None = None) -> float:
        return DATA.ABS_ZERO_CELSIUS

    def lift_and_coast_progress(self, index: int | None = None) -> float:
        return 0.0

    def fuel(self, index: int | None = None) -> float:
        return self.gauge.fuel_fraction * self.source.config["fuel_capacity"]

    def fuel_fraction(self, index: int | None = None) -> float:
        return self.gauge.fuel_fraction

    def tank_capacity(self, index: int | None = None) -> float:
        return self.source.config["fuel_capacity"]

    def virtual_energy(self, index: int | None = None) -> float:
        return 0.0

    def max_virtual_energy(self) -> float:
        return 0.0

    def absolute_refill(self) -> float:
        return 0.0


class Inputs(_reader.Inputs, DataAdapter):
    __slots__ = ()

    def throttle(self, index: int | None = None) -> float:
        return self.pedals()[0]

    def throttle_raw(self, index: int | None = None) -> float:
        return self.pedals()[0]

    def brake(self, index: int | None = None) -> float:
        return self.pedals()[1]

    def brake_raw(self, index: int | None = None) -> float:
        return self.pedals()[1]

    def clutch(self, index: int | None = None) -> float:
        return self.pedals()[2]

    def clutch_raw(self, index: int | None = None) -> float:
        return self.pedals()[2]

    def steering(self, index: int | None = None) -> float:
        return self.sim.inputs[2] if self.sim.inputs is not None else 0.0

    def steering_range(self, index: int | None = None) -> float:
        return self.source.config["steering_range"]

    def force_feedback(self) -> float:
        return 0.0


class Lap(_reader.Lap, DataAdapter):
    __slots__ = ()

    def completed(self, index: int | None = None) -> int:
        return 0

    def track_length(self) -> float:
        return self.source.config["track_length"]

    def distance(self, index: int | None = None) -> float:
        return self.sim.lap_distance_m if self.sim.lap_distance_m is not None else 0.0

    def progress(self, index: int | None = None) -> float:
        return max(0.0, min(1.0, self.distance(index) / self.track_length())) if self.track_length() > 0 else 0.0

    def maximum(self) -> int:
        return DATA.MAX_LAPS

    def remaining(self, index: int | None = None) -> float:
        return 0.0

    def sector_index(self, index: int | None = None) -> int:
        return 0

    def safety_car_distance(self) -> float:
        return 0.0

    def safety_car_active(self) -> bool:
        return False


class Session(_reader.Session, DataAdapter):
    __slots__ = ()

    def combo_name(self) -> str:
        return strip_invalid_char(self.track_name() + " - " + (self.gauge.car or "LFS"))

    def track_name(self) -> str:
        return strip_invalid_char(self.source.config["track_name"])

    def identifier(self) -> tuple[int, int, int]:
        return self.source.snapshot().generation, int(self.elapsed()), 0

    def elapsed(self) -> float:
        return self.sim.time_ms / 1000

    def remaining(self) -> float:
        return 0.0

    def session_type(self) -> int:
        return 0

    def finish_type(self, as_lap: bool | None = None) -> int:
        return 0

    def in_race(self) -> bool:
        return False

    def private_qualifying(self) -> bool:
        return False

    def pit_open(self) -> bool:
        return False

    def pre_race(self) -> bool:
        return False

    def green_flag(self) -> bool:
        return False

    def blue_flag(self, index: int | None = None) -> bool:
        return False

    def yellow_flag(self) -> bool:
        return False

    def start_lights(self) -> int:
        return -1

    def track_temperature(self) -> float:
        return DATA.ABS_ZERO_CELSIUS

    def ambient_temperature(self) -> float:
        return DATA.ABS_ZERO_CELSIUS

    def raininess(self) -> float:
        return 0.0

    def wetness(self) -> float:
        return 0.0

    def weather_forecast(self) -> tuple[tuple[float, int, float, float], ...]:
        return ()

    def cloud_coverage(self) -> int:
        return 0

    def grip_level(self) -> float:
        return 0.0

    def track_time(self, scale: int = 1) -> float:
        return 0.0

    def time_scale(self) -> int:
        return 1

    def limits_points(self) -> float:
        return 0.0

    def cut_points(self, index: int | None = None) -> float:
        return 0.0

    def wind_direction(self) -> float:
        return 0.0

    def wind_speed(self) -> float:
        return 0.0


class Switch(_reader.Switch, DataAdapter):
    __slots__ = ()

    def tc_level(self, index: int | None = None) -> int:
        return 0

    def tc_cut_level(self, index: int | None = None) -> int:
        return 0

    def tc_slip_level(self, index: int | None = None) -> int:
        return 0

    def abs_level(self, index: int | None = None) -> int:
        return 0

    def motor_map_level(self, index: int | None = None) -> int:
        return 0

    def brake_migration_level(self, index: int | None = None) -> int:
        return 0

    def front_arb_level(self, index: int | None = None) -> int:
        return 0

    def rear_arb_level(self, index: int | None = None) -> int:
        return 0

    def wipers(self, index: int | None = None) -> int:
        return 0

    def headlights(self, index: int | None = None) -> int:
        return int(bool(self.gauge.show_lights & (1 << 1)))

    def ignition(self, index: int | None = None, stall_rpm: float = 100) -> int:
        return 0

    def speed_limiter(self, index: int | None = None) -> int:
        return int(bool(self.gauge.show_lights & (1 << 4)))

    def tc_active(self, index: int | None = None) -> bool:
        return bool(self.gauge.show_lights & (1 << 5))

    def abs_active(self, index: int | None = None) -> bool:
        return bool(self.gauge.show_lights & (1 << 10))

    def drs_status(self, index: int | None = None) -> int:
        return 0

    def auto_clutch(self) -> bool:
        return False


class Timing(_reader.Timing, DataAdapter):
    __slots__ = ()

    def elapsed(self, index: int | None = None) -> float:
        return self.sim.time_ms / 1000

    def is_last_valid(self, index: int | None = None) -> bool:
        return False

    def current_laptime(self, index: int | None = None) -> float:
        return 0.0

    def last_laptime(self, index: int | None = None) -> float:
        return 0.0

    def best_laptime(self, index: int | None = None) -> float:
        return 0.0

    def reference_laptime(self, index: int | None = None, laptime: float = 0) -> float:
        return laptime if 0 < laptime < DATA.MAX_SECONDS else DATA.MAX_SECONDS

    def estimated_laptime(self, index: int | None = None) -> float:
        return DATA.MAX_SECONDS

    def estimated_time_into(self, index: int | None = None) -> float:
        return 0.0

    def last_sector(self, index: int | None = None) -> float:
        return 0.0


class Tyre(_reader.Tyre, DataAdapter):
    __slots__ = ()

    def compound_name(self, index: int | None = None) -> tuple[str, ...]:
        return ("",) * 4

    def compound_class(self, index: int | None = None) -> tuple[str, ...]:
        return ("",) * 4

    def surface_temperature_avg(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.TYRE_AVERAGE_NA

    def surface_temperature_ico(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.TYRE_ICO_NA

    def inner_temperature_avg(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.TYRE_AVERAGE_NA

    def inner_temperature_ico(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.TYRE_ICO_NA

    def pressure(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def load(self, index: int | None = None) -> tuple[float, ...]:
        return self.wheel_values("load_n")

    def wear(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_NA

    def puncture(self, index: int | None = None, threshold: float = 0.01) -> tuple[bool, ...]:
        return DATA.WHEELS_FALSE

    def carcass_temperature(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.TYRE_AVERAGE_NA

    def vertical_deflection(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def slip_angle(self, index: int | None = None) -> tuple[float, ...]:
        return tuple(math.atan(wheel.tan_slip_angle) for wheel in self.sim.wheels) if self.sim.wheels else DATA.WHEELS_ZERO


class Vehicle(_reader.Vehicle, DataAdapter):
    __slots__ = ()

    def incidents(self, index: int | None = None) -> int:
        return 0

    def is_player(self, index: int = 0) -> bool:
        return index == 0

    def is_driving(self) -> bool:
        return self.source.snapshot().physics is not None

    def player_index(self) -> int:
        return 0

    def slot_id(self, index: int | None = None) -> int:
        return 0

    def driver_name(self, index: int | None = None) -> str:
        return self.source.config["driver_name"]

    def team_name(self, index: int | None = None) -> str:
        return ""

    def vehicle_model(self, index: int | None = None) -> str:
        return self.gauge.car or "LFS"

    def class_name(self, index: int | None = None) -> str:
        return self.gauge.car or "LFS"

    def same_class(self, index: int | None = None) -> bool:
        return index in (None, 0)

    def total_vehicles(self) -> int:
        return int(self.source.snapshot().physics is not None)

    def place(self, index: int | None = None) -> int:
        return 0

    def qualification(self, index: int | None = None) -> int:
        return 0

    def in_pits(self, index: int | None = None) -> bool:
        return False

    def in_garage(self, index: int | None = None) -> bool:
        return False

    def in_paddock(self, index: int | None = None) -> int:
        return 0

    def number_pitstops(self, index: int | None = None) -> int:
        return 0

    def number_penalties(self, index: int | None = None) -> int:
        return 0

    def penalty_type(self, index: int | None = None) -> int:
        return 0

    def pit_request(self, index: int | None = None) -> bool:
        return False

    def pit_stop_time(self) -> float:
        return 0.0

    def repair_time(self) -> float:
        return 0.0

    def finish_state(self, index: int | None = None) -> int:
        return 0

    def orientation_yaw(self, index: int | None = None) -> float:
        return self.sim.heading

    def position_xyz(self, index: int | None = None) -> tuple[float, float, float]:
        return self.sim.position

    def position_longitudinal(self, index: int | None = None) -> float:
        return self.sim.position[1]

    def position_lateral(self, index: int | None = None) -> float:
        return -self.sim.position[0]

    def position_vertical(self, index: int | None = None) -> float:
        return self.sim.position[2]

    def acceleration_lateral(self, index: int | None = None) -> float:
        return self.sim.acceleration[0]

    def acceleration_longitudinal(self, index: int | None = None) -> float:
        return -self.sim.acceleration[1]

    def acceleration_vertical(self, index: int | None = None) -> float:
        return self.sim.acceleration[2]

    def velocity_lateral(self, index: int | None = None) -> float:
        return self.local_velocity()[0]

    def velocity_longitudinal(self, index: int | None = None) -> float:
        return self.local_velocity()[1]

    def velocity_vertical(self, index: int | None = None) -> float:
        return self.local_velocity()[2]

    def speed(self, index: int | None = None) -> float:
        return math.sqrt(sum(value * value for value in self.sim.velocity))

    def downforce_front(self, index: int | None = None) -> float:
        return 0.0

    def downforce_rear(self, index: int | None = None) -> float:
        return 0.0

    def damage_severity(self, index: int | None = None) -> tuple[float, ...]:
        return (0.0,) * 8

    def aero_damage(self, index: int | None = None) -> float:
        return -1.0

    def integrity(self, index: int | None = None) -> float:
        return 0.0

    def is_detached(self, index: int | None = None) -> bool:
        return False

    def impact_time(self, index: int | None = None) -> float:
        return 0.0

    def impact_position(self, index: int | None = None) -> tuple[float, float]:
        return 0.0, 0.0

    def setup(self) -> tuple[str, ...]:
        return ()


class Wheel(_reader.Wheel, DataAdapter):
    __slots__ = ()

    def track_front(self, index: int | None = None) -> float:
        return 0.0

    def track_rear(self, index: int | None = None) -> float:
        return 0.0

    def wheelbase(self, index: int | None = None) -> float:
        return 0.0

    def camber(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def toe(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def rotation(self, index: int | None = None) -> tuple[float, ...]:
        return self.wheel_values("rotation_rad_s", -1)

    def ride_height(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def third_spring_deflection(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def suspension_deflection(self, index: int | None = None) -> tuple[float, ...]:
        return self.wheel_values("suspension_m", 1000)

    def suspension_force(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def suspension_damage(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def position_vertical(self, index: int | None = None) -> tuple[float, ...]:
        return DATA.WHEELS_ZERO

    def is_detached(self, index: int | None = None) -> tuple[bool, ...]:
        return DATA.WHEELS_FALSE

    def offroad(self, index: int | None = None) -> int:
        return 0
