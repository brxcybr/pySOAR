"""MITRE ATT&CK adapter (STIX bundle or technique JSON)."""

from __future__ import annotations

import json
from typing import Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.formats.stix2 import Stix2Adapter
from core.cidm.model import CIDMBundle, CIDMAttackPattern
from core.cidm.types import IntelFormat


class MitreAttackAdapter(IntelFormatAdapter):
    format_id = IntelFormat.MITRE_ATTACK.value
    display_name = 'MITRE ATT&CK'

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        if isinstance(content, dict):
            payload = content
        else:
            text = content.decode() if isinstance(content, bytes) else content
            payload = json.loads(text)

        if payload.get('type') == 'bundle' or payload.get('objects'):
            bundle = Stix2Adapter().parse(payload)
            bundle.source_format = self.format_id
            return bundle

        techniques = payload.get('techniques') or payload.get('objects') or [payload]
        cidm = CIDMBundle(source_format=self.format_id, title='MITRE ATT&CK')
        for item in techniques:
            if not isinstance(item, dict):
                continue
            external_id = item.get('technique_id') or item.get('external_id') or item.get('id', '')
            cidm.attack_patterns.append(
                CIDMAttackPattern(
                    external_id=str(external_id),
                    name=item.get('name', str(external_id)),
                    description=item.get('description', ''),
                    tactics=list(item.get('tactics') or []),
                    platforms=list(item.get('platforms') or []),
                    metadata=dict(item.get('metadata') or {}),
                )
            )
        return cidm

    def serialize(self, bundle: CIDMBundle) -> dict:
        return {
            'type': 'mitre-attack-collection',
            'techniques': [pattern.to_dict() for pattern in bundle.attack_patterns],
        }
