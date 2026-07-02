# Extensibility and vendor neutrality

PySOAR's core knows about **capability categories**, never vendors. MISP and
pfSense are bundled *reference plugins* that prove the contracts work — the
platform does not depend on them. If a vendor product dies, you lose a plugin
file, not the platform.

| Capability | Contract | Extension point | Bundled references |
|---|---|---|---|
| Actions/responders | `integrations/` class + YAML manifest | entry points `pysoar.integrations` | MISP, pfSense, OPNsense, CrowdSec, webhook, SMTP |
| Intel formats | CIDM adapter (`parse`/`serialize`) | `IntelFormatRegistry.register()` | STIX, OpenIOC, YARA, SIGMA, ATT&CK, OpenC2 |
| Enrichment | `AnalyzerBase.analyze()` | entry points `pysoar.analyzers` | VirusTotal, AbuseIPDB, OTX, Shodan |
| Environmental detection | `SensorBase.poll()` | `SensorRegistry.register()` | beacon detector |
| Alert intake | JSON POST to `/ingest` | any tool that can POST | CIDM/STIX/observables/flat shapes |

## Adding an integration for any vendor

1. Write a class with methods for each action (see `integrations/smtp_functions.py`
   for the smallest example). Constructor receives the parsed config object.
2. Add a YAML manifest per action under `integrations/manifests/<name>/`:

```yaml
name: block_source
integration: myfirewall
category: responder
risk: high
idempotent: true          # skip identical repeat invocations
dedupe_window_seconds: 3600
retries: 2                # network retry with exponential backoff
retry_backoff_seconds: 2
inputs:
  - name: ip-dst
    maps_to: source_ip
outputs:
  - firewall-status
```

3. Register via entry point (external package) or `BUILTIN_INTEGRATIONS`
   (in-tree):

```toml
[project.entry-points."pysoar.integrations"]
myfirewall = "mypackage.integrations:MyFirewallFunction"
```

4. Config file `config/myfirewall.yaml` declares URL, credentials
   (secrets-manager backed), and — vendor-agnostically — how to health check:

```yaml
myfirewall:
  enabled: true
  url: "https://firewall.local"
  health_path: "/api/status"      # no core code change needed
  auth_header: "x-api-key"        # or "authorization" (default) / "none"
```

Dispatch, validation, risk gating, idempotency, retries, health checks, and
audit all derive from the manifest and config — no core edits.

## Adding an analyzer

```python
from analyzers.base import AnalyzerBase, AnalyzerReport

class MyAnalyzer(AnalyzerBase):
    analyzer_id = 'myintel'
    display_name = 'My Intel Service'
    supported_types = ('ip-dst', 'domain')

    def _analyze_live(self, obs_type, value):
        ...  # query provider, normalize to verdict/score
        return AnalyzerReport(self.analyzer_id, obs_type, value,
                              verdict='suspicious', score=40.0)
```

API keys come from `PYSOAR_ANALYZER_<ID>_API_KEY`. Caching (state store),
rate limiting, and mock mode are inherited from the base class.

Playbooks use analyzers generically:

```yaml
- function: analyze            # or analyze:virustotal,otx
  trigger: {type: always}
  on_success: decide_response
- function: add_firewall_rule
  trigger:
    type: condition
    condition: {type: expression, when: "analysis_max_score >= 75"}
```

## Alert ingestion (any producer)

```bash
curl -X POST http://pysoar:8088/ingest/triage \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"ip-dst": "203.0.113.9", "severity": "high", "sensor": "suricata"}'
```

The payload is normalized through CIDM into observables; unrecognized fields
are preserved under `shared_data['alert']`. STIX bundles, CIDM bundles,
observable lists, and flat keys are all accepted — so MISP, OpenCTI, Wazuh,
Suricata, or a shell script are equally valid alert sources.
