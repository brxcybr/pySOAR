#!/usr/bin/env python3

"""PySOAR entry point."""

import argparse
import curses
import getpass
import os
import sys
import traceback

from classes import ConfigurationManager, Log, Playbook
from menu import Menu
from secrets_manager import SecretStore, SecretStoreError

log = Log.get_instance()
SERVER_NAME = 'pysoar-dev.local'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="PySOAR — lightweight Security Orchestration, Automation, and Response",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python pysoar.py\n"
            "  python pysoar.py --run-playbook test --once\n"
            "  python pysoar.py --run-playbook test\n"
            "  python pysoar.py --init-secrets\n"
            "  python pysoar.py --migrate-secrets\n"
            "  python pysoar.py --set-secret misp\n"
        ),
    )
    parser.add_argument(
        '--run-playbook',
        metavar='NAME',
        help='Run a playbook non-interactively instead of launching the TUI',
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='With --run-playbook, stop after one full cycle',
    )
    parser.add_argument(
        '--list-playbooks',
        action='store_true',
        help='List available playbooks and exit',
    )
    parser.add_argument(
        '--init-secrets',
        action='store_true',
        help='Create the encrypted secrets master key file',
    )
    parser.add_argument(
        '--migrate-secrets',
        action='store_true',
        help='Move plaintext API keys from config YAML into the encrypted vault',
    )
    parser.add_argument(
        '--set-secret',
        metavar='INTEGRATION',
        help='Store an API key for an integration in the encrypted vault',
    )
    parser.add_argument(
        '--api-key',
        metavar='KEY',
        help='API key value for --set-secret (otherwise read securely from prompt)',
    )
    parser.add_argument(
        '--force-init-secrets',
        action='store_true',
        help='With --init-secrets, overwrite an existing master key file',
    )
    return parser.parse_args()


def init_secrets_cli(force=False):
    store = SecretStore.get_instance()
    path = store.init_master_key(force=force)
    print(f"Secrets master key ready at {path}")
    return 0


def migrate_secrets_cli():
    store = SecretStore.get_instance()
    try:
        migrated = store.migrate_all_integrations()
    except SecretStoreError as exc:
        log.error(str(exc))
        return 1
    if migrated:
        print(f"Migrated API keys for: {', '.join(migrated)}")
    else:
        print('No plaintext API keys needed migration.')
    return 0


def set_secret_cli(integration_name, api_key=None):
    store = SecretStore.get_instance()
    store.init_master_key()
    value = api_key or getpass.getpass(f'API key for {integration_name}: ')
    if not value:
        log.error('No API key provided.')
        return 1
    try:
        store.store_api_key(integration_name, value)
    except SecretStoreError as exc:
        log.error(str(exc))
        return 1
    print(f"Stored encrypted API key for {integration_name}.")
    print(
        f"Ensure config/{integration_name}.yaml uses `api_key_secret: true` "
        "instead of a plaintext `api_key`."
    )
    return 0


def run_playbook_cli(playbook_name, once=False):
    config_mgr = ConfigurationManager()
    playbook_mgr = config_mgr.playbook_mgr
    playbook_mgr._load_all_playbooks_if_required()

    if playbook_name not in playbook_mgr.playbook_names:
        log.error(f"Playbook '{playbook_name}' not found.")
        return 1

    playbook = Playbook(playbook_name)
    if not playbook.enabled:
        log.error(f"Playbook '{playbook_name}' is disabled.")
        return 1

    log.info(f"Running playbook '{playbook_name}' (once={once})")
    try:
        playbook_mgr.launch_playbook(playbook_name, config_mgr, once=once)
        return 0
    except Exception as exc:
        log.error(f"Playbook run failed: {exc}")
        log.error(traceback.format_exc())
        return 1


def list_playbooks_cli():
    config_mgr = ConfigurationManager()
    playbook_mgr = config_mgr.playbook_mgr
    playbook_mgr._load_all_playbooks_if_required()
    for name in playbook_mgr.playbook_names:
        enabled = playbook_mgr.playbooks_data.get(name, {}).get('enabled', False)
        status = 'enabled' if enabled else 'disabled'
        print(f"{name}\t{status}")
    return 0


def main(stdscr):
    try:
        Menu().run(stdscr)
    except KeyboardInterrupt:
        print('\nExiting...')
    except Exception as e:
        log.error(f"An error occurred: {e}")
        log.error(traceback.format_exc())
        raise


def main_cli():
    args = parse_arguments()
    log.info("Application is starting...")

    if args.init_secrets:
        sys.exit(init_secrets_cli(force=args.force_init_secrets))
    if args.migrate_secrets:
        sys.exit(migrate_secrets_cli())
    if args.set_secret:
        sys.exit(set_secret_cli(args.set_secret, api_key=args.api_key))
    if args.list_playbooks:
        sys.exit(list_playbooks_cli())
    if args.run_playbook:
        sys.exit(run_playbook_cli(args.run_playbook, once=args.once))

    curses.wrapper(main)


if __name__ == '__main__':
    main_cli()
