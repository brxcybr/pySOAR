"""STIX 2.x bundle adapter (stdlib JSON; optional stix2 library)."""

from __future__ import annotations

import ipaddress
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMObservable, CIDMIndicator, CIDMAttackPattern, CIDMRelationship
from core.cidm.types import IntelFormat, STIX_OBSERVABLE_MAP

_SCO_TYPES = ('ipv4-addr', 'ipv6-addr', 'domain-name', 'url', 'file', 'email-addr')


def _stix_id(stix_type: str) -> str:
    return f'{stix_type}--{uuid.uuid4()}'


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')


class Stix2Adapter(IntelFormatAdapter):
    format_id = IntelFormat.STIX2.value
    display_name = 'STIX 2.x'

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        if isinstance(content, dict):
            payload = content
        else:
            text = content.decode() if isinstance(content, bytes) else content
            payload = json.loads(text)

        try:
            import stix2
        except ImportError:
            return self._from_json(payload)
        try:
            parsed = stix2.parse(payload, allow_custom=True)
            return self._from_json(json.loads(parsed.serialize()))
        except Exception:
            # Not strictly valid STIX; fall back to the tolerant parser.
            return self._from_json(payload)

    def _from_json(self, payload: dict) -> CIDMBundle:
        cidm = CIDMBundle(
            source_format=self.format_id,
            title=payload.get('id', 'STIX bundle'),
            metadata={'spec_version': payload.get('spec_version', '2.1')},
        )
        objects = payload.get('objects', [payload] if payload.get('type') else [])
        id_map = {}
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            obj_type = obj.get('type', '')
            obj_id = obj.get('id', '')
            if obj_id:
                id_map[obj_id] = obj_type

            if obj_type == 'indicator':
                observables = self._observables_from_pattern(obj.get('pattern', ''))
                cidm.indicators.append(
                    CIDMIndicator(
                        pattern=obj.get('pattern', ''),
                        pattern_type=obj.get('pattern_type', 'stix'),
                        valid_from=obj.get('valid_from'),
                        valid_until=obj.get('valid_until'),
                        labels=list(obj.get('labels') or []),
                        observables=observables,
                        metadata={'stix_id': obj_id},
                    )
                )
                for obs in observables:
                    cidm.add_observable(obs)
            elif obj_type == 'attack-pattern':
                external_id = self._external_id(obj, 'mitre-attack')
                cidm.attack_patterns.append(
                    CIDMAttackPattern(
                        external_id=external_id or obj_id,
                        name=obj.get('name', external_id or obj_id),
                        description=obj.get('description', ''),
                        metadata={'stix_id': obj_id},
                    )
                )
            elif obj_type == 'relationship':
                cidm.relationships.append(
                    CIDMRelationship(
                        relationship_type=obj.get('relationship_type', ''),
                        source_ref=obj.get('source_ref', ''),
                        target_ref=obj.get('target_ref', ''),
                        metadata={'stix_id': obj_id},
                    )
                )
            elif obj_type.startswith('x-') or obj_type in _SCO_TYPES:
                obs = self._observable_from_sco(obj)
                if obs:
                    cidm.add_observable(obs)
        return cidm

    def _external_id(self, obj: dict, source: str) -> str:
        for ref in obj.get('external_references') or []:
            if ref.get('source_name') == source and ref.get('external_id'):
                return ref['external_id']
        return ''

    def _observable_from_sco(self, obj: dict) -> CIDMObservable | None:
        obj_type = obj.get('type', '')
        if obj_type in ('ipv4-addr', 'ipv6-addr'):
            return CIDMObservable('ip-dst', obj.get('value', ''), source_format=self.format_id)
        if obj_type == 'domain-name':
            return CIDMObservable('domain', obj.get('value', ''), source_format=self.format_id)
        if obj_type == 'url':
            return CIDMObservable('url', obj.get('value', ''), source_format=self.format_id)
        if obj_type == 'email-addr':
            return CIDMObservable('email', obj.get('value', ''), source_format=self.format_id)
        if obj_type == 'file':
            hashes = obj.get('hashes') or {}
            for algo in ('SHA-256', 'MD5', 'SHA-1'):
                if algo in hashes:
                    return CIDMObservable('hash', hashes[algo], source_format=self.format_id)
            if obj.get('name'):
                return CIDMObservable('filename', obj['name'], source_format=self.format_id)
        return None

    def _observables_from_pattern(self, pattern: str) -> list[CIDMObservable]:
        observables = []
        for match in re.finditer(r"([\w\-]+(?::[\w\-\.]+)?)\s*=\s*'([^']+)'", pattern):
            field = match.group(1)
            value = match.group(2)
            base = field.split(':')[0]
            obs_type = STIX_OBSERVABLE_MAP.get(field) or STIX_OBSERVABLE_MAP.get(base, 'generic')
            if base in ('ipv4-addr', 'ipv6-addr'):
                obs_type = 'ip-dst'
            elif base == 'domain-name':
                obs_type = 'domain'
            elif base == 'url':
                obs_type = 'url'
            elif base == 'email-addr':
                obs_type = 'email'
            observables.append(
                CIDMObservable(obs_type, value, source_format=self.format_id)
            )
        return observables

    def serialize(self, bundle: CIDMBundle) -> dict:
        """Serialize to a STIX 2.1 bundle with required ids and timestamps."""
        now = _now_utc()
        objects = []
        for obs in bundle.observables:
            objects.append(self._sco_from_observable(obs))
        for indicator in bundle.indicators:
            objects.append(
                {
                    'type': 'indicator',
                    'spec_version': '2.1',
                    'id': indicator.metadata.get('stix_id') or _stix_id('indicator'),
                    'created': now,
                    'modified': now,
                    'pattern': indicator.pattern,
                    'pattern_type': indicator.pattern_type or 'stix',
                    'valid_from': indicator.valid_from or now,
                    'labels': indicator.labels,
                }
            )
        for technique in bundle.attack_patterns:
            objects.append(
                {
                    'type': 'attack-pattern',
                    'spec_version': '2.1',
                    'id': technique.metadata.get('stix_id') or _stix_id('attack-pattern'),
                    'created': now,
                    'modified': now,
                    'name': technique.name,
                    'description': technique.description,
                    'external_references': [
                        {
                            'source_name': 'mitre-attack',
                            'external_id': technique.external_id,
                        }
                    ],
                }
            )
        return {
            'type': 'bundle',
            'id': _stix_id('bundle'),
            'objects': objects,
        }

    def _sco_from_observable(self, obs: CIDMObservable) -> dict:
        if obs.type in ('ip-dst', 'ip-src'):
            stix_type = 'ipv4-addr'
            try:
                if ipaddress.ip_address(obs.value).version == 6:
                    stix_type = 'ipv6-addr'
            except ValueError:
                pass
            return {'type': stix_type, 'id': _stix_id(stix_type), 'value': obs.value}
        if obs.type == 'domain':
            return {'type': 'domain-name', 'id': _stix_id('domain-name'), 'value': obs.value}
        if obs.type == 'url':
            return {'type': 'url', 'id': _stix_id('url'), 'value': obs.value}
        if obs.type == 'email':
            return {'type': 'email-addr', 'id': _stix_id('email-addr'), 'value': obs.value}
        if obs.type == 'hash':
            algo = {32: 'MD5', 40: 'SHA-1', 64: 'SHA-256'}.get(len(obs.value), 'SHA-256')
            return {'type': 'file', 'id': _stix_id('file'), 'hashes': {algo: obs.value}}
        if obs.type == 'filename':
            return {'type': 'file', 'id': _stix_id('file'), 'name': obs.value}
        return {
            'type': 'x-pysoar-observable',
            'id': _stix_id('x-pysoar-observable'),
            'value': obs.value,
            'obs_type': obs.type,
        }
