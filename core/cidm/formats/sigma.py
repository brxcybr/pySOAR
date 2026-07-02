"""SIGMA detection rule adapter."""

from __future__ import annotations

from typing import Union

import yaml

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMDetectionRule, CIDMObservable
from core.cidm.types import IntelFormat


class SigmaAdapter(IntelFormatAdapter):
    format_id = IntelFormat.SIGMA.value
    display_name = 'SIGMA'

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        if isinstance(content, dict):
            docs = [content]
        else:
            text = content.decode() if isinstance(content, bytes) else content
            loaded = yaml.safe_load(text)
            docs = loaded if isinstance(loaded, list) else [loaded]

        cidm = CIDMBundle(source_format=self.format_id, title='SIGMA rules')
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            title = doc.get('title', 'sigma-rule')
            cidm.detection_rules.append(
                CIDMDetectionRule(
                    rule_format='sigma',
                    name=title,
                    content=yaml.safe_dump(doc, sort_keys=False),
                    severity=str(doc.get('level', 'medium')),
                    tags=list(doc.get('tags') or []),
                    metadata={
                        'id': doc.get('id', ''),
                        'logsource': doc.get('logsource', {}),
                    },
                )
            )
            self._extract_observables(doc, cidm)
        return cidm

    def _extract_observables(self, doc: dict, cidm: CIDMBundle):
        detection = doc.get('detection') or {}
        for key, value in detection.items():
            if key in ('condition', 'keywords'):
                continue
            if isinstance(value, dict):
                for field, pattern in value.items():
                    if isinstance(pattern, str) and self._looks_like_ioc(pattern):
                        obs_type = 'ip-dst' if self._looks_like_ip(pattern) else 'generic'
                        cidm.add_observable(
                            CIDMObservable(obs_type, pattern, source_format=self.format_id)
                        )

    def _looks_like_ioc(self, value: str) -> bool:
        return bool(value) and '|' not in value and len(value) < 256

    def _looks_like_ip(self, value: str) -> bool:
        parts = value.split('.')
        return len(parts) == 4 and all(part.isdigit() for part in parts)

    def serialize(self, bundle: CIDMBundle) -> str:
        docs = []
        for rule in bundle.detection_rules:
            if rule.rule_format == 'sigma':
                docs.append(yaml.safe_load(rule.content))
        return yaml.safe_dump(docs if len(docs) > 1 else docs[0], sort_keys=False)
