"""Periodic beaconing detector.

Detects hosts calling out to the same destination at suspiciously regular
intervals — the C2 heartbeat pattern. Pure stdlib statistics; cheap enough
to poll every few minutes on Raspberry Pi class hardware.

Event sources:
- a JSONL connection log (``PYSOAR_CONN_LOG`` or constructor arg) with
  records like ``{"src": "10.0.0.5", "dst": "203.0.113.9", "ts": 1719900000}``
  (pfSense filter logs or Suricata eve.json reduce to this shape trivially)
- programmatic feeding via :meth:`observe` (used by tests and integrations)
"""

from __future__ import annotations

import json
import os
import statistics
import time
from collections import defaultdict
from pathlib import Path

from sensors.base import SensorBase, SensorReading


class BeaconDetectorSensor(SensorBase):
    sensor_id = 'beacon_detector'
    display_name = 'Periodic beaconing detector'

    def __init__(
        self,
        log_path: str = '',
        min_events: int = 6,
        max_coefficient_of_variation: float = 0.25,
        window_seconds: int = 24 * 3600,
    ):
        self.log_path = log_path or os.environ.get('PYSOAR_CONN_LOG', '')
        self.min_events = min_events
        self.max_cv = max_coefficient_of_variation
        self.window_seconds = window_seconds
        self._fed_events: list[dict] = []

    def observe(self, src: str, dst: str, ts: float | None = None):
        """Feed a connection event programmatically."""
        self._fed_events.append({'src': src, 'dst': dst, 'ts': ts if ts is not None else time.time()})

    def clear(self):
        self._fed_events.clear()

    def _load_events(self) -> list[dict]:
        events = list(self._fed_events)
        if self.log_path and Path(self.log_path).exists():
            for line in Path(self.log_path).read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict) and record.get('src') and record.get('dst'):
                    events.append(record)
        cutoff = time.time() - self.window_seconds
        return [e for e in events if float(e.get('ts', 0)) >= cutoff]

    def poll(self) -> SensorReading:
        flows: dict[tuple, list[float]] = defaultdict(list)
        for event in self._load_events():
            flows[(event['src'], event['dst'])].append(float(event['ts']))

        best_score = 0.0
        best_flow = None
        best_stats: dict = {}
        flagged = []
        for (src, dst), timestamps in flows.items():
            if len(timestamps) < self.min_events:
                continue
            timestamps.sort()
            intervals = [b - a for a, b in zip(timestamps, timestamps[1:])]
            mean_interval = statistics.fmean(intervals)
            if mean_interval <= 0:
                continue
            cv = statistics.pstdev(intervals) / mean_interval
            # Perfectly regular heartbeat -> cv 0 -> score 1.0
            score = max(0.0, 1.0 - cv)
            duration_hours = (timestamps[-1] - timestamps[0]) / 3600
            stats = {
                'src': src,
                'dst': dst,
                'events': len(timestamps),
                'mean_interval_seconds': round(mean_interval, 2),
                'coefficient_of_variation': round(cv, 4),
                'score': round(score, 4),
                'duration_hours': round(duration_hours, 2),
            }
            if cv <= self.max_cv:
                flagged.append(stats)
            if score > best_score:
                best_score = score
                best_flow = (src, dst)
                best_stats = stats

        observables = []
        for flow in flagged:
            observables.append({'type': 'ip-src', 'value': flow['src']})
            observables.append({'type': 'ip-dst', 'value': flow['dst']})

        metrics = {
            'beacon_score': round(best_score, 4),
            'beacon_count': float(len(flagged)),
            'duration_hours': best_stats.get('duration_hours', 0.0),
            'mean_interval_seconds': best_stats.get('mean_interval_seconds', 0.0),
        }
        return SensorReading(
            metrics=metrics,
            observables=observables,
            details={'best_flow': best_flow, 'flagged': flagged},
        )
