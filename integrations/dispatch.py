"""Playbook function dispatch helpers."""

import inspect

from core.manifests import ManifestRegistry

FUNCTION_ALIASES = {
    "get_misp_event_by_type": "get_event_data_by_type",
    "get_firewall_logs_by_daterange": "get_firewall_logs_by_datetimerange",
}

# Legacy defaults used when manifests are absent.
_LEGACY_PRODUCER_FUNCTIONS = {
    "get_misp_event_by_type",
    "get_event_data_by_type",
    "enable_threat_feed",
    "create_misp_event",
}

_LEGACY_FUNCTION_OUTPUT_KEYS = {
    "get_misp_event_by_type": "ip-dst",
    "get_event_data_by_type": "ip-dst",
}

_LEGACY_FUNCTION_INPUT_MAPPING = {
    "add_firewall_rule": {"ip-dst": "src"},
    "ban_ip": {"ip-dst": "ip_dst"},
    "sync_blocklist": {"ip-dst": "ip_dst"},
    "unban_ip": {"ip-dst": "ip_dst"},
    "notify_playbook_result": {"ip-dst": "ip_dst"},
}


def _registry():
    return ManifestRegistry.get_instance()


def producer_functions():
    manifest_producers = _registry().producer_functions()
    return manifest_producers | _LEGACY_PRODUCER_FUNCTIONS


def function_output_keys():
    merged = dict(_LEGACY_FUNCTION_OUTPUT_KEYS)
    merged.update(_registry().function_output_keys())
    return merged


def function_input_mapping():
    merged = dict(_LEGACY_FUNCTION_INPUT_MAPPING)
    for name, mapping in _registry().function_input_mapping().items():
        merged.setdefault(name, {}).update(mapping)
    return merged


# Backward-compatible module-level sets/dicts (computed at import).
PRODUCER_FUNCTIONS = producer_functions()
FUNCTION_OUTPUT_KEYS = function_output_keys()
FUNCTION_INPUT_MAPPING = function_input_mapping()


def resolve_method_name(function_name):
    manifest = _registry().get(function_name)
    if manifest and manifest.method:
        return manifest.method
    return FUNCTION_ALIASES.get(function_name, function_name)


def find_integration_for_function(config_mgr, function_name):
    manifest_integration = _registry().integration_for_function(function_name)
    if manifest_integration:
        for integration in config_mgr.enabled_integrations:
            if integration.name == manifest_integration:
                if function_name in integration.playbook_functions:
                    return integration
                alias = resolve_method_name(function_name)
                if alias in integration.playbook_functions:
                    return integration

    for integration in config_mgr.enabled_integrations:
        if function_name in integration.playbook_functions:
            return integration
        alias = resolve_method_name(function_name)
        if alias in integration.playbook_functions:
            return integration
    raise ValueError(f"No enabled integration provides function '{function_name}'")


def build_kwargs(function_name, method, shared_data, data_dependencies):
    shared_data = shared_data or {}
    kwargs = {}
    method_name = resolve_method_name(function_name)

    if method_name == "enable_threat_feed" and "feed_id" not in shared_data:
        data_type = (data_dependencies or ["ip-dst"])[0]
        return {"data_type": data_type}

    if method_name in ("get_misp_event_by_type", "get_event_data_by_type"):
        data_type = (data_dependencies or ["ip-dst"])[0]
        kwargs["data_type"] = data_type
        if shared_data.get("feed_id"):
            kwargs["feed_id"] = shared_data["feed_id"]
        return kwargs

    input_map = function_input_mapping().get(function_name, {})
    for shared_key, param_name in input_map.items():
        if shared_key in shared_data and shared_data[shared_key] is not None:
            kwargs[param_name] = shared_data[shared_key]

    if data_dependencies and function_name not in producer_functions():
        for dep in data_dependencies:
            if dep not in shared_data or shared_data[dep] is None:
                continue
            sig = inspect.signature(method)
            if dep in sig.parameters:
                kwargs[dep] = shared_data[dep]

    return kwargs


def merge_result(shared_data, function_name, result, integration_returns=None):
    from core.observables import wrap_shared_data

    ctx = wrap_shared_data(shared_data)
    data = ctx.raw

    output_key = function_output_keys().get(function_name)
    if output_key and not isinstance(result, dict):
        data[output_key] = result
        ctx.sync_from_legacy(source=function_name)
        return data

    if isinstance(result, dict):
        for key, value in result.items():
            if integration_returns and key not in integration_returns and key not in data:
                continue
            data[key] = value
        ctx.sync_from_legacy(source=function_name)
        return data

    if integration_returns:
        if len(integration_returns) == 1:
            data[integration_returns[0]] = result

    ctx.sync_from_legacy(source=function_name)
    return data


def is_success(result):
    if result is False or result is None:
        return False
    if isinstance(result, str) and result.startswith("Error"):
        return False
    return True
