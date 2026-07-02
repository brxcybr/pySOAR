"""SIGMA detection rule adapter."""

from __future__ import annotations

import ipaddress
import re
from typing import Optional, Union

import yaml

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMDetectionRule, CIDMObservable
from core.cidm.types import IntelFormat

_HASH_RE = re.compile(r'^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$')
_DOMAIN_RE = re.compile(r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$')


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
            if not isinstance(value, dict):
                continue
            for _field, pattern in value.items():
                candidates = pattern if isinstance(pattern, list) else [pattern]
                for candidate in candidates:
                    if not isinstance(candidate, str):
                        continue
                    obs_type = self._classify_ioc(candidate)
                    if obs_type:
                        cidm.add_observable(
                            CIDMObservable(obs_type, candidate, source_format=self.format_id)
                        )

    def _classify_ioc(self, value: str) -> Optional[str]:
        """Classify a detection value as an observable type, or None to skip.

        Only obvious atomic indicators (IP, URL, domain, hash) are promoted;
        generic strings like event IDs or process names are left in the rule.
        """
        value = value.strip()
        if not value or '|' in value or len(value) > 512:
            return None
        try:
            ipaddress.ip_address(value)
            return 'ip-dst'
        except ValueError:
            pass
        if value.startswith(('http://', 'https://')):
            return 'url'
        if _HASH_RE.match(value):
            return 'hash'
        if _DOMAIN_RE.match(value):
            return 'domain'
        return None

    def serialize(self, bundle: CIDMBundle) -> str:
        docs = []
        for rule in bundle.detection_rules:
            if rule.rule_format == 'sigma':
                docs.append(yaml.safe_load(rule.content))
        if not docs:
            return ''
        return yaml.safe_dump(docs if len(docs) > 1 else docs[0], sort_keys=False)
