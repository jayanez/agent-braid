#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Publish public synthetic experiment JSON/logs without artifact or cache storage.

Only use with public owned fixtures. Never pass private journals, source snapshots,
registration payloads, participant data, keys or model-host transcripts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import uuid


def _cell(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;").replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def publish(path: Path) -> int:
    raw = path.read_bytes()
    record = json.loads(raw)
    candidate = record.get("candidateCommit") if isinstance(record, dict) else None
    if not isinstance(candidate, str) or not re.fullmatch(r"[0-9a-f]{40}", candidate):
        raise ValueError("public experiment record requires a full candidate commit")
    status = record.get("status")
    if status not in {"passed", "failed", "incomplete", "invalidated", "captured", "descriptive-comparison"}:
        raise ValueError("public experiment record requires an explicit result status")
    digest = hashlib.sha256(raw).hexdigest()
    log = path.with_suffix(".txt")
    log_raw = log.read_bytes() if log.is_file() else None
    if log_raw is not None and record.get("logSha256") != hashlib.sha256(log_raw).hexdigest():
        raise ValueError("raw public log differs from the record digest")
    if log_raw is None and "logSha256" in record:
        raise ValueError("record-bound raw public log is missing")
    # Candidate-controlled text must not create Actions commands while being
    # displayed. The random delimiter is generated after the record was read.
    delimiter = uuid.uuid4().hex
    print(f"::stop-commands::{delimiter}")
    try:
        print(f"BEGIN_PUBLIC_EXPERIMENT_JSON {path.name} sha256={digest}")
        print(raw.decode("utf-8"), end="" if raw.endswith(b"\n") else "\n")
        print("END_PUBLIC_EXPERIMENT_JSON")
        if log_raw is not None:
            log_digest = hashlib.sha256(log_raw).hexdigest()
            print(f"BEGIN_PUBLIC_EXPERIMENT_LOG {log.name} sha256={log_digest}")
            print(log_raw.decode("utf-8", errors="replace"), end="" if log_raw.endswith(b"\n") else "\n")
            print("END_PUBLIC_EXPERIMENT_LOG")
    finally:
        print(f"::{delimiter}::")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        rows = {"Candidate": candidate, "Status": status, "Record SHA-256": digest}
        for key in ("tests", "exitCode", "realPairsAdmitted", "executionAuthorization", "utilityOutcome",
                    "baselineCommit", "candidateParallelImprovedObserved", "candidateSerialNotRegressedObserved"):
            if key in record:
                rows[key] = record[key]
        for key, value in record.get("environment", {}).items():
            rows[key] = value
        for key in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH", "GITHUB_WORKFLOW_SHA"):
            if key in os.environ:
                rows[key] = os.environ[key]
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"### Public experiment: {_cell(path.name)}\n\n")
            stream.write("| Field | Observed value |\n| --- | --- |\n")
            for key, value in rows.items():
                stream.write(f"| {_cell(key)} | {_cell(value)} |\n")
            stream.write("\nFull JSON, input hashes and available raw test output are in this step's public log.\n")
            stream.write("No artifact/cache upload, private source or real-model calls. ")
            stream.write("This record does not approve a real M3.5 capture or close M4.\n")
            for limit in record.get("limits", []):
                stream.write(f"\n- {_cell(limit)}\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    raise SystemExit(publish(parser.parse_args().record))
