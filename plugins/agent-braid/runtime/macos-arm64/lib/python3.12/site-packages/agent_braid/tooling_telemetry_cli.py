# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit local telemetry management, independent of host/provider execution."""
from __future__ import annotations

import json
from pathlib import Path
import sys


def add_parser(subparsers):
    parser = subparsers.add_parser('telemetry', help='local numeric telemetry; no automatic upload')
    commands = parser.add_subparsers(dest='telemetry_command', required=True)
    for name in ('status', 'report', 'export', 'merge', 'purge'):
        command = commands.add_parser(name, help=f'{name} local aggregates')
        command.add_argument('--format', choices=('text', 'json'), default='text')
        if name in {'export', 'merge'}:
            command.add_argument('file', type=Path, help='explicit local batch file; export requires a private destination outside repositories')


def run(args) -> int:
    from .tooling_telemetry import Store
    try:
        store = Store()
        method = getattr(store, args.telemetry_command)
        output = method(args.file) if args.telemetry_command in {'export', 'merge'} else method()
        if args.format == 'json':
            print(json.dumps(output, sort_keys=True, indent=2))
        elif args.telemetry_command == 'report':
            print('Local telemetry: daily aggregates, 30-day retention, manual export only')
            for row in output['rows']:
                print(' '.join(str(row[k]) for k in ('day', 'surface', 'operation', 'outcome', 'metric', 'bucket', 'count')))
            print(f"Known collector failures (this process only): {output['knownCollectorFailuresThisProcess']}")
            print(f"Known pending export calls discarded: {output['knownPendingExportCallsDiscarded']}")
            print('Unobserved losses: unknown')
            for limit in output['limits']:
                print(limit)
        else:
            print(json.dumps(output, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError, ImportError):
        # No exception payload, source data or paths enter diagnostics.
        print('local telemetry refused: invalid batch, unsafe/unavailable storage or local capacity limit', file=sys.stderr)
        return 2
