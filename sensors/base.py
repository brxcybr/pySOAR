"""Sensor plugin contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SensorReading:
    """One poll result: numeric metrics plus any observables that explain them."""

    metrics: dict[str, float] = field(default_factory=dict)
    observables: list[dict] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class SensorBase(ABC):
    sensor_id: str = ''
    display_name: str = ''

    @abstractmethod
    def poll(self) -> SensorReading:
        """Evaluate the environment and return current metrics."""
