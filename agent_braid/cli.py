# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only Agent Braid CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.lab.certificates import verify
from research.lab.model import Invalid, loads, require

from .analysis import InvalidAnalysis, analyze, render_text
from .git_adapter import InvalidGitAnalysis, analyze_git_with_provenance
from .git_replay import InvalidGitReplay, produce as produce_git_replay, verify as verify_git_replay


def _read(path: Path) -> object:
    require(path.stat().st_size <= 8_000_000, "input exceeds 8 MB")
    return loads(path.read_text(encoding="utf-8"))


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
    except (Invalid, InvalidAnalysis, InvalidGitAnalysis, InvalidGitReplay, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
