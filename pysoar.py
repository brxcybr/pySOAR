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
    parser.add_argument(
        '--serve-api',
        action='store_true',
        help='Start the FastAPI REST server instead of the TUI',
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host for --serve-api (default: 127.0.0.1)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8088,
        help='Port for --serve-api (default: 8088)',
    )
    parser.add_argument(
        '--scheduler',
        metavar='PLAYBOOK',
        help='Run a playbook on an interval in the foreground scheduler',
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Scheduler interval in seconds (default: 300)',
    )
    parser.add_argument(
        '--list-actions',
        action='store_true',
        help='List registered action manifests and exit',
    )
    parser.add_argument(
        '--list-intel-formats',
        action='store_true',
        help='List supported threat intelligence formats',
    )
    parser.add_argument(
        '--convert-intel',
        metavar='FILE',
        help='Convert a threat intelligence file through the CIDM hub',
    )
    parser.add_argument(
        '--from-format',
        metavar='FORMAT',
        help='Source format for --convert-intel (e.g. stix2, openioc, yara)',
    )
    parser.add_argument(
        '--to-format',
        metavar='FORMAT',
        default='cidm',
        help='Target format for --convert-intel (default: cidm)',
    )
    parser.add_argument(
        '--output',
        metavar='FILE',
        help='Output path for --convert-intel',
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


def list_actions_cli():
    from core.manifests import ManifestRegistry

    registry = ManifestRegistry.get_instance()
    for manifest in registry.all_manifests():
        print(
            f"{manifest.name}\t{manifest.integration}\t{manifest.risk}\t{manifest.category}"
        )
    return 0


def list_intel_formats_cli():
    from core.cidm.converter import IntelConverter

    for item in IntelConverter().list_formats():
        status = 'implemented' if item['implemented'] else 'stub'
        print(f"{item['id']}\t{item['name']}\t{status}")
    return 0


def convert_intel_cli(input_path, source_format, target_format, output_path=None):
    import json
    from pathlib import Path

    from core.cidm.converter import IntelConverter

    if not source_format:
        log.error('--from-format is required with --convert-intel')
        return 1
    converter = IntelConverter()
    try:
        result = converter.convert_file(
            input_path,
            source_format,
            target_format,
            output_path=output_path,
        )
    except NotImplementedError as exc:
        log.error(str(exc))
        return 1
    except Exception as exc:
        log.error(f'Intel conversion failed: {exc}')
        log.error(traceback.format_exc())
        return 1

    if output_path:
        print(f'Wrote converted intel to {output_path}')
    else:
        if isinstance(result, (dict, list)):
            print(json.dumps(result, indent=2))
        else:
            print(result)
    return 0


def serve_api_cli(host='127.0.0.1', port=8088):
    from api_server import serve
    log.info(f"Starting PySOAR API on {host}:{port}")
    serve(host=host, port=port)
    return 0


def scheduler_cli(playbook_name, interval=300, once=False):
    from scheduler import PlaybookScheduler

    config_mgr = ConfigurationManager()
    sched = PlaybookScheduler(config_mgr)
    sched.schedule_interval(playbook_name, interval, once=once)
    log.info(
        f"Scheduler running playbook '{playbook_name}' every {interval}s "
        "(Ctrl+C to stop)"
    )
    sched.run_forever()
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
    if args.list_actions:
        sys.exit(list_actions_cli())
    if args.list_intel_formats:
        sys.exit(list_intel_formats_cli())
    if args.convert_intel:
        sys.exit(
            convert_intel_cli(
                args.convert_intel,
                args.from_format,
                args.to_format,
                args.output,
            )
        )
    if args.serve_api:
        sys.exit(serve_api_cli(host=args.host, port=args.port))
    if args.scheduler:
        sys.exit(scheduler_cli(args.scheduler, interval=args.interval, once=args.once))
    if args.run_playbook:
        sys.exit(run_playbook_cli(args.run_playbook, once=args.once))

    curses.wrapper(main)


if __name__ == '__main__':
    main_cli()
