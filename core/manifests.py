"""Load and query action/analyzer manifests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

MANIFESTS_DIR = Path(__file__).resolve().parent.parent / 'integrations' / 'manifests'

RISK_LEVELS = frozenset({'low', 'medium', 'high', 'critical'})
CATEGORIES = frozenset({'action', 'analyzer', 'responder', 'orchestrator', 'transform'})


@dataclass
class ActionManifest:
    name: str
    integration: str
    category: str = 'action'
    risk: str = 'low'
    play_type: str = 'action'
    producer: bool = False
    method: Optional[str] = None
    inputs: list[dict] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    description: str = ''
    idempotent: bool = False
    dedupe_window_seconds: int = 3600

    @classmethod
    def from_dict(cls, data: dict, path: Path) -> 'ActionManifest':
        name = data.get('name') or path.stem
        return cls(
            name=name,
            integration=data.get('integration', path.parent.name),
            category=data.get('category', 'action'),
            risk=data.get('risk', 'low'),
            play_type=data.get('play_type', data.get('category', 'action')),
            producer=bool(data.get('producer', False)),
            method=data.get('method'),
            inputs=list(data.get('inputs') or []),
            outputs=list(data.get('outputs') or []),
            description=data.get('description', ''),
            idempotent=bool(data.get('idempotent', False)),
            dedupe_window_seconds=int(data.get('dedupe_window_seconds', 3600)),
        )

    @property
    def resolved_method(self) -> str:
        return self.method or self.name

    @property
    def is_high_risk(self) -> bool:
        return self.risk in ('high', 'critical')

    @property
    def input_mapping(self) -> dict[str, str]:
        mapping = {}
        for item in self.inputs:
            obs_name = item.get('name')
            maps_to = item.get('maps_to') or obs_name
            if obs_name:
                mapping[obs_name] = maps_to
        return mapping

    @property
    def primary_output(self) -> Optional[str]:
        for output in self.outputs:
            if output in ('ip-dst', 'domain', 'url', 'hash'):
                return output
        return self.outputs[0] if self.outputs else None


class ManifestRegistry:
    _instance = None

    @classmethod
    def get_instance(cls, manifests_dir: Optional[Path] = None):
        if cls._instance is None:
            cls._instance = cls(manifests_dir)
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def __init__(self, manifests_dir: Optional[Path] = None):
        self.manifests_dir = manifests_dir or MANIFESTS_DIR
        self._by_name: dict[str, ActionManifest] = {}
        self._load()

    def _load(self):
        self._by_name.clear()
        if not self.manifests_dir.exists():
            return
        for path in sorted(self.manifests_dir.rglob('*.yaml')):
            if path.name.endswith('.template.yaml'):
                continue
            try:
                data = yaml.safe_load(path.read_text()) or {}
                if not isinstance(data, dict):
                    continue
                manifest = ActionManifest.from_dict(data, path)
                self._by_name[manifest.name] = manifest
            except (OSError, yaml.YAMLError):
                continue

    def get(self, name: str) -> Optional[ActionManifest]:
        return self._by_name.get(name)

    def all_manifests(self) -> list[ActionManifest]:
        return list(self._by_name.values())

    def for_integration(self, integration: str) -> list[ActionManifest]:
        return [m for m in self._by_name.values() if m.integration == integration]

    def producer_functions(self) -> set[str]:
        return {name for name, m in self._by_name.items() if m.producer}

    def function_output_keys(self) -> dict[str, str]:
        # Only producers write their scalar result into shared_data; mapping a
        # responder here would let a bare `True` return stomp e.g. 'ip-dst'.
        result = {}
        for name, manifest in self._by_name.items():
            if not manifest.producer:
                continue
            primary = manifest.primary_output
            if primary:
                result[name] = primary
        return result

    def function_input_mapping(self) -> dict[str, dict[str, str]]:
        return {name: m.input_mapping for name, m in self._by_name.items() if m.input_mapping}

    def high_risk_functions(self) -> set[str]:
        return {name for name, m in self._by_name.items() if m.is_high_risk}

    def blocked_first_functions(self) -> set[str]:
        return {
            name for name, m in self._by_name.items()
            if m.risk in ('high', 'critical') or m.play_type == 'responder'
        }

    def integration_for_function(self, function_name: str) -> Optional[str]:
        manifest = self.get(function_name)
        return manifest.integration if manifest else None
