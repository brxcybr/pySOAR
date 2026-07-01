#!/usr/bin/env python3

"""PySOAR entry point."""

import argparse
import curses
import os
import sys
import traceback

from classes import ConfigurationManager, Log, Playbook
from menu import Menu

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
    return parser.parse_args()


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

    if args.list_playbooks:
        sys.exit(list_playbooks_cli())
    if args.run_playbook:
        sys.exit(run_playbook_cli(args.run_playbook, once=args.once))

    curses.wrapper(main)


if __name__ == '__main__':
    main_cli()
