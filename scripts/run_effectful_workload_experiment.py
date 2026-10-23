#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run SPEC-024's frozen stdlib-only local simulation protocol."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Direct script invocation uses the repository's inert experimental package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.workload_lab.analysis import run_experiment
from research.workload_lab.__main__ import load_file, write_exclusive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--registration", help="Defaults to registration.json beside the manifest")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    registration = args.registration or str(Path(args.manifest).with_name("registration.json"))
    try:
        manifest = load_file(args.manifest)
        frozen = load_file(registration)
        report = run_experiment(manifest, frozen, command=["scripts/run_effectful_workload_experiment.py", *(sys.argv[1:] if argv is None else argv)])
        data = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"
        write_exclusive(args.output, data, args.manifest)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"experiment rejected: {exc}\n")
    print(json.dumps({"output": args.output, "feasibility": report["feasibility"]["status"], "executionAuthorization": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
