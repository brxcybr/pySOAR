"""YARA rule adapter (structure parse; no native compilation)."""

from __future__ import annotations

import re
from typing import Optional, Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMDetectionRule, CIDMObservable
from core.cidm.types import IntelFormat


class YaraAdapter(IntelFormatAdapter):
    format_id = IntelFormat.YARA.value
    display_name = 'YARA'

    # Matches the rule declaration up to the opening brace, including
    # optional global/private modifiers and rule tags (rule name : tag1 tag2 {).
    _rule_start_re = re.compile(
        r'^\s*(?:(?:global|private)\s+)*rule\s+(?P<name>\w+)'
        r'(?:\s*:\s*(?P<tags>[\w\s]+?))?\s*\{',
        re.MULTILINE,
    )
    _string_hash_re = re.compile(
        r'\$[\w]+\s*=\s*"(?P<hash>[a-fA-F0-9]{32,64})"',
    )

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        text = content if isinstance(content, str) else content.decode()
        cidm = CIDMBundle(source_format=self.format_id, title='YARA rules')
        for match in self._rule_start_re.finditer(text):
            name = match.group('name')
            declared_tags = (match.group('tags') or '').split()
            body, end = self._read_braced_block(text, match.end())
            if body is None:
                continue
            cidm.detection_rules.append(
                CIDMDetectionRule(
                    rule_format='yara',
                    name=name,
                    content=text[match.start():end].strip(),
                    tags=declared_tags + self._meta_tags(body),
                    metadata={'raw_meta': self._meta_block(body)},
                )
            )
            for hash_match in self._string_hash_re.finditer(body):
                cidm.add_observable(
                    CIDMObservable('hash', hash_match.group('hash'), source_format=self.format_id)
                )
        return cidm

    def _read_braced_block(self, text: str, start: int) -> tuple[Optional[str], int]:
        """Scan from just after an opening brace to its matching close brace.

        Brace-counts while skipping string literals and comments so hex
        string patterns like ``{ 6A 40 68 }`` don't terminate the rule early.
        """
        depth = 1
        i = start
        n = len(text)
        while i < n:
            char = text[i]
            if char == '"':
                i += 1
                while i < n and text[i] != '"':
                    if text[i] == '\\':
                        i += 1
                    i += 1
            elif char == '/' and i + 1 < n and text[i + 1] == '/':
                while i < n and text[i] != '\n':
                    i += 1
                continue
            elif char == '/' and i + 1 < n and text[i + 1] == '*':
                i += 2
                while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                    i += 1
                i += 1
            elif char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i], i + 1
            i += 1
        return None, n

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
