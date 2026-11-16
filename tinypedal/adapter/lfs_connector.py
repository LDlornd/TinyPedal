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

"""将 LFS UDP 生命周期接入现有游戏接口。"""

from ..constant import API
from . import lfs_reader
from ._connector import APIDataReader, Connector
from .lfs_udp import Telemetry


class SimLFS(Connector):
    NAME = API.NAME_LFS
    LEGACY = False
    __slots__ = ("_udpapi",)

    def __init__(self):
        self._udpapi = Telemetry()

    def start(self):
        self._udpapi.start()

    def stop(self):
        self._udpapi.stop()

    def setup(self, config: dict):
        try:
            self._udpapi.setup(config)
        except ValueError as error:
            self._udpapi.config = config.copy()
            self._udpapi.error = str(error)

    def reader(self) -> APIDataReader:
        source = self._udpapi
        return APIDataReader(
            lfs_reader.State(source),
            lfs_reader.Brake(source),
            lfs_reader.ElectricMotor(source),
            lfs_reader.Engine(source),
            lfs_reader.Inputs(source),
            lfs_reader.Lap(source),
            lfs_reader.Session(source),
            lfs_reader.Switch(source),
            lfs_reader.Timing(source),
            lfs_reader.Tyre(source),
            lfs_reader.Vehicle(source),
            lfs_reader.Wheel(source),
        )
