"""Normalize inbound alert payloads into playbook shared_data.

Vendor-agnostic by design: any tool that can POST JSON can hand work to
PySOAR. Recognized shapes, tried in order:

1. CIDM bundle          {"cidm_bundle": {...}} or a bare CIDM bundle dict
2. STIX 2.x bundle      {"type": "bundle", "objects": [...]}
3. Observables payload  {"observables": [{"type": ..., "value": ...}]}
4. Flat observable keys {"ip-dst": "...", "domain": [...], ...}

Anything unrecognized inside the payload is preserved under `alert` so the
playbook still has the raw context.
"""

from __future__ import annotations

from typing import Any

from core.observables import STANDARD_OBSERVABLE_TYPES, wrap_shared_data


def normalize_alert(payload: Any, source: str = 'ingest') -> dict:
    """Convert an arbitrary alert payload into shared_data with observables."""
    if not isinstance(payload, dict):
        raise ValueError('Alert payload must be a JSON object')

    from core.cidm.bridge import inject_cidm_into_shared_data
    from core.cidm.converter import IntelConverter
    from core.cidm.model import CIDMBundle

    shared_data: dict = {}
    ctx = wrap_shared_data(shared_data)

    if isinstance(payload.get('cidm_bundle'), dict):
        bundle = CIDMBundle.from_dict(payload['cidm_bundle'])
        shared_data = inject_cidm_into_shared_data(shared_data, bundle)
    elif payload.get('schema_version') and payload.get('observables') is not None and payload.get('source_format'):
        # Bare CIDM bundle posted directly.
        bundle = CIDMBundle.from_dict(payload)
        shared_data = inject_cidm_into_shared_data(shared_data, bundle)
    elif payload.get('type') == 'bundle' and isinstance(payload.get('objects'), list):
        bundle = IntelConverter().parse(payload, 'stix2')
        shared_data = inject_cidm_into_shared_data(shared_data, bundle)
    else:
        for item in payload.get('observables') or []:
            if isinstance(item, dict) and item.get('value'):
                ctx.add_observable(
                    item.get('type', 'generic'), str(item['value']), source=source
                )
        for key, value in payload.items():
            if key not in STANDARD_OBSERVABLE_TYPES:
                continue
            values = value if isinstance(value, list) else [value]
            for entry in values:
                if entry is not None:
                    ctx.add_observable(key, str(entry), source=source)

    context = {
        key: value
        for key, value in payload.items()
        if key not in STANDARD_OBSERVABLE_TYPES
        and key not in ('observables', 'cidm_bundle', 'objects')
    }
    if context:
        shared_data['alert'] = context
    shared_data['alert_source'] = source
    return shared_data
