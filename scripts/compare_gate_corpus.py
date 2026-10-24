#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-052 T021: compare `analyze-git` with `git merge-tree --write-tree` on the T005 corpus.

Truth labels are the literals in tests/claude_workflow_gate_helpers.py (TRUTH), written
before any tool output is read. The baseline runs with a temporary object directory so
nothing is written to the corpus repository. Descriptive only: the result is bounded to
this corpus and claims neither H1 nor H2 beyond it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import claude_workflow_gate_helpers as fixtures  # noqa: E402

DEFAULT_OUTPUT = ROOT / "specs/052-claude-workflow-gate/evidence/corpus-comparison.json"
CLASSES = ("both-clean", "both-conflicting", "analyzer-stricter", "baseline-stricter",
           "analyzer-unknown", "baseline-unavailable", "not-comparable")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def scrub(text: str, work: Path) -> str:
    """Replace machine-specific paths so the committed evidence is reproducible."""
    work_dirs = {str(work), str(work.resolve())}
    for path in sorted(work_dirs, key=len, reverse=True):
        text = text.replace(path, "<work>")
    return text.replace(str(ROOT), "<repo>").replace(sys.executable, "python")


def request_for(corpus: fixtures.Corpus, case: fixtures.Case) -> dict:
    def operation(name: str) -> dict:
        return {"instanceId": name, "attemptId": f"{name}-1", "dependencies": [], "uncertainPaths": [],
                "source": {"kind": "commit", "revision": corpus.shas[name]}}
    return {"gitAnalysisRequestVersion": "0.1.0-alpha", "repository": str(corpus.repo),
            "baseRevision": corpus.base, "operations": [operation(case.left), operation(case.right)]}


def run_analyzer(request: dict, work: Path, stem: str) -> tuple[list[str], str | None, str | None, str]:
    """Return (command, classification, error, report sha256) from the packaged CLI."""
    request_path, provenance_path = work / f"{stem}.request.json", work / f"{stem}.provenance.json"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n")
    command = [sys.executable, "-m", "agent_braid", "analyze-git", str(request_path), "--format", "json",
               "--provenance-output", str(provenance_path)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        return command, None, scrub((result.stderr or result.stdout).strip()[:500], work), sha256(scrub(result.stdout, work).encode())
    report = json.loads(result.stdout)
    classifications = [item["classification"] for item in report["interactions"]]
    return command, classifications[0] if len(classifications) == 1 else None, None, sha256(scrub(result.stdout, work).encode())


def run_baseline(corpus: fixtures.Corpus, case: fixtures.Case, objects: Path) -> tuple[list[str], str]:
    """`merge-tree --write-tree` with objects redirected to a temporary directory."""
    command = ["git", "-C", str(corpus.repo), "merge-tree", "--write-tree", f"--merge-base={corpus.base}",
               corpus.shas[case.left], corpus.shas[case.right]]
    env = fixtures.git_env()
    env["GIT_OBJECT_DIRECTORY"] = str(objects)
    env["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(corpus.repo / ".git/objects")
    result = subprocess.run(command, env=env, capture_output=True)
    return command, {0: "clean", 1: "conflicted"}.get(result.returncode, "unavailable")


def classify(analyzer: str | None, baseline: str) -> str:
    if baseline == "unavailable":
        return "baseline-unavailable"
    if analyzer is None:
        return "not-comparable"
    if analyzer == "unknown":
        return "analyzer-unknown"
    if analyzer == "independent-candidate":
        return "both-clean" if baseline == "clean" else "baseline-stricter"
    if analyzer == "conflicting":
        return "both-conflicting" if baseline == "conflicted" else "analyzer-stricter"
    return "not-comparable"


def store_fingerprint(repo: Path) -> str:
    """Hash of refs and object-store file names, to show the repository store is unchanged."""
    refs = fixtures.git(repo, "for-each-ref").stdout
    names = sorted(str(p.relative_to(repo / ".git/objects")) for p in (repo / ".git/objects").rglob("*") if p.is_file())
    return sha256(refs + "\n".join(names).encode())


def compare(work: Path) -> dict:
    corpus = fixtures.build_corpus(work)
    store_before = store_fingerprint(corpus.repo)
    rows, inputs = [], {}
    for case in corpus.cases:
        analyzer_command, analyzer, error, report_sha = run_analyzer(request_for(corpus, case), work, case.name)
        with tempfile.TemporaryDirectory(dir=work) as objects:
            baseline_command, baseline = run_baseline(corpus, case, Path(objects))
        inputs[case.name] = sha256(scrub((work / f"{case.name}.request.json").read_text(), work).encode())
        classification = classify(analyzer, baseline)
        rows.append({
            "case": case.name, "left": {"branch": case.left, "commit": corpus.shas[case.left]},
            "right": {"branch": case.right, "commit": corpus.shas[case.right]},
            "truth": {"sharedFile": case.shared_file, "analyzer": case.analyzer, "mergeTree": case.merge_tree},
            "analyzer": {"classification": analyzer, "error": error, "command": [scrub(part, work) for part in analyzer_command],
                         "reportSha256": report_sha, "matchesTruth": analyzer == case.analyzer},
            "baseline": {"result": baseline, "command": [scrub(part, work) for part in baseline_command],
                         "matchesTruth": baseline == case.merge_tree},
            "classification": classification,
        })
    counts = {name: sum(row["classification"] == name for row in rows) for name in CLASSES}
    counterexamples = [
        {"case": row["case"], "left": row["left"]["commit"], "right": row["right"]["commit"],
         "base": corpus.base}
        for row in rows if row["analyzer"]["classification"] == "independent-candidate"
        and row["baseline"]["result"] == "conflicted"
    ]
    return {
        "evidenceVersion": "0.1.0-alpha", "task": "SPEC-052 T021", "requirement": "REQ-015 / SC-015",
        "executionAuthorization": False,
        "versions": {"git": fixtures.git_version(), "python": platform.python_version(),
                     "agentBraidSource": fixtures.git_out(ROOT, "rev-parse", "HEAD"), "platform": platform.platform()},
        "inputSha256": {"corpusBuilder": file_sha256(ROOT / "tests/claude_workflow_gate_helpers.py"),
                        "comparisonScript": file_sha256(Path(__file__)), "requests": inputs,
                        "baseCommit": corpus.base},
        "method": "Truth labels are literals in tests/claude_workflow_gate_helpers.py TRUTH, fixed before tool output was read. "
                  "Analyzer: `analyze-git` over commit sources. Baseline: `git merge-tree --write-tree --merge-base` with "
                  "GIT_OBJECT_DIRECTORY set to a temporary directory and the corpus store as alternate.",
        "repositoryStoreUnchanged": store_fingerprint(corpus.repo) == store_before,
        "denominators": {"pairs": len(rows), **counts},
        "pairs": rows,
        "counterexamples": counterexamples or "none observed in this corpus",
        "truthMismatches": [row["case"] for row in rows
                            if not (row["analyzer"]["matchesTruth"] and row["baseline"]["matchesTruth"])],
        "claims": "Descriptive for this corpus only. H1 and H2 are not claimed beyond it; a counterexample would block "
                  "conservativeness wording and is not a protocol failure. The analyzer is file-level (added/modified "
                  "writes only; delete, rename, binary and symlink yield unknown), coarser than merge-tree hunk merging, "
                  "so same-file-different-hunks is expected to be analyzer-stricter.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if not fixtures.supports_merge_tree_write_tree():
        print("git merge-tree --write-tree (Git 2.38+) is required", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as work:
        evidence = compare(Path(work))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence["denominators"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
