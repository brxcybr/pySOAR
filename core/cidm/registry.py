"""Format adapter registry."""

from __future__ import annotations

from typing import Optional

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.types import IntelFormat


class IntelFormatRegistry:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def __init__(self):
        self._adapters: dict[str, IntelFormatAdapter] = {}
        self._register_defaults()

    def _register_defaults(self):
        from core.cidm.formats.cidm_json import CidmJsonAdapter
        from core.cidm.formats.stix2 import Stix2Adapter
        from core.cidm.formats.openioc import OpenIocAdapter
        from core.cidm.formats.yara import YaraAdapter
        from core.cidm.formats.sigma import SigmaAdapter
        from core.cidm.formats.mitre_attack import MitreAttackAdapter
        from core.cidm.formats.openc2 import OpenC2Adapter
        from core.cidm.formats.observables import ObservablesAdapter
        from core.cidm.formats.stubs import (
            TaxiiAdapter,
            MaecAdapter,
            VerisAdapter,
            CyboxAdapter,
            IdmefAdapter,
            IodefAdapter,
            CapecAdapter,
            MispIntelDatAdapter,
        )

        for adapter in (
            CidmJsonAdapter(),
            Stix2Adapter(),
            OpenIocAdapter(),
            YaraAdapter(),
            SigmaAdapter(),
            MitreAttackAdapter(),
            OpenC2Adapter(),
            ObservablesAdapter(),
            TaxiiAdapter(),
            MaecAdapter(),
            VerisAdapter(),
            CyboxAdapter(),
            IdmefAdapter(),
            IodefAdapter(),
            CapecAdapter(),
            MispIntelDatAdapter(),
        ):
            self.register(adapter)

    def register(self, adapter: IntelFormatAdapter):
        self._adapters[adapter.format_id] = adapter

    def get(self, format_id: str) -> Optional[IntelFormatAdapter]:
        return self._adapters.get(format_id.lower())

    def list_formats(self) -> list[dict]:
        return [
            {
                'id': adapter.format_id,
                'name': adapter.display_name,
                'implemented': adapter.implemented,
            }
            for adapter in sorted(
                self._adapters.values(),
                key=lambda item: item.format_id,
            )
        ]

    def supported_ids(self) -> list[str]:
        return sorted(self._adapters.keys())
