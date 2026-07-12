"""Bridge CIDM bundles to playbook shared_data."""

from __future__ import annotations

from typing import Optional

from core.cidm.model import CIDMBundle
from core.observables import SharedDataContext, wrap_shared_data


def inject_cidm_into_shared_data(
    shared_data: Optional[dict],
    bundle: CIDMBundle,
) -> dict:
    ctx = wrap_shared_data(shared_data)
    data = ctx.raw
    data['cidm_bundle'] = bundle.to_dict()
    for observable in bundle.all_observables():
        ctx.add_observable(
            observable.type,
            observable.value,
            source=bundle.source_format or observable.source_format,
            enrichment=observable.metadata or None,
        )
    return data


def extract_cidm_from_shared_data(shared_data: Optional[dict]) -> CIDMBundle | None:
    if not shared_data or 'cidm_bundle' not in shared_data:
        return None
    return CIDMBundle.from_dict(shared_data['cidm_bundle'])
