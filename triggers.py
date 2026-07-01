"""Trigger evaluation for playbook steps."""

import os
import time

from integrations.health import check_playbook_integrations, summarize_health


def sync_trigger_dict(playbook_function):
    """Keep PlaybookFunction.trigger dict aligned with trigger_type fields."""
    trigger = {'type': playbook_function.trigger_type or 'always'}
    if playbook_function.trigger_type == 'time':
        trigger['duration'] = playbook_function.trigger_duration
    if playbook_function.trigger_type == 'condition':
        existing = playbook_function.trigger.get('condition', {})
        trigger['condition'] = existing
    playbook_function.trigger = trigger
    return trigger


def evaluate_condition(condition, shared_data=None, config_mgr=None, playbook=None):
    """Evaluate a declarative condition against runtime context."""
    shared_data = shared_data or {}
    condition = condition or {}
    condition_type = condition.get('type', 'shared_data_present')

    if condition_type == 'shared_data_present':
        key = condition.get('key')
        if not key:
            return False
        value = shared_data.get(key)
        if value is None:
            return False
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            return False
        return True

    if condition_type == 'shared_data_count_gt':
        key = condition.get('key')
        threshold = int(condition.get('threshold', 0))
        value = shared_data.get(key, [])
        if not isinstance(value, list):
            value = [value]
        return len(value) > threshold

    if condition_type == 'integration_healthy':
        if config_mgr is None or playbook is None:
            return False
        results = check_playbook_integrations(config_mgr, playbook)
        return all(r.healthy for r in results)

    if condition_type == 'environment':
        var_name = condition.get('var')
        expected = condition.get('equals')
        actual = os.environ.get(var_name)
        return actual == expected

    if condition_type == 'all':
        return all(
            evaluate_condition(sub, shared_data, config_mgr, playbook)
            for sub in condition.get('conditions', [])
        )

    if condition_type == 'any':
        return any(
            evaluate_condition(sub, shared_data, config_mgr, playbook)
            for sub in condition.get('conditions', [])
        )

    return False


def wait_for_trigger(playbook_function, shared_data=None, config_mgr=None, playbook=None, poll_interval=5):
    """
    Block until a trigger is satisfied.
    Returns True when the step should run, False when it should be skipped.
    """
    trigger = sync_trigger_dict(playbook_function)
    trigger_type = trigger.get('type', 'always')

    if trigger_type in ('always', 'continuous'):
        return True

    if trigger_type == 'time':
        duration = trigger.get('duration') or playbook_function.trigger_duration or 0
        time.sleep(max(int(duration), 0))
        return True

    if trigger_type == 'condition':
        condition = trigger.get('condition') or {}
        mode = condition.get('mode', 'wait')
        timeout = int(condition.get('timeout', 0))
        deadline = time.time() + timeout if timeout > 0 else None

        while True:
            if evaluate_condition(condition, shared_data, config_mgr, playbook):
                return True
            if mode != 'wait':
                return False
            if deadline is not None and time.time() >= deadline:
                return False
            time.sleep(max(int(condition.get('poll_interval', poll_interval)), 1))

    return True
