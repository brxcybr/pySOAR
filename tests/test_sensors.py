#!/usr/bin/env python3

import random
import time
import unittest

from sensors.beacon_detector import BeaconDetectorSensor
from sensors.conditions import evaluate_metric_expression
from sensors.registry import SensorRegistry


class TestMetricExpressions(unittest.TestCase):
    def test_comparisons(self):
        metrics = {'score': 0.9, 'count': 3}
        self.assertTrue(evaluate_metric_expression('score >= 0.8', metrics))
        self.assertFalse(evaluate_metric_expression('score >= 0.95', metrics))
        self.assertTrue(evaluate_metric_expression('score >= 0.8 and count > 2', metrics))
        self.assertFalse(evaluate_metric_expression('score >= 0.8 and count > 5', metrics))
        self.assertTrue(evaluate_metric_expression('count > 5 or score > 0.5', metrics))

    def test_unknown_metric_and_garbage_are_false(self):
        self.assertFalse(evaluate_metric_expression('missing > 1', {'a': 1}))
        self.assertFalse(evaluate_metric_expression('a > banana', {'a': 1}))
        self.assertFalse(evaluate_metric_expression('', {'a': 1}))
        self.assertFalse(evaluate_metric_expression('import os', {'a': 1}))


class TestBeaconDetector(unittest.TestCase):
    def test_regular_beacon_scores_high(self):
        sensor = BeaconDetectorSensor(min_events=6)
        base = time.time() - 20 * 300
        for i in range(20):
            sensor.observe('10.0.0.5', '203.0.113.9', ts=base + i * 300)  # every 5 min
        reading = sensor.poll()
        self.assertGreaterEqual(reading.metrics['beacon_score'], 0.95)
        self.assertGreaterEqual(reading.metrics['beacon_count'], 1)
        values = {(o['type'], o['value']) for o in reading.observables}
        self.assertIn(('ip-src', '10.0.0.5'), values)
        self.assertIn(('ip-dst', '203.0.113.9'), values)

    def test_random_traffic_scores_low(self):
        sensor = BeaconDetectorSensor(min_events=6)
        rng = random.Random(42)
        ts = time.time() - 20 * 3000
        for _ in range(20):
            ts += rng.uniform(10, 3000)
            sensor.observe('10.0.0.6', '198.51.100.20', ts=ts)
        reading = sensor.poll()
        self.assertLess(reading.metrics['beacon_score'], 0.8)
        self.assertEqual(reading.metrics['beacon_count'], 0)
        self.assertEqual(reading.observables, [])

    def test_too_few_events_ignored(self):
        sensor = BeaconDetectorSensor(min_events=6)
        base = time.time() - 300
        for i in range(3):
            sensor.observe('10.0.0.7', '203.0.113.50', ts=base + i * 60)
        reading = sensor.poll()
        self.assertEqual(reading.metrics['beacon_score'], 0.0)

    def test_registry_has_beacon_detector(self):
        SensorRegistry.reset()
        registry = SensorRegistry.get_instance()
        self.assertIsNotNone(registry.get('beacon_detector'))
        ids = [s['id'] for s in registry.list_sensors()]
        self.assertIn('beacon_detector', ids)


class TestSensorTrigger(unittest.TestCase):
    def test_sensor_condition_injects_observables(self):
        from triggers import evaluate_condition

        SensorRegistry.reset()
        registry = SensorRegistry.get_instance()
        sensor = registry.get('beacon_detector')
        sensor.clear()
        base = time.time() - 12 * 300
        for i in range(12):
            sensor.observe('10.0.0.5', '203.0.113.9', ts=base + i * 300)

        shared = {}
        condition = {
            'type': 'sensor',
            'sensor': 'beacon_detector',
            'when': 'beacon_score >= 0.9',
        }
        self.assertTrue(evaluate_condition(condition, shared))
        values = [o['value'] for o in shared.get('observables', [])]
        self.assertIn('203.0.113.9', values)
        self.assertIn('beacon_detector', shared.get('sensor_metrics', {}))

    def test_sensor_condition_false_when_quiet(self):
        from triggers import evaluate_condition

        SensorRegistry.reset()
        sensor = SensorRegistry.get_instance().get('beacon_detector')
        sensor.clear()
        shared = {}
        condition = {
            'type': 'sensor',
            'sensor': 'beacon_detector',
            'when': 'beacon_score >= 0.9',
        }
        self.assertFalse(evaluate_condition(condition, shared))
        self.assertNotIn('sensor_metrics', shared)

    def test_unknown_sensor_is_false(self):
        from triggers import evaluate_condition

        self.assertFalse(
            evaluate_condition({'type': 'sensor', 'sensor': 'nope', 'when': 'x > 1'}, {})
        )


if __name__ == '__main__':
    unittest.main()
