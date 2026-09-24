# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only Agent Braid CLI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import tempfile
import threading

from research.lab.certificates import verify
from research.lab.model import Invalid, loads, require

from .analysis import InvalidAnalysis, analyze, render_text
from .git_adapter import InvalidGitAnalysis, analyze_git_with_provenance
from .git_process import GitExecutionCancelled, GitInfrastructureFailure
from .git_integration_prototype import (
    InvalidGitIntegrationPrototype,
    run_prototype as run_git_integration_prototype,
)
from .git_replay import (
    InvalidGitReplay,
    produce as produce_git_replay,
    verify as verify_git_replay,
    verify_plan as verify_git_plan,
)


def _read(path: Path) -> object:
    require(path.stat().st_size <= 8_000_000, "input exceeds 8 MB")
    return loads(path.read_text(encoding="utf-8"))


def _run_cancellable_prototype(data: object) -> dict:
    cancellation = threading.Event()
    if threading.current_thread() is not threading.main_thread():
        return run_git_integration_prototype(data, cancel_event=cancellation)
    previous = {}
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, lambda _signum, _frame: cancellation.set())
        report = run_git_integration_prototype(data, cancel_event=cancellation)
        if cancellation.is_set():
            raise GitExecutionCancelled("Git integration prototype was cancelled")
        return report
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def _write_prototype_report(path: Path, serialized: str) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="analyze AIM 0.2 records")
    analyze_parser.add_argument("input", type=Path)
    analyze_parser.add_argument("--format", choices=("json", "text"), default="json")
    git_parser = subparsers.add_parser("analyze-git", help="analyze stable Git snapshots")
    git_parser.add_argument("input", type=Path)
    git_parser.add_argument("--format", choices=("json", "text"), default="json")
    git_parser.add_argument("--provenance-output", type=Path, required=True,
                            help="explicit path for the required Git provenance artifact")
    verify_parser = subparsers.add_parser("verify", help="verify a bounded certificate bundle")
    verify_parser.add_argument("input", type=Path)
    plan_git_parser = subparsers.add_parser(
        "plan-git", help="replay immutable Git commits and emit an advisory preparation plan"
    )
    plan_git_parser.add_argument("input", type=Path, help="M1 Git analysis request JSON")
    plan_git_parser.add_argument("--evidence-output", type=Path, required=True,
                                 help="explicit path for the replay evidence bundle")
    verify_git_parser = subparsers.add_parser(
        "verify-git", help="replay and verify a bounded Git evidence bundle"
    )
    verify_git_parser.add_argument("input", type=Path, help="Git replay evidence JSON")
    verify_git_parser.add_argument("--repository", type=Path, required=True,
                                   help="local source repository containing the bound commits")
    verify_plan_parser = subparsers.add_parser(
        "verify-plan", help="verify a plan against independently replayed Git evidence"
    )
    verify_plan_parser.add_argument("input", type=Path, help="consultative Git plan JSON")
    verify_plan_parser.add_argument("--evidence", type=Path, required=True,
                                    help="Git replay evidence JSON bound by the plan")
    verify_plan_parser.add_argument("--repository", type=Path, required=True,
                                    help="local source repository containing the bound commits")
    prototype_parser = subparsers.add_parser(
        "prototype-git",
        help="compare bounded parallel Git patch preparation with a serial scratch integration",
    )
    prototype_parser.add_argument("input", type=Path, help="parallel integration prototype request JSON")
    prototype_parser.add_argument("--report-output", type=Path, required=True,
                                  help="explicit path for the local prototype report")
    args = parser.parse_args(argv)
    try:
        data = _read(args.input)
        if args.command == "plan-git":
            bundle, plan = produce_git_replay(data)
            args.evidence_output.write_text(
                json.dumps(bundle, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(plan, sort_keys=True, indent=2))
            return 0
        if args.command == "verify-git":
            result = verify_git_replay(data, str(args.repository))
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0 if result["status"] == "verified" else 1
        if args.command == "verify-plan":
            result = verify_git_plan(data, _read(args.evidence), str(args.repository))
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0 if result["status"] == "verified" else 1
        if args.command == "prototype-git":
            report = _run_cancellable_prototype(data)
            serialized = json.dumps(report, sort_keys=True, indent=2) + "\n"
            _write_prototype_report(args.report_output, serialized)
            print(serialized, end="")
            return 0
        if args.command in {"analyze", "analyze-git"}:
            if args.command == "analyze":
                report = analyze(data)
            else:
                report, provenance = analyze_git_with_provenance(data)
                args.provenance_output.write_text(
                    json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8"
                )
            print(render_text(report) if args.format == "text" else
                  json.dumps(report, sort_keys=True, indent=2))
            return 0
        result = verify(data)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["status"] == "verified" else 1
    except GitInfrastructureFailure as exc:
        print(json.dumps({"status": "infrastructure-failure", "category": exc.category,
                          "reason": str(exc)}, sort_keys=True))
        return 3
    except (Invalid, InvalidAnalysis, InvalidGitAnalysis, InvalidGitReplay,
            InvalidGitIntegrationPrototype, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
