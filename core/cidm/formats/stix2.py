"""STIX 2.x bundle adapter (stdlib JSON; optional stix2 library)."""

from __future__ import annotations

import json
import re
from typing import Any, Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMObservable, CIDMIndicator, CIDMAttackPattern, CIDMRelationship
from core.cidm.types import IntelFormat, STIX_OBSERVABLE_MAP


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

            parsed = stix2.parse(payload, allow_custom=True)
            return self._from_json(json.loads(parsed.serialize()))
        except ImportError:
            return self._from_json(payload)
        except Exception:
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
            elif obj_type.startswith('x-') or obj_type in (
                'ipv4-addr', 'domain-name', 'url', 'file', 'email-addr'
            ):
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
        if obj_type == 'ipv4-addr':
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
        for match in re.finditer(r"([\w\-]+(?::[\w\-]+)?)\s*=\s*'([^']+)'", pattern):
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
        objects = []
        for obs in bundle.observables:
            stix_type = {
                'ip-dst': 'ipv4-addr',
                'domain': 'domain-name',
                'url': 'url',
                'email': 'email-addr',
                'filename': 'file',
            }.get(obs.type, 'x-pysoar-observable')
            if stix_type == 'ipv4-addr':
                objects.append({'type': 'ipv4-addr', 'value': obs.value})
            elif stix_type == 'domain-name':
                objects.append({'type': 'domain-name', 'value': obs.value})
            elif stix_type == 'url':
                objects.append({'type': 'url', 'value': obs.value})
            elif stix_type == 'email-addr':
                objects.append({'type': 'email-addr', 'value': obs.value})
            elif obs.type == 'hash':
                objects.append({'type': 'file', 'hashes': {'SHA-256': obs.value}})
            else:
                objects.append({'type': 'x-pysoar-observable', 'value': obs.value, 'obs_type': obs.type})
        for indicator in bundle.indicators:
            objects.append(
                {
                    'type': 'indicator',
                    'pattern': indicator.pattern,
                    'pattern_type': indicator.pattern_type,
                    'labels': indicator.labels,
                }
            )
        for technique in bundle.attack_patterns:
            objects.append(
                {
                    'type': 'attack-pattern',
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
            'spec_version': '2.1',
            'objects': objects,
        }
