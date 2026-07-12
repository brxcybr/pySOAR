"""CIDM native JSON format."""

from __future__ import annotations

import json
from typing import Any, Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle
from core.cidm.types import IntelFormat


class CidmJsonAdapter(IntelFormatAdapter):
    format_id = IntelFormat.CIDM.value
    display_name = 'CIDM JSON'

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        if isinstance(content, dict):
            return CIDMBundle.from_dict(content)
        text = content.decode() if isinstance(content, bytes) else content
        return CIDMBundle.from_dict(json.loads(text))

    def serialize(self, bundle: CIDMBundle) -> dict:
        return bundle.to_dict()
