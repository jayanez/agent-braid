# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental product tooling commands, independent of the legacy CLI paths."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys


def _strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate presentation JSON member")
            result[key] = value
        return result
    def constant(_value):
        raise ValueError("nonfinite presentation JSON value")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def add_parser(subparsers):
    parser = subparsers.add_parser("tooling", help="experimental portable local AI tooling")
    commands = parser.add_subparsers(dest="tooling_command", required=True)
    serve = commands.add_parser("serve", help="stdio MCP server (requires optional tooling extra)")
    serve.add_argument("--source-root", type=Path, required=True)
    serve.add_argument("--result-root", type=Path, required=True)
    serve.add_argument("--grant-store", type=Path)
    serve.add_argument("--enable-runtime", action="store_true")
    serve.add_argument("--worktree-root", type=Path, action="append", default=[])
    for name in ("configure", "install", "doctor", "update", "uninstall"):
        command = commands.add_parser(name, help=f"{name} selected receipt-owned host assets")
        command.add_argument("--host", choices=("codex", "claude"), required=True)
        command.add_argument("--scope", choices=("user", "project"), required=True)
        command.add_argument("--source-root", type=Path, required=True)
        command.add_argument("--result-root", type=Path, required=True)
        command.add_argument("--name", default="agent-braid")
        command.add_argument("--grant-store", type=Path)
        command.add_argument("--enable-runtime", action="store_true")
        command.add_argument("--executable", type=Path)
        command.add_argument("--destination", type=Path, help="explicit alternate config/skills/receipt root")
        command.add_argument("--receipt", type=Path)
        command.add_argument("--source-checkout-assets", action="store_true", help="explicit source-development assets instead of installed resources")
        if name != "doctor":
            command.add_argument("--apply", action="store_true")
            command.add_argument("--preview-digest", help="exact digest from the selected preview; required for apply")
    present = commands.add_parser("present", help="render a bounded tooling result; no runtime dispatch")
    present.add_argument("input", type=Path)
    present.add_argument("--format", choices=("text", "json", "graph"), default="text")
    present.add_argument("--export-directory", type=Path)
    present.add_argument("--evidence-ref", action="append", default=[])


def run(args) -> int:
    from .tooling_install import InstallationRefused, Selection, apply, doctor, plan
    try:
        if args.tooling_command == "serve":
            from .tooling_mcp import ToolingConfig, serve_stdio
            config = ToolingConfig(source_root=args.source_root, result_parent=args.result_root,
                                   grant_store=args.grant_store, runtime_enabled=args.enable_runtime,
                                   worktree_roots=tuple(args.worktree_root))
            asyncio.run(serve_stdio(config))
            return 0
        if args.tooling_command == "present":
            from .tooling_present import (PresentationError, canonical_result_json,
                                         render_summary, build_graph, render_graph_ascii, write_exports)
            with args.input.open("rb") as stream:
                raw = stream.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise PresentationError("presentation input exceeds 8 MiB")
            value = _strict_json(raw.decode("utf-8"))
            if args.export_directory:
                output = write_exports(value, args.export_directory, selected_evidence_refs=args.evidence_ref)
                print(json.dumps(output, ensure_ascii=False, sort_keys=True))
            elif args.format == "json":
                sys.stdout.write(canonical_result_json(value).decode("utf-8"))
            elif args.format == "graph":
                print(render_graph_ascii(build_graph(value)))
            else:
                print(render_summary(value, selected_evidence_refs=args.evidence_ref))
            return 0
        selection = Selection(host=args.host, scope=args.scope, source_root=args.source_root,
                              result_root=args.result_root, name=args.name,
                              executable=args.executable, destination=args.destination, receipt=args.receipt,
                              enable_runtime=args.enable_runtime, grant_store=args.grant_store)
        if args.tooling_command == "doctor":
            output = doctor(selection, source_checkout=args.source_checkout_assets)
        else:
            transaction = plan(selection, operation=args.tooling_command, source_checkout=args.source_checkout_assets)
            if args.apply:
                if not args.preview_digest:
                    raise InstallationRefused("--apply requires the exact --preview-digest from the selected preview")
                output = apply(transaction, preview_digest=args.preview_digest)
            else:
                output = transaction.preview()
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError, ImportError, RuntimeError) as exc:
        # Preserve actionable fixed diagnoses, never print a traceback/payload on stdout.
        if isinstance(exc, InstallationRefused) and exc.diagnostic is not None:
            record = {"schema": "agent-braid-tooling-refusal-record/v1",
                      "message": str(exc), "diagnostic": exc.diagnostic}
            sys.stderr.write(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                        separators=(",", ":"), allow_nan=False) + "\n")
            return 2
        print(f"tooling refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    from .cli import main
    raise SystemExit(main())
