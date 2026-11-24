# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-073 T010 (procedure_009): the owner's rollback drill on a fixture candidate.

Every write the drill makes lands in one scratch work directory: a temporary plugin home
(never the real one) and a scratch copy of the mapped ``SKILL.md`` (never the checkout's).
The owner runs each human-actor step with ``agent-braid lightning promote``; this script only
prepares the fixture, reads digests, runs the build check, records the evidence and cleans up.

    python -m scripts.spec073_owner_promotion setup --workdir DIR
    python -m scripts.spec073_owner_promotion digest PREVIEW.json
    python -m scripts.spec073_owner_promotion check --workdir DIR
    python -m scripts.spec073_owner_promotion evidence --workdir DIR [--out PATH]
    python -m scripts.spec073_owner_promotion cleanup --workdir DIR
    python -m scripts.spec073_owner_promotion render-doc

The fixture pairs are synthetic (OD-4: a real SPEC-072 pair is descriptive-only and never
approves), so the evidence shows the promotion, build check and rollback mechanics, not any
measured improvement. ``specs/073-lightning-promotion/drill.md`` is rendered from ``STEPS``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_braid import harness_promotion as promotion  # noqa: E402
from agent_braid import lightning_promote as lp  # noqa: E402
from agent_braid import lightning_store as store  # noqa: E402
from agent_braid import plugin_registry  # noqa: E402
from agent_braid.harness_evaluation import EvaluationRecord, _record  # noqa: E402
from agent_braid.lightning_evaluation import spec049_pair  # noqa: E402
from agent_braid.lightning_resources import sha256_text  # noqa: E402
from agent_braid.plugin_package import check_lightning_promotions  # noqa: E402

SCOPE = "lightning.skill.analyze"
RUN_ID = "drill-1"
MARKER = "spec073-drill.json"
EVIDENCE = ROOT / "specs" / "073-lightning-promotion" / "evidence" / "procedure_009.json"
# The drill test redirects the record so a fixture run never rewrites the committed evidence.
EVIDENCE_ENV = "SPEC073_DRILL_EVIDENCE"
DOC = ROOT / "specs" / "073-lightning-promotion" / "drill.md"
IDENTITY = {"sourceSha256": "d" * 64, "host": "claude-code", "model": "fixture-model",
            "toolSetSha256": "e" * 64, "policySha256": "f" * 64}
SAFE = {"unsafeAdmissions": 0, "authorityViolations": 0, "effectViolations": 0}


def _summary(verdict: str) -> dict:
    return {"hosts": {"claude-code": {"verdict": verdict, "trials": 30, "prompts": 10,
                                      "firstAttemptPrompts": 8, "withinRetryPrompts": 10}}}


def fixture_pair(candidate: str, baseline: str):
    """A synthetic SPEC-049 pair whose C-vs-A strata are all assessed noninferior (OD-4)."""
    registration, evaluation = spec049_pair(
        baseline={"arm": "A0", "candidateSha256": baseline, "canaryHits": 0, "summary": _summary("misses")},
        primary={"arm": "A2", "candidateSha256": candidate, "canaryHits": 0, "summary": _summary("meets")},
        heldout_sha256="b" * 64, protocol_sha256="c" * 64,
        costs={"A": {"rollouts": 30}, "C": {"rollouts": 30}})
    data = evaluation.to_dict()
    for stratum in data["strata"].values():
        stratum["comparisons"]["C-vs-A"]["noninferiority"] = {
            "status": "assessed", "verdict": "noninferior", "reasons": []}
    return registration, _record(EvaluationRecord, data)


def _refuse(message: str) -> None:
    raise SystemExit(f"spec073 drill refused: {message}")


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _workdir(value: str, *, new: bool) -> Path:
    workdir = Path(value).expanduser().absolute()
    real_home = plugin_registry.home_path(None).absolute()
    if _inside(workdir, real_home) or _inside(real_home, workdir):
        _refuse(f"{workdir} overlaps the real plugin home {real_home}")
    if _inside(workdir, ROOT) or _inside(ROOT, workdir):
        _refuse(f"{workdir} overlaps the checkout {ROOT}")
    if new:
        if workdir.exists():
            _refuse(f"{workdir} already exists")
    elif not (workdir / MARKER).is_file():
        _refuse(f"{workdir} has no {MARKER}; run setup first")
    return workdir


def setup(workdir: Path) -> dict:
    """Temporary home, run store with candidates A and B, scratch root, fixture JSON files."""
    workdir.mkdir(parents=True, mode=0o700)
    home, root = workdir / "home", workdir / "root"
    entry = lp.SCOPES[SCOPE]
    baseline = (ROOT / entry.target).read_text(encoding="utf-8")
    target = root / entry.target
    target.parent.mkdir(parents=True)
    target.write_text(baseline, encoding="utf-8")
    texts = {"a": baseline + "\n<!-- SPEC-073 drill fixture candidate A -->\n",
             "b": baseline + "\n<!-- SPEC-073 drill fixture candidate B -->\n"}
    run = store.RunStore(home, RUN_ID)
    run.create(config_digest="c" * 64)
    shas = {}
    for name, text in texts.items():
        shas[name] = sha256_text(text)
        run.write_candidate_text(shas[name], text)
        registration, evaluation = fixture_pair(shas[name], sha256_text(baseline))
        (workdir / f"registration-{name}.json").write_bytes(registration.canonical_bytes)
        (workdir / f"evaluation-{name}.json").write_bytes(evaluation.canonical_bytes)
    (workdir / "identity.json").write_text(json.dumps(IDENTITY, indent=2) + "\n")
    (workdir / "safety.json").write_text(json.dumps(SAFE, indent=2) + "\n")
    (workdir / "drill.env").write_text(
        f"export CAND_A={shas['a']}\nexport CAND_B={shas['b']}\nexport BASE={sha256_text(baseline)}\n")
    info = {"workdir": str(workdir), "home": str(home), "root": str(root), "runId": RUN_ID,
            "baselineSha256": sha256_text(baseline), "candidateA": shas["a"], "candidateB": shas["b"]}
    (workdir / MARKER).write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info


def digest(path: Path) -> str:
    return json.loads(Path(path).read_text(encoding="utf-8"))["previewDigest"]


def _registry(workdir: Path) -> promotion.ProfileRegistry:
    return promotion.load(lp.registry_path(workdir / "home", SCOPE))


def check(workdir: Path) -> list[str]:
    """Write the export of the drill registry into the scratch root, then run the release check."""
    root = workdir / "root"
    path = root / lp.EXPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(lp.export_bytes([_registry(workdir)]))
    try:
        check_lightning_promotions(root, release=True)
    except ValueError as exc:
        return str(exc).split("; ")
    return []


def _sha_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evidence(workdir: Path) -> dict:
    info = json.loads((workdir / MARKER).read_text())
    value = _registry(workdir)
    events = [row["event"] for row in value.journal]
    file_sha = _sha_file(workdir / "root" / lp.SCOPES[SCOPE].target)
    mismatches = check(workdir)
    expected = ["recorded", "begun", "committed", "recorded", "begun", "committed", "rolled-back"]
    passed = (events == expected and lp.active_candidate(value) == info["candidateA"] == file_sha
              and not mismatches)
    decisions = [row["subject"] for row in value.journal if row["event"] == "committed"]
    return {
        "command": "python -m scripts.spec073_owner_promotion evidence --workdir DIR "
                   "(after the drill.md steps)",
        "environment": {"platform": platform.platform(terse=True), "python": platform.python_version()},
        "inputs": {name: _sha_file(ROOT / name) for name in (
            "agent_braid/lightning_promote.py", "agent_braid/plugin_package.py",
            "scripts/spec073_owner_promotion.py", "specs/073-lightning-promotion/drill.md")},
        "limits": "Synthetic noninferior fixture pairs (OD-4) on fixture candidates A and B in a temporary "
                  "plugin home and a scratch copy of the mapped SKILL.md; shows the promotion, build check "
                  "and rollback mechanics, not a measured improvement. The build check is "
                  "check_lightning_promotions over the scratch root, not a full plugin package build.",
        "observed": {"journal": events, "committedDecisions": decisions,
                     "activeSha256": lp.active_candidate(value), "fileSha256": file_sha,
                     "registrySha256": value.sha256, "releaseCheckMismatches": mismatches,
                     "candidateA": info["candidateA"], "candidateB": info["candidateB"],
                     "baselineSha256": info["baselineSha256"]},
        "outcome": ("passed: " if passed else "failed: ")
        + "the owner promoted A then B (human decide, begin, commit), the release build check passed "
          "after each, and the rollback restored A; the active candidate equals the file digest.",
        "procedure": "procedure_009",
        "result": "OK" if passed else "FAILED",
        "scenario": "supplementary (supports SC-002, SC-004, SC-005)",
        "specification": "SPEC-073 BL.3",
    }


def cleanup(workdir: Path) -> None:
    shutil.rmtree(workdir)


# --- the drill, as the owner runs it (rendered into drill.md, executed by the test) --------

PROMOTE = ('$PY -m agent_braid lightning promote --home "$D/home" --root "$D/root" --run-id drill-1')
DRILL = "$PY -m scripts.spec073_owner_promotion"


def _promote(name: str) -> tuple[str, str]:
    upper = name.upper()
    pair = (f'--candidate "$CAND_{upper}" --registration "$D/registration-{name}.json" '
            f'--evaluation "$D/evaluation-{name}.json" --identity "$D/identity.json"')
    preview = f'{PROMOTE} {pair} > "$D/preview-{name}.json" && cat "$D/preview-{name}.json"'
    apply = (f'{PROMOTE} {pair} --apply --preview-digest "$({DRILL} digest "$D/preview-{name}.json")" '
             f'--actor owner --safety "$D/safety.json"')
    return preview, apply


STEPS = [
    ("Set up the fixture",
     "Creates the work directory with a temporary plugin home, run `drill-1` holding candidates A "
     "and B, a scratch copy of the mapped `SKILL.md`, the synthetic pair files, and `drill.env`. "
     "It refuses a directory that exists or overlaps the real plugin home or the checkout.",
     f'{DRILL} setup --workdir "$D" && . "$D/drill.env"', 0, '"candidateA"'),
    ("Preview promoting candidate A",
     "Read the preview: `candidateSha256` is `$CAND_A`, `currentSha256` is null, `blockers` is "
     "empty and `requiredDecision` is `approved`. Nothing is written.",
     _promote("a")[0], 0, '"blockers": []'),
    ("Decide, begin and commit candidate A",
     "Your human decision: apply with the digest of the preview you read. Expect `status` "
     "`committed` and `fileSha256After` equal to `$CAND_A`.",
     _promote("a")[1], 0, '"status": "committed"'),
    ("Rebuild check after A",
     "Exports the drill registry into the scratch root and runs the release build check. Expect "
     "`release check passed`.",
     f'{DRILL} check --workdir "$D"', 0, "release check passed"),
    ("Preview promoting candidate B",
     "Expect `currentSha256` `$CAND_A`, `candidateSha256` `$CAND_B` and no blockers.",
     _promote("b")[0], 0, '"blockers": []'),
    ("Decide, begin and commit candidate B",
     "Expect `status` `committed` and `fileSha256After` equal to `$CAND_B`.",
     _promote("b")[1], 0, '"status": "committed"'),
    ("Rebuild check after B",
     "Expect `release check passed`.",
     f'{DRILL} check --workdir "$D"', 0, "release check passed"),
    ("Preview the rollback",
     "Expect `action` `rollback`, `currentSha256` `$CAND_B`, `candidateSha256` `$CAND_A`, `reason` "
     "`owner-rollback` and `requiredDecision` `human-apply`. Nothing is written.",
     f'{PROMOTE} --rollback > "$D/preview-rollback.json" && cat "$D/preview-rollback.json"', 0,
     '"action": "rollback"'),
    ("Apply the rollback",
     "Your human decision: apply with the rollback preview's digest. Expect `status` `applied` and "
     "`activeSha256` equal to `$CAND_A`.",
     f'{PROMOTE} --rollback --apply --preview-digest "$({DRILL} digest "$D/preview-rollback.json")"', 0,
     '"status": "applied"'),
    ("Rebuild check after the rollback",
     "Expect `release check passed`.",
     f'{DRILL} check --workdir "$D"', 0, "release check passed"),
    ("Record the evidence",
     "Writes `specs/073-lightning-promotion/evidence/procedure_009.json` with the journal, the "
     "committed decisions, the active and file digests and the check result. Expect `result OK`. "
     "Commit that file in the T010 evidence PR.",
     f'{DRILL} evidence --workdir "$D"', 0, "result OK"),
    ("Clean up",
     "Removes the work directory (it refuses one that `setup` did not create).",
     f'{DRILL} cleanup --workdir "$D"', 0, "removed"),
]


def render_doc() -> str:
    lines = [
        "# SPEC-073 T010: owner rollback drill",
        "",
        "<!-- Rendered by `python -m scripts.spec073_owner_promotion render-doc`; edit STEPS there. -->",
        "",
        "This drill is procedure_009. You run every step; each human decision is an `--apply` with the",
        "digest of the preview you just read. It promotes fixture candidate A, then B, rebuilds the",
        "build check after each, and rolls back to A. Every write lands in one scratch work",
        "directory: a temporary plugin home and a scratch copy of the mapped `SKILL.md`. The real",
        "plugin home and the checkout's `SKILL.md` are never touched. The pairs are synthetic",
        "(OD-4), so the evidence covers the mechanics, not a measured improvement. Revocation is not",
        "part of T010.",
        "",
        "Run the steps in one shell from the repository root:",
        "",
        "```bash",
        "PY=python3.13",
        'D="$(mktemp -d)/spec073-drill"',
        "```",
        "",
    ]
    for number, (title, expect, command, _, _) in enumerate(STEPS, 1):
        lines += [f"## {number}. {title}", "", expect, "", "```bash", command, "```", ""]
    lines += [
        "Any refusal prints one line `lightning promote refused (<reason>)` and exits 2; stop and",
        "report it. A test (`tests/test_spec073_owner_drill.py`) runs these exact commands on a",
        "fixture, so this page stays in step with the code.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("setup", "check", "evidence", "cleanup"):
        command = sub.add_parser(name)
        command.add_argument("--workdir", required=True)
        if name == "evidence":
            command.add_argument("--out", type=Path, default=Path(os.environ.get(EVIDENCE_ENV, EVIDENCE)))
    sub.add_parser("digest").add_argument("preview", type=Path)
    sub.add_parser("render-doc")
    args = parser.parse_args(argv)
    if args.command == "setup":
        print(json.dumps(setup(_workdir(args.workdir, new=True)), indent=2, sort_keys=True))
    elif args.command == "digest":
        print(digest(args.preview))
    elif args.command == "check":
        lines = check(_workdir(args.workdir, new=False))
        print("\n".join(lines) if lines else "release check passed")
        return 1 if lines else 0
    elif args.command == "evidence":
        record = evidence(_workdir(args.workdir, new=False))
        args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        print(f"result {record['result']}: {args.out}")
        return 0 if record["result"] == "OK" else 1
    elif args.command == "cleanup":
        workdir = _workdir(args.workdir, new=False)
        cleanup(workdir)
        print(f"removed {workdir}")
    else:
        sys.stdout.write(render_doc())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
