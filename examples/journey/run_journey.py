#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run the owned synthetic tooling journey with one command and print a receipt.

    .venv/bin/python examples/journey/run_journey.py [--output receipt.json]

Install, discovery, analysis, plan, grant refusal, interrupted execution,
recovery, verification, export and uninstall run against one temporary Git
fixture through the existing public entry points. No host connection, network,
model call or real project is involved. The only grants are issued by this
script acting as a *local test operator* through the core policy API, never by
a tool or skill; the tooling service itself holds no issuer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch

if not __debug__:  # the checks below are assert statements
    raise SystemExit("run without -O so the journey checks are not stripped")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_braid import git_runtime, runtime_policy, tooling_present as presentation  # noqa: E402
from agent_braid.git_process import GitExecutionCancelled  # noqa: E402
from agent_braid.tooling_assets import load_skill_bundle  # noqa: E402
from agent_braid.tooling_fixtures import load_inventory, materialize_fixture  # noqa: E402
from agent_braid.tooling_install import Selection, apply, plan  # noqa: E402
from agent_braid.tooling_mcp import ToolingConfig, ToolingService  # noqa: E402

FIXTURE_ID = "m45-inspect-recover-interruption-01"
EXPECTED_TOOLS = {"analyze-work", "analyze", "prepare", "status", "execute", "recover", "verify"}
LIMITS = (
    "Synthetic local control, not actual-host observation, native discovery, "
    "user approval, provider call or M4.5 evaluation attempt.",
    "Grants are test-operator grants on owned temporary roots; no model or tool issues authority.",
    "Hashes embed per-run temporary paths: they bind one run, not comparable across runs.",
    "Structural checks only; no claim of general concurrency safety or speedup.",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_journey() -> dict:
    inventory = load_inventory(source_checkout=True)
    steps: list[dict] = []
    controls: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="agent-braid-journey-") as temporary:
        root = Path(temporary).resolve()
        fixture = materialize_fixture(inventory, FIXTURE_ID, root / "fixture")
        results, grants = root / "results", root / "grants"
        results.mkdir(mode=0o700)
        grants.mkdir(mode=0o700)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

        def source_identity() -> bytes:
            return subprocess.check_output(
                ["git", "-C", str(fixture.repository_root), "rev-parse", "HEAD", "HEAD^{tree}"],
                env=env, timeout=30)

        original = source_identity()

        def record(step: str, **fields) -> None:
            steps.append({"step": step, "outcome": "passed", **fields})

        # 1. Install into isolated destinations (preview first, then apply).
        selections = []
        for host in ("codex", "claude"):
            selection = Selection(host, "user", fixture.repository_root, results,
                                  grant_store=grants, enable_runtime=True,
                                  destination=root / (host + " isolated assets"))
            transaction = plan(selection, source_checkout=True)
            assert not selection.destination.exists(), "preview must not write"
            apply(transaction, preview_digest=transaction.preview()["previewDigest"])
            assert plan(selection, source_checkout=True).changes == [], "install not idempotent"
            selections.append(selection)
        record("install", hosts=["codex", "claude"], previewBeforeApply=True)

        # 2. Discovery: installed skill bytes match the packaged bundle; catalog is exact.
        bundle = load_skill_bundle(source_checkout=True)
        for selection in selections:
            _, skills, _ = selection.paths()
            assert len(list(skills.glob("*/SKILL.md"))) == len(bundle.skills) == 5
            for skill in bundle.skills:
                assert skill.sha256 == _sha((skills / skill.name / "SKILL.md").read_bytes())
        service = ToolingService(ToolingConfig(fixture.repository_root, results, grants, True))
        tools = set(service.capabilities()["tools"])
        assert tools == EXPECTED_TOOLS, tools
        record("discovery", skillCount=len(bundle.skills),
               skillSha256={s.name: s.sha256 for s in bundle.skills}, tools=sorted(tools))
        assert "grant" not in " ".join(service.tools), "a grant tool is exposed"
        controls.append({"name": "no-grant-tool-exposed", "held": True})

        event = threading.Event()
        # 3. Analysis.
        analyzed = service.invoke("analyze-work", {"kind": "git", "request": fixture.analysis_request}, event)
        assert analyzed["status"] == "ok"
        assert "independent-candidate" in presentation.render_summary(analyzed)
        record("analysis", toolStatus=analyzed["status"],
               envelopeSha256=_sha(presentation.canonical_json(analyzed)))

        # 4. Plan (advisory; creates no run and no authority).
        run_dir = results / "run"
        prepared = service.invoke("prepare", {"request": fixture.request,
                                              "runDirectory": str(run_dir), "mode": "serial"}, event)
        assert prepared["status"] == "ok" and not run_dir.exists()
        bounded = prepared["result"]
        record("plan", toolStatus=prepared["status"], planDigest=bounded["planDigest"],
               runCreated=False)

        # 5. Grant refusal: an unissued identifier must be refused and change nothing.
        refused = service.invoke("execute", {"plan": bounded, "grantId": "synthetic-unissued-grant"}, event)
        assert refused["status"] == "refused" and not run_dir.exists()
        no_grants = list(grants.iterdir()) == []
        assert no_grants
        controls.append({"name": "unissued-grant-refused", "held": True})
        try:
            runtime_policy.issue_operator_grant(bounded, grants, acknowledge="0" * 64)
            held = False
        except runtime_policy.InvalidRuntimePolicy:
            held = list(grants.iterdir()) == []
        assert held, "mismatched acknowledgement must not issue a grant"
        controls.append({"name": "mismatched-acknowledgement-refused", "held": True})
        record("grant-refusal", toolStatus=refused["status"], runCreated=False,
               grantsIssued=False)

        # 6. Local test operator grants the exact inspected plan; execution is interrupted
        #    at a committed checkpoint so recovery is real, not simulated.
        grant = runtime_policy.issue_operator_grant(bounded, grants, acknowledge=bounded["planDigest"])
        original_write = git_runtime._atomic_json
        interrupted = False

        def checkpoint_interruption(directory, name, value):
            nonlocal interrupted
            original_write(directory, name, value)
            if name == "state.json" and value.get("phase") == "ready" and value.get("nextIndex") == 1:
                interrupted = True
                raise GitExecutionCancelled("owned journey checkpoint control")

        with patch("agent_braid.git_runtime._atomic_json", side_effect=checkpoint_interruption):
            stopped = service.invoke("execute", {"plan": bounded, "grantId": grant["grantId"]}, event)
        assert interrupted and stopped["status"] in {"unknown", "refused"}
        inspected = service.invoke("status", {"plan": bounded}, event)
        prefix = inspected["result"]["runtime"]["status"]
        assert prefix in {"verified-prefix", "unknown"}, prefix
        record("execute-interrupted", toolStatus=stopped["status"], inspectedStatus=prefix,
               interruptedAtCheckpoint=True)

        # 7. Separate resume grant, then recovery.
        resume_grant = runtime_policy.issue_operator_grant(
            bounded, grants, acknowledge=bounded["planDigest"], action="resume")
        recovered = service.invoke("recover", {"plan": bounded, "grantId": resume_grant["grantId"],
                                               "action": "resume"}, event)
        assert recovered["status"] == "ok", recovered["summary"]
        record("recover", toolStatus=recovered["status"], action="resume",
               distinctGrant=resume_grant["grantId"] != grant["grantId"])

        # 8. Verify result tree against the fixture's expected tree; source untouched.
        verified = service.invoke("verify", {"plan": bounded}, event)
        runtime = verified["result"]["runtime"]
        assert runtime["status"] == "verified-completed"
        assert runtime["resultTree"] == fixture.request["expectedFinalTree"]
        assert "verified-completed" in presentation.render_summary(verified)
        source_unchanged = original == source_identity()
        assert source_unchanged
        record("verify", runtimeStatus=runtime["status"], resultTreeMatchesExpected=True)

        # 9. Export the complete verified envelope; bytes must be reproducible on disk.
        expected = presentation.build_exports(verified, selected_evidence_refs=[])
        presentation.write_exports(verified, root / "export", selected_evidence_refs=[])
        deterministic = all((root / "export" / name).read_bytes() == raw for name, raw in expected.items())
        assert deterministic
        assert json.loads(expected["evidence.json"]) == verified, "export is not the complete envelope"
        record("export", deterministic=True,
               files={name: _sha(raw) for name, raw in sorted(expected.items())})

        # 10. Uninstall removes only installed assets.
        for selection in selections:
            removal = plan(selection, operation="uninstall", source_checkout=True)
            apply(removal, preview_digest=removal.preview()["previewDigest"])
            assert plan(selection, operation="uninstall", source_checkout=True).changes == []
        assert original == source_identity()
        record("uninstall", assetsRemoved=True)

    return {
        "receiptVersion": "1",
        "task": "SPEC-043/T001",
        "domain": "synthetic-local",
        "fixtureId": FIXTURE_ID,
        "status": "passed" if all(s["outcome"] == "passed" for s in steps)
                  and all(c["held"] for c in controls) else "failed",
        "hostConnection": False,
        "networkUsed": False,
        "modelSpend": False,
        "executionAuthorization": False,
        "executionAuthorizationNote": "The tooling service and skills issue no authority; "
                                      "grants come only from the local test operator in this script.",
        "sourceUnchanged": source_unchanged,
        "steps": steps,
        "negativeControls": controls,
        "limits": list(LIMITS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, help="also write the receipt JSON here")
    args = parser.parse_args(argv)
    try:
        receipt = run_journey()
    except AssertionError as error:
        print(f"journey failed: {error!r}", file=sys.stderr)
        return 1
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
