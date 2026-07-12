"""CIDM entity definitions — internal hub for threat intelligence interchange."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import uuid


def _new_id(prefix: str = 'cidm') -> str:
    return f'{prefix}--{uuid.uuid4()}'


@dataclass
class CIDMObservable:
    type: str
    value: str
    labels: list[str] = field(default_factory=list)
    source_format: str = ''
    external_refs: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'object_type': 'observable',
            'type': self.type,
            'value': self.value,
            'labels': list(self.labels),
            'source_format': self.source_format,
            'external_refs': list(self.external_refs),
            'metadata': dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CIDMObservable':
        return cls(
            type=data.get('type', 'generic'),
            value=str(data.get('value', '')),
            labels=list(data.get('labels') or []),
            source_format=data.get('source_format', ''),
            external_refs=list(data.get('external_refs') or []),
            metadata=dict(data.get('metadata') or {}),
        )


@dataclass
class CIDMIndicator:
    pattern: str
    pattern_type: str = 'stix'
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    labels: list[str] = field(default_factory=list)
    observables: list[CIDMObservable] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'object_type': 'indicator',
            'pattern': self.pattern,
            'pattern_type': self.pattern_type,
            'valid_from': self.valid_from,
            'valid_until': self.valid_until,
            'labels': list(self.labels),
            'observables': [o.to_dict() for o in self.observables],
            'metadata': dict(self.metadata),
        }


@dataclass
class CIDMDetectionRule:
    rule_format: str
    name: str
    content: str
    severity: str = 'medium'
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'object_type': 'detection_rule',
            'rule_format': self.rule_format,
            'name': self.name,
            'content': self.content,
            'severity': self.severity,
            'tags': list(self.tags),
            'metadata': dict(self.metadata),
        }


@dataclass
class CIDMAttackPattern:
    external_id: str
    name: str
    description: str = ''
    tactics: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'object_type': 'attack_pattern',
            'external_id': self.external_id,
            'name': self.name,
            'description': self.description,
            'tactics': list(self.tactics),
            'platforms': list(self.platforms),
            'metadata': dict(self.metadata),
        }


@dataclass
class CIDMRelationship:
    relationship_type: str
    source_ref: str
    target_ref: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'object_type': 'relationship',
            'relationship_type': self.relationship_type,
            'source_ref': self.source_ref,
            'target_ref': self.target_ref,
            'metadata': dict(self.metadata),
        }


@dataclass
class CIDMOpenC2Command:
    action: str
    target: dict[str, Any] = field(default_factory=dict)
    args: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'object_type': 'openc2_command',
            'action': self.action,
            'target': dict(self.target),
            'args': dict(self.args),
            'metadata': dict(self.metadata),
        }


@dataclass
class CIDMObject:
    """Generic wrapper preserving source-native payloads."""

    object_type: str
    id: str = field(default_factory=_new_id)
    source_format: str = ''
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'object_type': self.object_type,
            'id': self.id,
            'source_format': self.source_format,
            'data': dict(self.data),
        }


@dataclass
class CIDMBundle:
    """Normalized intelligence container."""

    schema_version: str = '1.0'
    id: str = field(default_factory=_new_id)
    title: str = ''
    description: str = ''
    source_format: str = 'cidm'
    observables: list[CIDMObservable] = field(default_factory=list)
    indicators: list[CIDMIndicator] = field(default_factory=list)
    detection_rules: list[CIDMDetectionRule] = field(default_factory=list)
    attack_patterns: list[CIDMAttackPattern] = field(default_factory=list)
    relationships: list[CIDMRelationship] = field(default_factory=list)
    openc2_commands: list[CIDMOpenC2Command] = field(default_factory=list)
    generic_objects: list[CIDMObject] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'schema_version': self.schema_version,
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'source_format': self.source_format,
            'observables': [o.to_dict() for o in self.observables],
            'indicators': [i.to_dict() for i in self.indicators],
            'detection_rules': [r.to_dict() for r in self.detection_rules],
            'attack_patterns': [a.to_dict() for a in self.attack_patterns],
            'relationships': [r.to_dict() for r in self.relationships],
            'openc2_commands': [c.to_dict() for c in self.openc2_commands],
            'generic_objects': [g.to_dict() for g in self.generic_objects],
            'metadata': dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CIDMBundle':
        if not isinstance(data, dict):
            raise ValueError(
                f'CIDM bundle must be a JSON object, got {type(data).__name__}'
            )
        return cls(
            schema_version=data.get('schema_version', '1.0'),
            id=data.get('id', _new_id()),
            title=data.get('title', ''),
            description=data.get('description', ''),
            source_format=data.get('source_format', 'cidm'),
            observables=[
                CIDMObservable.from_dict(o) for o in data.get('observables', [])
            ],
            indicators=[
                CIDMIndicator(
                    pattern=i.get('pattern', ''),
                    pattern_type=i.get('pattern_type', 'stix'),
                    valid_from=i.get('valid_from'),
                    valid_until=i.get('valid_until'),
                    labels=list(i.get('labels') or []),
                    observables=[
                        CIDMObservable.from_dict(o)
                        for o in i.get('observables', [])
                    ],
                    metadata=dict(i.get('metadata') or {}),
                )
                for i in data.get('indicators', [])
            ],
            detection_rules=[
                CIDMDetectionRule(
                    rule_format=r.get('rule_format', ''),
                    name=r.get('name', ''),
                    content=r.get('content', ''),
                    severity=r.get('severity', 'medium'),
                    tags=list(r.get('tags') or []),
                    metadata=dict(r.get('metadata') or {}),
                )
                for r in data.get('detection_rules', [])
            ],
            attack_patterns=[
                CIDMAttackPattern(
                    external_id=a.get('external_id', ''),
                    name=a.get('name', ''),
                    description=a.get('description', ''),
                    tactics=list(a.get('tactics') or []),
                    platforms=list(a.get('platforms') or []),
                    metadata=dict(a.get('metadata') or {}),
                )
                for a in data.get('attack_patterns', [])
            ],
            relationships=[
                CIDMRelationship(
                    relationship_type=r.get('relationship_type', ''),
                    source_ref=r.get('source_ref', ''),
                    target_ref=r.get('target_ref', ''),
                    metadata=dict(r.get('metadata') or {}),
                )
                for r in data.get('relationships', [])
            ],
            openc2_commands=[
                CIDMOpenC2Command(
                    action=c.get('action', ''),
                    target=dict(c.get('target') or {}),
                    args=dict(c.get('args') or {}),
                    metadata=dict(c.get('metadata') or {}),
                )
                for c in data.get('openc2_commands', [])
            ],
            generic_objects=[
                CIDMObject(
                    object_type=g.get('object_type', 'generic'),
                    id=g.get('id', _new_id()),
                    source_format=g.get('source_format', ''),
                    data=dict(g.get('data') or {}),
                )
                for g in data.get('generic_objects', [])
            ],
            metadata=dict(data.get('metadata') or {}),
        )

    def all_observables(self) -> list[CIDMObservable]:
        found = list(self.observables)
        for indicator in self.indicators:
            found.extend(indicator.observables)
        return found

    def add_observable(self, observable: CIDMObservable) -> None:
        for existing in self.observables:
            if existing.type == observable.type and existing.value == observable.value:
                existing.labels.extend(
                    label for label in observable.labels if label not in existing.labels
                )
                return
        self.observables.append(observable)
