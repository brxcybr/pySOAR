#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from core.cidm.converter import IntelConverter
from core.cidm.bridge import inject_cidm_into_shared_data
from core.cidm.registry import IntelFormatRegistry
from core.cidm.types import IntelFormat

FIXTURES = Path(__file__).parent / 'fixtures' / 'intel'


class TestIntelConverter(unittest.TestCase):
    def setUp(self):
        IntelFormatRegistry.reset()

    def test_list_formats_includes_stubs(self):
        formats = {item['id'] for item in IntelConverter().list_formats()}
        self.assertIn('stix2', formats)
        self.assertIn('idmef', formats)
        self.assertIn('maec', formats)

    def test_stix2_to_observables(self):
        content = json.loads((FIXTURES / 'sample_stix2.json').read_text())
        result = IntelConverter().convert(content, 'stix2', 'observables')
        self.assertIn('observables', result)
        values = result.get('ip-dst', [])
        if isinstance(values, str):
            values = [values]
        self.assertIn('203.0.113.50', values)

    def test_openioc_to_cidm(self):
        content = (FIXTURES / 'sample_openioc.xml').read_text()
        bundle = IntelConverter().parse(content, 'openioc')
        ips = [o.value for o in bundle.all_observables()]
        self.assertIn('198.51.100.10', ips)

    def test_sigma_to_cidm(self):
        content = (FIXTURES / 'sample_sigma.yaml').read_text()
        bundle = IntelConverter().parse(content, 'sigma')
        self.assertEqual(len(bundle.detection_rules), 1)
        self.assertEqual(bundle.detection_rules[0].rule_format, 'sigma')

    def test_yara_extracts_hash(self):
        content = (FIXTURES / 'sample.yar').read_text()
        bundle = IntelConverter().parse(content, 'yara')
        hashes = [o.value for o in bundle.all_observables() if o.type == 'hash']
        self.assertIn('d41d8cd98f00b204e9800998ecf8427e', hashes)

    def test_roundtrip_stix2_via_cidm(self):
        converter = IntelConverter()
        original = json.loads((FIXTURES / 'sample_stix2.json').read_text())
        cidm = converter.convert(original, 'stix2', 'cidm')
        restored = converter.convert(cidm, 'cidm', 'stix2')
        self.assertEqual(restored['type'], 'bundle')
        self.assertTrue(restored['objects'])

    def test_openc2_command(self):
        payload = {
            'action': 'deny',
            'target': {'ipv4': '203.0.113.77'},
            'args': {},
        }
        bundle = IntelConverter().parse(payload, 'openc2')
        self.assertEqual(bundle.openc2_commands[0].action, 'deny')
        self.assertIn('203.0.113.77', [o.value for o in bundle.all_observables()])

    def test_stub_format_raises(self):
        with self.assertRaises(NotImplementedError):
            IntelConverter().parse('<idmef></idmef>', 'idmef')

    def test_bridge_injects_shared_data(self):
        converter = IntelConverter()
        bundle = converter.parse(
            json.loads((FIXTURES / 'sample_stix2.json').read_text()),
            IntelFormat.STIX2.value,
        )
        shared = inject_cidm_into_shared_data({}, bundle)
        self.assertIn('cidm_bundle', shared)
        self.assertIn('observables', shared)


class TestDispatchCidmMerge(unittest.TestCase):
    def test_merge_result_with_cidm_bundle(self):
        from integrations.dispatch import merge_result

        cidm = IntelConverter().parse(
            json.loads((FIXTURES / 'sample_stix2.json').read_text()),
            'stix2',
        )
        shared = merge_result({}, 'test_fn', {'cidm_bundle': cidm.to_dict()})
        self.assertIn('cidm_bundle', shared)
        self.assertTrue(shared.get('observables'))


if __name__ == '__main__':
    unittest.main()
