"""Discover integration plugins via entry points with convention fallback."""

from __future__ import annotations

import importlib
from importlib import import_module
from typing import Optional, Type

try:
    from importlib.metadata import entry_points
except ImportError:
    from importlib_metadata import entry_points  # type: ignore


# Explicit class names where capitalize() convention fails.
BUILTIN_INTEGRATIONS = {
    'misp': ('integrations.misp_functions', 'MispFunction'),
    'pfsense': ('integrations.pfsense_functions', 'PfsenseFunction'),
    'crowdsec': ('integrations.crowdsec_functions', 'CrowdsecFunction'),
    'webhook': ('integrations.webhook_functions', 'WebhookFunction'),
    'opnsense': ('integrations.opnsense_functions', 'OpnsenseFunction'),
}


class PluginRegistry:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def __init__(self):
        self._classes: dict[str, type] = {}
        self._load_entry_points()
        for name, (module_path, class_name) in BUILTIN_INTEGRATIONS.items():
            if name not in self._classes:
                self._register_from_module(name, module_path, class_name)

    def _load_entry_points(self):
        try:
            eps = entry_points(group='pysoar.integrations')
        except TypeError:
            eps = entry_points().get('pysoar.integrations', [])
        for ep in eps:
            try:
                self._classes[ep.name] = ep.load()
            except Exception:
                continue

    def _register_from_module(self, name: str, module_path: str, class_name: str):
        try:
            module = import_module(module_path)
            cls = getattr(module, class_name)
            self._classes[name] = cls
        except (ImportError, AttributeError):
            pass

    def get_class(self, integration_name: str) -> Optional[Type]:
        if integration_name in self._classes:
            return self._classes[integration_name]
        return self._load_by_convention(integration_name)

    def _load_by_convention(self, integration_name: str) -> Optional[Type]:
        module_path = f'integrations.{integration_name}_functions'
        class_name = integration_name.capitalize() + 'Function'
        try:
            module = import_module(module_path)
            cls = getattr(module, class_name)
            self._classes[integration_name] = cls
            return cls
        except (ImportError, AttributeError):
            return None

    def registered_names(self) -> list[str]:
        return sorted(self._classes.keys())

    def register(self, name: str, cls: type):
        self._classes[name] = cls
