"""Placeholder adapters for additional intel formats."""

from __future__ import annotations

from typing import Union

from core.cidm.formats.base import IntelFormatAdapter
from core.cidm.model import CIDMBundle, CIDMObject
from core.cidm.types import IntelFormat


class _StubAdapter(IntelFormatAdapter):
    implemented = False

    def __init__(self, format_id: str, display_name: str):
        self.format_id = format_id
        self.display_name = display_name

    def parse(self, content: Union[str, bytes, dict]) -> CIDMBundle:
        raise NotImplementedError(
            f'{self.display_name} import is not implemented yet. '
            f'Convert to STIX 2.x or CIDM JSON first.'
        )

    def serialize(self, bundle: CIDMBundle):
        raise NotImplementedError(
            f'{self.display_name} export is not implemented yet.'
        )


class TaxiiAdapter(_StubAdapter):
    def __init__(self):
        super().__init__(IntelFormat.TAXII.value, 'TAXII 2.x client')


class MaecAdapter(_StubAdapter):
    def __init__(self):
        super().__init__(IntelFormat.MAEC.value, 'MAEC')


class VerisAdapter(_StubAdapter):
    def __init__(self):
        super().__init__(IntelFormat.VERIS.value, 'VERIS')


class CyboxAdapter(_StubAdapter):
    def __init__(self):
        super().__init__(IntelFormat.CYBOX.value, 'CybOX (legacy)')


class IdmefAdapter(_StubAdapter):
    def __init__(self):
        super().__init__(IntelFormat.IDMEF.value, 'IDMEF (RFC 4765)')


class IodefAdapter(_StubAdapter):
    def __init__(self):
        super().__init__(IntelFormat.IODEF.value, 'IODEF (RFC 5070)')


class CapecAdapter(_StubAdapter):
    def __init__(self):
        super().__init__(IntelFormat.CAPEC.value, 'CAPEC')


class MispIntelDatAdapter(_StubAdapter):
    def __init__(self):
        super().__init__(IntelFormat.MISP_INTEL.value, 'MISP intel.dat export')
