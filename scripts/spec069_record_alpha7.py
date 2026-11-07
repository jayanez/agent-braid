# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T009: record what plugin 0.1.0-alpha.7 does with a fixed set of aim requests.

The alpha.7 runtime is extracted from Git (source commit 0eb75d84, the commit the
published dist was built from) into a temporary directory and run in a
subprocess, so the baseline never depends on the working tree. The evidence file
stores, per request, the request digest and the alpha.7 verdict and report digest.

    python -m scripts.spec069_record_alpha7            # write
    python -m scripts.spec069_record_alpha7 --check    # fail when the committed file differs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALPHA7_COMMIT = "0eb75d84"
OUTPUT = ROOT / "specs/069-aim-request-authoring/evidence/alpha7-replay.json"
CORPUS = ROOT / "tests/fixtures/analysis-requests/aim.json"
FILES = (
    ["examples/analysis/file-edits.json", "examples/analysis/file-edits-conflict.json",
     "examples/aim/file-edits.json", "examples/contracts/0.2.0-draft/aim.json"]
    + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "examples/workloads").glob("*.json"))
)
# SPEC-068 T010 row 16: the call the OpenCode model made first (refused in alpha.7).
T010_F1 = {"units": [{"id": "a", "writes": ["README.md"]}, {"id": "b", "writes": ["README.md"]}]}

RUNNER = r'''
import hashlib, json, sys, tempfile, threading
from pathlib import Path
from agent_braid.tooling_mcp import ToolingConfig, ToolingService

requests = json.loads(Path(sys.argv[1]).read_text())
with tempfile.TemporaryDirectory() as tmp:
    source, results = Path(tmp) / "source", Path(tmp) / "results"
    source.mkdir(); results.mkdir()
    service = ToolingService(ToolingConfig(source, results))
    out = []
    for item in requests:
        envelope = service.invoke("analyze-work", {"kind": "aim", "request": item["request"]}, threading.Event())
        entry = {"id": item["id"], "status": envelope["status"]}
        if envelope["status"] == "ok":
            report = envelope["result"]["report"]
            entry["reportSha256"] = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            entry["analysisId"] = report["analysisId"]
        out.append(entry)
print(json.dumps(out))
'''


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def requests() -> list[dict]:
    """The fixed request set: example files, workloads, the T010 first attempt and every aim corpus case."""
    items = []
    for name in FILES:
        items.append({"id": f"file:{name}", "request": json.loads((ROOT / name).read_text())})
    items.append({"id": "literal:t010-f1-units", "request": T010_F1})
    for case in json.loads(CORPUS.read_text())["cases"]:
        items.append({"id": f"corpus:{case['id']}", "request": case["request"]})
    return items


def record() -> dict:
    items = requests()
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "alpha7"
        tree.mkdir()
        archive = subprocess.run(["git", "archive", ALPHA7_COMMIT, "agent_braid", "research"], cwd=ROOT, check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", str(tree)], input=archive, check=True)
        data = Path(tmp) / "requests.json"
        data.write_text(json.dumps(items))
        process = subprocess.run([sys.executable, "-c", RUNNER, str(data)], cwd=tree, check=True,
                                 capture_output=True, text=True, env={"PYTHONPATH": str(tree), "PATH": "/usr/bin:/bin"})
    results = {entry["id"]: entry for entry in json.loads(process.stdout)}
    commit = subprocess.run(["git", "rev-parse", ALPHA7_COMMIT], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    entries = []
    for item in items:
        entry = results[item["id"]]
        entries.append({"id": item["id"], "requestSha256": canonical_sha(item["request"]),
                        **{k: v for k, v in entry.items() if k != "id"}})
    accepted = sum(1 for e in entries if e["status"] == "ok")
    return {
        "recordVersion": "1",
        "specification": "SPEC-069 T009 / REQ-009",
        "baseline": {"plugin": "0.1.0-alpha.7", "sourceCommit": commit, "tag": "agent-braid--v0.1.0-alpha.7"},
        "method": "alpha.7 runtime extracted with git archive and run in an isolated subprocess through ToolingService.invoke('analyze-work')",
        "counts": {"requests": len(entries), "accepted": accepted, "notAccepted": len(entries) - accepted},
        "entries": entries,
    }


def render(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render(record())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != text:
            print("alpha7-replay.json is stale; rerun without --check", file=sys.stderr)
            return 1
        print("alpha7-replay.json is current")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text)
    doc = json.loads(text)
    print(doc["counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
