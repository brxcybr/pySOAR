"""OpenIOC 1.x XML adapter."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMObservable, CIDMIndicator
from core.cidm.types import IntelFormat, OPENIOC_TERM_MAP


class OpenIocAdapter(IntelFormatAdapter):
    format_id = IntelFormat.OPENIOC.value
    display_name = 'OpenIOC'

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        text = content if isinstance(content, str) else content.decode()
        root = ET.fromstring(text)
        ns = {'ioc': 'http://openioc.org/schemas/OpenIOC_1.1'}
        short = root.find('.//ioc:short_description', ns)
        cidm = CIDMBundle(
            source_format=self.format_id,
            title=(short.text if short is not None else 'OpenIOC'),
        )
        indicators = []
        for indicator in root.findall('.//ioc:Indicator', ns) or root.findall('.//Indicator'):
            obs_list = []
            for node in indicator.iter():
                tag = node.tag.split('}')[-1]
                if tag.endswith('Item'):
                    obs_type = OPENIOC_TERM_MAP.get(tag, 'generic')
                    value = self._item_value(node)
                    if value:
                        observable = CIDMObservable(
                            obs_type, value, source_format=self.format_id
                        )
                        obs_list.append(observable)
                        cidm.add_observable(observable)
            if obs_list:
                indicators.append(
                    CIDMIndicator(
                        pattern=f'openioc:{tag}',
                        pattern_type='openioc',
                        observables=obs_list,
                    )
                )
        cidm.indicators = indicators
        return cidm

    def _item_value(self, node) -> str:
        for child in node:
            if child.tag.endswith('Content') and child.text:
                return child.text.strip()
        return (node.text or '').strip()

    def serialize(self, bundle: CIDMBundle) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<OpenIOC xmlns="http://openioc.org/schemas/OpenIOC_1.1">',
            f'<short_description>{bundle.title or "PySOAR export"}</short_description>',
            '<criteria><Indicator operator="OR">',
        ]
        for obs in bundle.observables:
            item = {
                'ip-dst': 'AddressItem',
                'domain': 'DomainItem',
                'url': 'URLItem',
                'hash': 'FileHashItem',
                'filename': 'FileItem',
                'email': 'EmailItem',
            }.get(obs.type, 'AddressItem')
            lines.append(f'<{item}><Content>{obs.value}</Content></{item}>')
        lines.extend(['</Indicator></criteria>', '</OpenIOC>'])
        return '\n'.join(lines)
