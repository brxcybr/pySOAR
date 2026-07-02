"""Format adapter base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Union

from core.cidm.model import CIDMBundle


class IntelFormatAdapter(ABC):
    format_id: str = ''
    display_name: str = ''
    implemented: bool = True

    @abstractmethod
    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        """Parse external format into CIDM."""

    @abstractmethod
    def serialize(self, bundle: CIDMBundle) -> Any:
        """Serialize CIDM into external format."""

    def can_parse(self, content: Union[str, bytes, dict]) -> bool:
        return True
