#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Reproduce public synthetic M3.5 preparation; no private sources or real yield."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time

from scripts.instrument_m35_flow import audit_capture, capture_synthetic


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/m35/m35-synthetic-sessions.json"
SUITES = (
    "tests.test_m35_source_capture", "tests.test_m35_source_window",
    "tests.test_m35_lab_export", "tests.test_m35_seal_validate",
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=30).decode().strip()


def inventory() -> dict[str, str]:
    names = set()
    for directory in ("agent_braid", "research/lab", "schemas", "examples/m35"):
        names.update(path.relative_to(ROOT).as_posix()
                     for path in (ROOT / directory).rglob("*")
                     if path.is_file() and path.suffix in {".py", ".json", ".jsonl"})
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT / "scripts").glob("m35_*.py"))
    names.update(module.replace(".", "/") + ".py" for module in SUITES)
    names.update((
        "scripts/instrument_m35_flow.py", "scripts/reproduce_m35_synthetic.py",
        "scripts/summarize_public_experiment.py", "requirements-dev.txt",
        ".github/workflows/m35-synthetic-reproduction.yml", "CONSTITUTION.md", "GOVERNANCE.md",
        "docs/adr/0018-private-source-sidecar-and-disposable-labs.md",
        "specs/019-native-predictor/spec.md", "specs/019-native-predictor/instrumentation.md",
        "specs/019-native-predictor/prospective-pilot.md",
    ))
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(names)}


def measure_capture(output_parent: Path) -> dict:
    """Include capture, audit, byte comparison and scratch cleanup in each sample."""
    frozen_capture = FIXTURE.with_name("m35-synthetic-capture.jsonl").read_bytes()
    frozen_report = json.loads(FIXTURE.with_name("m35-synthetic-report.json").read_text(encoding="utf-8"))
    samples = []
    for repetition in range(3):
        wall_start = time.monotonic_ns()
        cpu_start = time.process_time_ns()
        with tempfile.TemporaryDirectory(prefix="m35-synthetic-", dir=output_parent) as temporary:
            capture = Path(temporary) / "capture.jsonl"
            capture_synthetic(FIXTURE, capture)
            report = audit_capture(capture)
            if capture.read_bytes() != frozen_capture or report != frozen_report:
                raise ValueError("synthetic capture/report differs from the frozen public fixture")
            if report["realPairsAdmitted"] != 0 or report["executionAuthorization"] is not False:
                raise ValueError("synthetic reproduction must not admit real pairs or authorize execution")
        samples.append({"repetition": repetition + 1, "wallNs": time.monotonic_ns() - wall_start,
                        "parentCpuNs": time.process_time_ns() - cpu_start})
    return {"samples": samples, "captureSha256": hashlib.sha256(frozen_capture).hexdigest(),
            "report": report,
            "limits": ["Three descriptive synthetic capture/audit samples; uncontrolled host caches and background load.",
                       "This is tooling cost, not source yield, model training or predictor utility."]}


def run(output: Path) -> int:
    output = output.expanduser().resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("reproduction output must be outside the candidate checkout")
    if output.exists() or output.with_suffix(".txt").exists():
        raise FileExistsError("reproduction output must be new")
    if _git("status", "--porcelain"):
        raise ValueError("reproduction requires a clean frozen candidate")
    candidate = _git("rev-parse", "HEAD")
    before = inventory()
    command = [sys.executable, "-m", "unittest", "-v", *SUITES]
    wall_start = time.monotonic_ns()
    timed_out = False
    try:
        process = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=600, check=False)
        raw, code = process.stdout, process.returncode
    except subprocess.TimeoutExpired as exc:
        raw, code, timed_out = exc.output or b"", 124, True
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".txt").write_bytes(raw)
    text = raw.decode("utf-8", errors="replace")
    count = re.search(r"Ran (\d+) tests in", text)
    incomplete = [line for line in text.splitlines()
                  if " ... skipped " in line or " ... expected failure" in line]
    capture, capture_error = None, None
    try:
        capture = measure_capture(output.parent)
    except (ValueError, OSError, KeyError) as exc:
        capture_error = str(exc)
    record = {
        "m35SyntheticReproductionVersion": "0.1.0-alpha", "candidateCommit": candidate,
        "inputs": before, "candidateInputsChangedDuringRun": before != inventory(),
        "candidateWorkingTreeChangedDuringRun": bool(_git("status", "--porcelain")),
        "candidateHeadChangedDuringRun": candidate != _git("rev-parse", "HEAD"),
        "environment": {"python": platform.python_version(), "git": _git("--version"),
                        "platform": platform.system(), "machine": platform.machine()},
        "command": "python -m unittest -v " + " ".join(SUITES),
        "exitCode": code, "timedOut": timed_out, "tests": int(count.group(1)) if count else None,
        "skippedOrExpectedFailures": incomplete, "logSha256": hashlib.sha256(raw).hexdigest(),
        "capture": capture, "captureError": capture_error, "wallNs": time.monotonic_ns() - wall_start,
        "realPairsAdmitted": 0, "executionAuthorization": False,
        "limits": ["Public synthetic fixtures only; no private source, permission record, journal, participant or model credentials.",
                   "Journal, pair enumeration, filtered lab and seal checks validate tooling, not real-source completeness.",
                   "No actual remote registration, 24-hour lead-time observation or prospective capture is established.",
                   "Fresh-process reproduction on the recorded host is not independent external validation.",
                   "No labels, fitting, evaluation, utility result, scientific approval or milestone closure follows."],
    }
    if any(record[field] for field in ("candidateInputsChangedDuringRun",
                                      "candidateWorkingTreeChangedDuringRun", "candidateHeadChangedDuringRun")):
        record["status"], record["exitCode"] = "invalidated", 2
    elif code != 0 or capture_error is not None:
        record["status"], record["exitCode"] = "failed", code or 1
    elif count is None or record["tests"] == 0 or incomplete:
        record["status"], record["exitCode"] = "incomplete", 2
    else:
        record["status"] = "passed"
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "exitCode": record["exitCode"], "output": str(output)}))
    return record["exitCode"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return run(parser.parse_args().output)


if __name__ == "__main__":
    raise SystemExit(main())
