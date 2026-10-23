# SPDX-License-Identifier: AGPL-3.0-only
"""Structured commands backing the plugin onboarding skill."""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import sys

from . import plugin_registry as registry


def add_parser(subparsers):
    parser = subparsers.add_parser('plugin', help='native user-scoped plugin onboarding and MCP')
    commands = parser.add_subparsers(dest='plugin_command', required=True)
    for name in ('setup', 'discover', 'doctor', 'workspaces', 'serve', 'legacy'):
        command = commands.add_parser(name)
        command.add_argument('--home', type=Path, help='explicit private Agent Braid state root')
        command.add_argument('--plugin-root', type=Path, default=os.environ.get('AGENT_BRAID_PLUGIN_ROOT'), help='installed plugin root, supplied by its launcher')
        if name in {'setup', 'workspaces'}:
            command.add_argument('--source-root', type=Path, action='append', default=[])
            command.add_argument('--remove', action='append', default=[])
            command.add_argument('--apply', action='store_true')
            command.add_argument('--preview-digest')
            mode = command.add_mutually_exclusive_group()
            mode.add_argument('--enable-runtime', dest='runtime', action='store_const', const=True, default=None)
            mode.add_argument('--disable-runtime', dest='runtime', action='store_const', const=False)
            command.add_argument('--grant-store', type=Path)
            command.add_argument('--worktree-root', type=Path, action='append', default=[])
        if name == 'setup':
            command.add_argument('--telemetry', choices=('off', 'local'), help='persist plugin MCP local telemetry consent; default off')
        if name == 'legacy':
            command.add_argument('--host', choices=('codex', 'claude'), required=True)
            command.add_argument('--receipt', type=Path)
            command.add_argument('--destination', type=Path, help='explicit alternate legacy host root')
            command.add_argument('--apply', action='store_true')
            command.add_argument('--preview-digest')
            command.add_argument('--source-checkout-assets', action='store_true', help='explicit development-only legacy asset lookup')
        if name == 'discover':
            command.add_argument('--search-root', type=Path, action='append', default=[])
            command.add_argument('--current', type=Path)
            command.add_argument('--max-entries', type=int, default=2000)
            command.add_argument('--max-depth', type=int, default=4)


def run(args):
    try:
        home = registry.home_path(args.home)
        if args.plugin_command == 'serve':
            from .plugin_mcp import serve
            asyncio.run(serve(home, args.plugin_root))
            return 0
        if args.plugin_command == 'legacy':
            from . import plugin_legacy
            if args.receipt is None:
                if args.apply or args.preview_digest:
                    raise registry.RegistryError('Select a receipt before migration')
                output = plugin_legacy.inventory(args.host, args.destination)
            else:
                if args.apply and not args.preview_digest:
                    raise registry.RegistryError('Migration apply requires the exact preview digest')
                output = plugin_legacy.migrate(args.host, args.receipt, destination=args.destination,
                    digest=args.preview_digest, do_apply=args.apply, source_checkout=args.source_checkout_assets)
        elif args.plugin_command == 'discover':
            output = registry.discover(home, args.search_root, current=args.current,
                                      max_entries=args.max_entries, max_depth=args.max_depth)
        elif args.plugin_command == 'doctor':
            from .plugin_mcp import PluginRouter
            output = PluginRouter(home, args.plugin_root).status()
            if args.plugin_root:
                from .plugin_package import verify_package
                output['package'] = verify_package(args.plugin_root)
        elif args.plugin_command == 'workspaces' and not (args.source_root or args.remove):
            if args.apply or args.preview_digest or args.runtime is not None or args.grant_store or args.worktree_root:
                raise registry.RegistryError('Choose explicit source roots for configuration changes')
            output = registry.load(home)
        else:
            telemetry = getattr(args, 'telemetry', None)
            if not (args.source_root or args.remove or telemetry):
                raise registry.RegistryError('Select repositories first with discover or --source-root, or choose --telemetry')
            if args.grant_store and args.runtime is not True:
                raise registry.RegistryError('--grant-store requires explicit --enable-runtime')
            if args.runtime is not None and len(args.source_root) != 1:
                raise registry.RegistryError('Configure runtime for one explicit workspace at a time')
            preview = registry.plan_setup(home, args.source_root, remove=args.remove,
                runtime=args.runtime, grant_store=args.grant_store, worktree_roots=args.worktree_root,
                telemetry=telemetry)
            output = registry.apply(home, preview, args.preview_digest) if args.apply else preview
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f'plugin refused: {exc}', file=sys.stderr)
        return 2
