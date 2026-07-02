"""Sensor registry (singleton, mirrors integration/manifest registries)."""

from __future__ import annotations

from typing import Optional

from sensors.base import SensorBase


class SensorRegistry:
    _instance = None

    @classmethod
    def get_instance(cls) -> 'SensorRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def __init__(self):
        self._sensors: dict[str, SensorBase] = {}
        self._register_defaults()

    def _register_defaults(self):
        from sensors.beacon_detector import BeaconDetectorSensor

        self.register(BeaconDetectorSensor())

    def register(self, sensor: SensorBase):
        self._sensors[sensor.sensor_id] = sensor

    def get(self, sensor_id: str) -> Optional[SensorBase]:
        return self._sensors.get(sensor_id)

    def list_sensors(self) -> list[dict]:
        return [
            {'id': sensor.sensor_id, 'name': sensor.display_name}
            for sensor in sorted(self._sensors.values(), key=lambda s: s.sensor_id)
        ]
