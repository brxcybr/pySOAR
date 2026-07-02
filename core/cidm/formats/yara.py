"""YARA rule adapter (structure parse; no native compilation)."""

from __future__ import annotations

import re
from typing import Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMDetectionRule, CIDMObservable
from core.cidm.types import IntelFormat


class YaraAdapter(IntelFormatAdapter):
    format_id = IntelFormat.YARA.value
    display_name = 'YARA'

    _rule_re = re.compile(
        r'rule\s+(?P<name>\w+)\s*\{(?P<body>.*?)\}',
        re.DOTALL | re.IGNORECASE,
    )
    _string_hash_re = re.compile(
        r'\$[\w]+\s*=\s*"(?P<hash>[a-fA-F0-9]{32,64})"',
    )

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        text = content if isinstance(content, str) else content.decode()
        cidm = CIDMBundle(source_format=self.format_id, title='YARA rules')
        for match in self._rule_re.finditer(text):
            name = match.group('name')
            body = match.group('body')
            cidm.detection_rules.append(
                CIDMDetectionRule(
                    rule_format='yara',
                    name=name,
                    content=f'rule {name} {{{body}}}',
                    tags=self._meta_tags(body),
                    metadata={'raw_meta': self._meta_block(body)},
                )
            )
            for hash_match in self._string_hash_re.finditer(body):
                cidm.add_observable(
                    CIDMObservable('hash', hash_match.group('hash'), source_format=self.format_id)
                )
        return cidm

    def _meta_block(self, body: str) -> dict:
        meta = {}
        block = re.search(r'meta:\s*(.*?)(?:strings:|condition:)', body, re.DOTALL)
        if not block:
            return meta
        for line in block.group(1).splitlines():
            if '=' in line:
                key, _, value = line.partition('=')
                meta[key.strip()] = value.strip().strip('"')
        return meta

    def _meta_tags(self, body: str) -> list[str]:
        tags = []
        for key, value in self._meta_block(body).items():
            if key in ('tag', 'tags'):
                tags.extend(part.strip() for part in value.split(','))
        return tags

    def serialize(self, bundle: CIDMBundle) -> str:
        chunks = []
        for rule in bundle.detection_rules:
            if rule.rule_format == 'yara':
                chunks.append(rule.content)
        return '\n\n'.join(chunks)
