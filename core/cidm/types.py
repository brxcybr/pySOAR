"""CIDM type constants and format identifiers."""

from enum import Enum


class IntelFormat(str, Enum):
    CIDM = 'cidm'
    STIX2 = 'stix2'
    OPENIOC = 'openioc'
    YARA = 'yara'
    SIGMA = 'sigma'
    MITRE_ATTACK = 'mitre_attack'
    OPENC2 = 'openc2'
    TAXII = 'taxii'
    MAEC = 'maec'
    VERIS = 'veris'
    CYBOX = 'cybox'
    IDMEF = 'idmef'
    IODEF = 'iodef'
    CAPEC = 'capec'
    MISP_INTEL = 'intel.dat'
    OBSERVABLES = 'observables'


class CIDMObjectType(str, Enum):
    OBSERVABLE = 'observable'
    INDICATOR = 'indicator'
    DETECTION_RULE = 'detection_rule'
    ATTACK_PATTERN = 'attack_pattern'
    RELATIONSHIP = 'relationship'
    OPENC2_COMMAND = 'openc2_command'
    BUNDLE = 'bundle'
    GENERIC = 'generic'


# STIX 2.x cyber-observable key -> PySOAR/MISP observable type
STIX_OBSERVABLE_MAP = {
    'ipv4-addr': 'ip-dst',
    'ipv6-addr': 'ip-dst',
    'domain-name': 'domain',
    'url': 'url',
    'file:hashes.MD5': 'hash',
    'file:hashes.SHA-256': 'hash',
    'file:hashes.SHA-1': 'hash',
    'email-addr': 'email',
    'file:name': 'filename',
}

# OpenIOC search type -> observable type
OPENIOC_TERM_MAP = {
    'PortItem': 'port',
    'AddressItem': 'ip-dst',
    'DomainItem': 'domain',
    'URLItem': 'url',
    'FileItem': 'filename',
    'EmailItem': 'email',
    'FileHashItem': 'hash',
}

SUPPORTED_FORMATS = frozenset(item.value for item in IntelFormat)

FULLY_IMPLEMENTED_FORMATS = frozenset({
    IntelFormat.CIDM.value,
    IntelFormat.STIX2.value,
    IntelFormat.OPENIOC.value,
    IntelFormat.YARA.value,
    IntelFormat.SIGMA.value,
    IntelFormat.MITRE_ATTACK.value,
    IntelFormat.OPENC2.value,
    IntelFormat.OBSERVABLES.value,
})

STUB_FORMATS = frozenset({
    IntelFormat.TAXII.value,
    IntelFormat.MAEC.value,
    IntelFormat.VERIS.value,
    IntelFormat.CYBOX.value,
    IntelFormat.IDMEF.value,
    IntelFormat.IODEF.value,
    IntelFormat.CAPEC.value,
    IntelFormat.MISP_INTEL.value,
})
