"""OpenC2 JSON command adapter."""

from __future__ import annotations

import json
from typing import Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMOpenC2Command, CIDMObservable
from core.cidm.types import IntelFormat


class OpenC2Adapter(IntelFormatAdapter):
    format_id = IntelFormat.OPENC2.value
    display_name = 'OpenC2'

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        if isinstance(content, dict):
            payload = content
        else:
            text = content.decode() if isinstance(content, bytes) else content
            payload = json.loads(text)

        commands = payload if isinstance(payload, list) else [payload]
        cidm = CIDMBundle(source_format=self.format_id, title='OpenC2 commands')
        for cmd in commands:
            if not isinstance(cmd, dict):
                continue
            action = cmd.get('action', '')
            target = cmd.get('target', {})
            args = cmd.get('args', {})
            cidm.openc2_commands.append(
                CIDMOpenC2Command(action=action, target=target, args=args)
            )
            for key in ('ipv4', 'ipv6', 'domain_name', 'url'):
                if key in target:
                    obs_type = {
                        'ipv4': 'ip-dst',
                        'ipv6': 'ip-dst',
                        'domain_name': 'domain',
                        'url': 'url',
                    }[key]
                    cidm.add_observable(
                        CIDMObservable(str(obs_type), str(target[key]), source_format=self.format_id)
                    )
        return cidm

    def serialize(self, bundle: CIDMBundle) -> list[dict]:
        return [
            {
                'action': cmd.action,
                'target': cmd.target,
                'args': cmd.args,
            }
            for cmd in bundle.openc2_commands
        ]
