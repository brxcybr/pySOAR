#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from core.cidm.converter import IntelConverter
from core.cidm.bridge import inject_cidm_into_shared_data
from core.cidm.model import CIDMBundle, CIDMObservable
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


class TestAdapterHardening(unittest.TestCase):
    def setUp(self):
        IntelFormatRegistry.reset()

    def test_openioc_export_escapes_xml(self):
        import xml.etree.ElementTree as ET

        bundle = CIDMBundle(title='Feed <A> & B')
        bundle.add_observable(CIDMObservable('url', 'http://x.test/?a=1&b=<2>'))
        xml_text = IntelConverter().serialize(bundle, 'openioc')
        root = ET.fromstring(xml_text)  # must be well-formed XML
        self.assertIsNotNone(root)
        self.assertIn('&amp;', xml_text)

    def test_openioc_indicator_pattern_uses_indicator_id(self):
        xml_text = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<OpenIOC xmlns="http://openioc.org/schemas/OpenIOC_1.1">'
            '<short_description>test</short_description>'
            '<criteria><Indicator id="abc-123" operator="OR">'
            '<AddressItem><Content>198.51.100.20</Content></AddressItem>'
            '</Indicator></criteria></OpenIOC>'
        )
        bundle = IntelConverter().parse(xml_text, 'openioc')
        self.assertEqual(bundle.indicators[0].pattern, 'openioc:abc-123')

    def test_openioc_roundtrip_special_chars(self):
        bundle = CIDMBundle()
        bundle.add_observable(CIDMObservable('url', 'http://x.test/?a=1&b=2'))
        xml_text = IntelConverter().serialize(bundle, 'openioc')
        restored = IntelConverter().parse(xml_text, 'openioc')
        values = [o.value for o in restored.all_observables()]
        self.assertIn('http://x.test/?a=1&b=2', values)

    def test_yara_hex_strings_and_tags(self):
        text = (
            'rule tagged_rule : trojan apt {\n'
            '    strings:\n'
            '        $hex = { 6A 40 68 00 30 00 00 }\n'
            '        $s = "closing } brace in string"\n'
            '    condition:\n'
            '        any of them\n'
            '}\n\n'
            'rule second_rule {\n'
            '    condition: true\n'
            '}\n'
        )
        bundle = IntelConverter().parse(text, 'yara')
        names = [r.name for r in bundle.detection_rules]
        self.assertEqual(names, ['tagged_rule', 'second_rule'])
        first = bundle.detection_rules[0]
        self.assertIn('trojan', first.tags)
        self.assertIn('condition:', first.content)
        self.assertTrue(first.content.rstrip().endswith('}'))

    def test_sigma_serialize_empty_bundle(self):
        result = IntelConverter().serialize(CIDMBundle(), 'sigma')
        self.assertEqual(result, '')

    def test_sigma_ioc_classification(self):
        doc = {
            'title': 'classify',
            'detection': {
                'selection': {
                    'dst_ip': '203.0.113.9',
                    'bad_ip': '999.999.999.999',
                    'domain': 'evil.example.com',
                    'event_id': '4688',
                },
                'condition': 'selection',
            },
        }
        bundle = IntelConverter().parse(doc, 'sigma')
        by_type = {}
        for obs in bundle.all_observables():
            by_type.setdefault(obs.type, []).append(obs.value)
        self.assertIn('203.0.113.9', by_type.get('ip-dst', []))
        self.assertIn('evil.example.com', by_type.get('domain', []))
        all_values = [o.value for o in bundle.all_observables()]
        self.assertNotIn('999.999.999.999', all_values)
        self.assertNotIn('4688', all_values)

    def test_stix_export_is_valid_stix21(self):
        content = json.loads((FIXTURES / 'sample_stix2.json').read_text())
        result = IntelConverter().convert(content, 'stix2', 'stix2')
        self.assertEqual(result['type'], 'bundle')
        self.assertTrue(result['id'].startswith('bundle--'))
        for obj in result['objects']:
            self.assertIn('id', obj)
            self.assertTrue(obj['id'].startswith(f"{obj['type']}--"))
            if obj['type'] == 'indicator':
                self.assertIn('valid_from', obj)
                self.assertIn('pattern_type', obj)
                self.assertIn('created', obj)

    def test_stix_parse_ipv6_sco(self):
        payload = {
            'type': 'bundle',
            'objects': [{'type': 'ipv6-addr', 'value': '2001:db8::1'}],
        }
        bundle = IntelConverter().parse(payload, 'stix2')
        values = [o.value for o in bundle.all_observables() if o.type == 'ip-dst']
        self.assertIn('2001:db8::1', values)

    def test_stix_export_ipv6_uses_ipv6_type(self):
        bundle = CIDMBundle()
        bundle.add_observable(CIDMObservable('ip-dst', '2001:db8::1'))
        result = IntelConverter().serialize(bundle, 'stix2')
        self.assertEqual(result['objects'][0]['type'], 'ipv6-addr')

    def test_stix_export_md5_hash_algo(self):
        bundle = CIDMBundle()
        bundle.add_observable(CIDMObservable('hash', 'd41d8cd98f00b204e9800998ecf8427e'))
        result = IntelConverter().serialize(bundle, 'stix2')
        self.assertIn('MD5', result['objects'][0]['hashes'])

    def test_observables_adapter_ignores_control_keys(self):
        data = {'feed_id': 5, 'ip-dst': '198.51.100.30'}
        bundle = IntelConverter().parse(data, 'observables')
        types = {o.type for o in bundle.all_observables()}
        self.assertEqual(types, {'ip-dst'})

    def test_malformed_cidm_content_raises_value_error(self):
        with self.assertRaises(ValueError):
            IntelConverter().parse('[1, 2, 3]', 'cidm')


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
