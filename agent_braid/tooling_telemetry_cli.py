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
    audit = commands.add_parser('audit-logs', help='read-only comparison of this plugin\'s host MCP logs with the local store')
    audit.add_argument('--format', choices=('text', 'json'), default='text')
    audit.add_argument('--cache-root', type=Path, help='host CLI cache root; default is the standard per-user location')
    audit.add_argument('--since', help='first UTC date, YYYY-MM-DD; default the last seven days')


def _run_audit(args) -> int:
    import datetime
    from . import telemetry_audit
    from .tooling_telemetry import Store
    try:
        since = datetime.date.fromisoformat(args.since).isoformat() if args.since else None
        try:
            report = Store().report()
        except Exception:  # corrupt or unusable store (sqlite errors included); never echo its payload
            report = None  # reconciliation is then reported as unavailable, never as success
        result = telemetry_audit.audit(args.cache_root or telemetry_audit.default_cache_root(), report, since=since)
    except (ValueError, OSError):
        print('telemetry audit refused: invalid date or unreadable log location', file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2) if args.format == 'json' else telemetry_audit.render_text(result))
    return 0


def run(args) -> int:
    if args.telemetry_command == 'audit-logs':
        return _run_audit(args)
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
