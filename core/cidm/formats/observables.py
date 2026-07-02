"""Playbook observables list adapter."""

from __future__ import annotations

from typing import Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMObservable
from core.cidm.types import IntelFormat
from core.observables import STANDARD_OBSERVABLE_TYPES


class ObservablesAdapter(IntelFormatAdapter):
    format_id = IntelFormat.OBSERVABLES.value
    display_name = 'PySOAR observables'

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        if isinstance(content, dict):
            data = content
        else:
            import json

            text = content.decode() if isinstance(content, bytes) else content
            data = json.loads(text)

        cidm = CIDMBundle(source_format=self.format_id, title='Observables export')
        for item in data.get('observables', []):
            cidm.add_observable(CIDMObservable.from_dict(item))
        for key, value in data.items():
            # Only promote known observable keys; skip control keys such as
            # feed_id or playbook bookkeeping values in shared_data.
            if key not in STANDARD_OBSERVABLE_TYPES:
                continue
            if isinstance(value, list):
                for entry in value:
                    cidm.add_observable(CIDMObservable(key, str(entry), source_format=self.format_id))
            elif value is not None:
                cidm.add_observable(CIDMObservable(key, str(value), source_format=self.format_id))
        return cidm

    def serialize(self, bundle: CIDMBundle) -> dict:
        grouped = {}
        for obs in bundle.all_observables():
            grouped.setdefault(obs.type, [])
            if obs.value not in grouped[obs.type]:
                grouped[obs.type].append(obs.value)
        payload = {
            'schema_version': 1,
            'observables': [o.to_dict() for o in bundle.all_observables()],
        }
        for key, values in grouped.items():
            payload[key] = values[0] if len(values) == 1 else values
        return payload
