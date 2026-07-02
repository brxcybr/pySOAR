"""Playbook structure, safety, and data-flow validation."""

from dataclasses import dataclass, field

from integrations.dispatch import producer_functions, function_input_mapping
from core.manifests import ManifestRegistry

_LEGACY_HIGH_RISK = {
    'add_firewall_rule',
    'delete_firewall_rule',
    'ban_ip',
    'sync_blocklist',
    'apply_changes',
}


def _high_risk_functions():
    return ManifestRegistry.get_instance().high_risk_functions() | _LEGACY_HIGH_RISK


def _blocked_first_functions():
    return ManifestRegistry.get_instance().blocked_first_functions() | _LEGACY_HIGH_RISK | {
        'unban_ip',
    }


def _producer_functions():
    return producer_functions()


PRODUCER_FUNCTIONS = _producer_functions()
HIGH_RISK_FUNCTIONS = _high_risk_functions()
BLOCKED_FIRST_FUNCTIONS = _blocked_first_functions()


@dataclass
class ValidationIssue:
    level: str  # error | warning
    code: str
    message: str


@dataclass
class ValidationResult:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def is_valid(self):
        return len(self.errors) == 0

    def add_error(self, code, message):
        self.errors.append(ValidationIssue('error', code, message))

    def add_warning(self, code, message):
        self.warnings.append(ValidationIssue('warning', code, message))


def _function_names(logic):
    return [step.name for step in logic]


def _resolve_branch_target(target, logic_names):
    if target in (None, 'halt_playbook', 'next', 'loop'):
        return True, target
    if target in logic_names:
        return True, target
    return False, target


def validate_playbook(playbook, config_mgr=None):
    """Validate playbook graph, integrations, data flow, and safety rules."""
    result = ValidationResult()
    logic = playbook.logic or []
    names = _function_names(logic)

    if not playbook.name or not str(playbook.name).strip():
        result.add_error('empty_name', 'Playbook name is required.')

    if not logic:
        result.add_error('empty_logic', 'Playbook must contain at least one action.')
        return result

    if logic[0].name == 'halt_playbook':
        result.add_error('halt_first', 'Playbook cannot start with halt_playbook.')

    if logic[0].name in BLOCKED_FIRST_FUNCTIONS:
        result.add_error(
            'risky_first_step',
            f'First action "{logic[0].name}" can modify the environment without prior context.',
        )

    if 'halt_playbook' not in names:
        result.add_warning(
            'missing_halt',
            'Playbook has no explicit halt_playbook step; execution relies on branch targets.',
        )

    available_data = set()
    enabled_functions = set()
    enabled_integrations = set()
    if config_mgr is not None:
        enabled_functions = set(config_mgr.enabled_playbook_functions.keys())
        enabled_integrations = {i.name for i in config_mgr.enabled_integrations}

    for idx, step in enumerate(logic):
        if step.name == 'halt_playbook':
            continue

        if config_mgr and enabled_functions and step.name not in enabled_functions:
            result.add_error(
                'unknown_function',
                f'Step {idx + 1} "{step.name}" is not enabled in any integration.',
            )

        for branch in ('on_success', 'on_fail'):
            target = getattr(step, branch, None)
            ok, resolved = _resolve_branch_target(target, names)
            if not ok:
                result.add_error(
                    'dangling_branch',
                    f'Step {idx + 1} "{step.name}" {branch} references unknown target "{target}".',
                )
            elif resolved == 'loop' and idx == 0:
                result.add_error('loop_first', 'First action cannot loop to a previous step.')
            elif resolved == 'next' and idx == len(logic) - 1:
                result.add_warning(
                    'next_on_last',
                    f'Last action "{step.name}" uses EXECUTE NEXT on {branch}; there is no following step.',
                )

        if step.name in HIGH_RISK_FUNCTIONS and idx == 0:
            result.add_warning(
                'early_risky_action',
                f'High-impact action "{step.name}" appears very early in the playbook.',
            )

        if step.data_dependencies and step.name not in PRODUCER_FUNCTIONS:
            missing = [
                dep for dep in step.data_dependencies
                if dep not in available_data
            ]
            if missing:
                result.add_error(
                    'missing_data_dependency',
                    f'Step {idx + 1} "{step.name}" requires {missing} before it is produced.',
                )

        if step.name in PRODUCER_FUNCTIONS:
            output_key = None
            manifest = ManifestRegistry.get_instance().get(step.name)
            if manifest:
                output_key = manifest.primary_output
            if output_key:
                available_data.add(output_key)
            elif step.data_dependencies:
                available_data.update(step.data_dependencies)

        for shared_key in function_input_mapping().get(step.name, {}):
            available_data.add(shared_key)

        trigger_type = getattr(step, 'trigger_type', '') or step.trigger.get('type', '')
        if trigger_type == 'condition':
            condition = step.trigger.get('condition') or {}
            if not condition:
                result.add_error(
                    'empty_condition',
                    f'Step {idx + 1} "{step.name}" uses CONDITION trigger but defines no condition.',
                )

    if config_mgr and playbook.integration_deps:
        missing_integrations = [
            dep for dep in playbook.integration_deps
            if dep not in enabled_integrations
        ]
        if missing_integrations:
            result.add_error(
                'missing_integrations',
                f'Playbook requires disabled or missing integrations: {missing_integrations}',
            )

    return result


def format_validation_result(result):
    lines = []
    for issue in result.errors + result.warnings:
        prefix = 'ERROR' if issue.level == 'error' else 'WARN'
        lines.append(f'{prefix} [{issue.code}]: {issue.message}')
    if not lines:
        lines.append('Playbook validation passed.')
    return '\n'.join(lines)
