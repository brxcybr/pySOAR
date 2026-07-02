"""Format conversion hub — all paths route through CIDM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

from core.cidm.model import CIDMBundle
from core.cidm.registry import IntelFormatRegistry
from core.cidm.types import IntelFormat


class IntelConverter:
    def __init__(self, registry: IntelFormatRegistry | None = None):
        self.registry = registry or IntelFormatRegistry.get_instance()

    def parse(self, content: Union[str, bytes, dict], source_format: str) -> CIDMBundle:
        adapter = self._adapter(source_format)
        return adapter.parse(content)

    def serialize(self, bundle: CIDMBundle, target_format: str) -> Any:
        adapter = self._adapter(target_format)
        return adapter.serialize(bundle)

    def convert(
        self,
        content: Union[str, bytes, dict],
        source_format: str,
        target_format: str,
    ) -> Any:
        bundle = self.parse(content, source_format)
        if target_format.lower() != IntelFormat.CIDM.value:
            bundle.source_format = source_format
        return self.serialize(bundle, target_format)

    def convert_file(
        self,
        input_path: Union[str, Path],
        source_format: str,
        target_format: str,
        output_path: Union[str, Path] | None = None,
    ) -> Any:
        path = Path(input_path)
        raw = path.read_bytes()
        content: Union[str, bytes, dict]
        if source_format in (IntelFormat.STIX2.value, IntelFormat.OPENC2.value, IntelFormat.MITRE_ATTACK.value, IntelFormat.CIDM.value, IntelFormat.OBSERVABLES.value):
            content = json.loads(raw.decode())
        else:
            content = raw.decode()
        result = self.convert(content, source_format, target_format)
        if output_path is not None:
            self.write_result(result, Path(output_path), target_format)
        return result

    def write_result(self, result: Any, output_path: Path, target_format: str):
        if isinstance(result, (dict, list)):
            output_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        else:
            output_path.write_text(str(result), encoding='utf-8')

    def list_formats(self) -> list[dict]:
        return self.registry.list_formats()

    def _adapter(self, format_id: str):
        adapter = self.registry.get(format_id)
        if adapter is None:
            supported = ', '.join(self.registry.supported_ids())
            raise ValueError(f'Unknown intel format {format_id!r}. Supported: {supported}')
        return adapter
