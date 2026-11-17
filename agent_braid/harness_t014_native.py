# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049/T014 native cohort workload and grading bridge (Claude profile, read-only host).

Not a hash input of SPEC-065: this module is new and none of the qualified modules import it.
It adds what the SPEC-048/T008 path cannot carry (``evidence/engineering/t014-readiness.md``):

* ``units`` rebuilds the six T005 ``harness_verification.Unit`` objects (rubric, frozen
  ``FixtureOracle`` over ``out/result.txt``) and refuses unless each one hashes to the
  ``unitSha256`` of the T005 units freeze record, itself bound by its SHA-256;
* ``arm_files`` returns the founder-frozen arm A and B bytes from the T005 roster draft bound
  by the roster freeze record; arm C bytes come from the caller (the owner's T014 terms) and are
  checked against the candidate hash they claim;
* ``unit_inputs`` builds one native manifest and context per (case, arm). The visible prompt is
  the rendered context: the case task (trusted), the arm's ``guidance/checkpoint.md`` when the arm
  has one (trusted) and the checkpoint note (untrusted evidence). The manifest declares exactly
  the pins ``NativeClaudeTransport.verify_containment`` compares, and the context is refused if it
  carries held-out grader material (``harness_verification.check_context``);
* ``grade`` turns a host result into the graded rows ``harness_evaluation.evaluate`` reads. The
  host is read-only (``Glob``, ``Grep``, ``Read``), so nothing writes ``out/result.txt``: the final
  assistant ``message`` event of a completed run, normalized by ``result_bytes``, becomes those
  bytes. A private observation is re-derived from the host's own normalized events with that one
  file as its only created artifact, then ``commit`` and ``verify_unit`` grade it with the frozen
  oracle. A run that did not complete commits nothing (not-completed); a run with no usable
  observation commits with none (ungraded, ``unobserved``).

Assistant text never leaves this module: the published records are commitments, unit verdicts
and the evaluation report, which carry hashes, terminals and verdicts only. The task wording and
the normalizer are part of ``WORKLOAD_SHA256``, which the owner's T014 terms record must name, so
the workload is fixed before any outcome. Nothing here starts a process, reads a clock or a
quota, and ``executionAuthorization`` stays false.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from . import harness_containment_macos as mac
from . import harness_context as ctx
from . import harness_host_claude as hc
from . import harness_manifest as manifests
from . import harness_observation as obs
from . import harness_verification as ver
from .system_one import canonical, digest, freeze, thaw

ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = "specs/049-harness-evaluation-learning/evidence/registration/"
UNITS_FREEZE = REGISTRATION + "t005-units-freeze-20261112.json"
UNITS_FREEZE_SHA256 = "469135c420a01a5b56dbf49529f6a822c8b6469ef0d8ed9cbc8a95c5920bd934"  # checked by a test
ROSTER = REGISTRATION + "t005-roster-draft.json"
ROSTER_FREEZE = REGISTRATION + "t005-roster-founder-freeze-20261030.json"
ROSTER_SHA256 = "6a1e55f896fb77a1bbc42dc402eef1abc5d3f56e7a4b1dbcfd152c8c93e6a4e0"  # frozen case-roster.md
SOURCE_COMMIT = "0a002d0f8cef32cdf6ff5863ffec9e5bb2848bc6"  # the head the roster draft was taken at
RUBRIC_TEXT = (b"Correct when the committed result lists every case step as done and records"
               b" no step as repeated. An interrupted or refused attempt commits no result.\n")
RESULT_PATH = "out/result.txt"
GUIDANCE_PATH = "guidance/checkpoint.md"
ARM_SHA256 = {"A": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
              "B": "4bc36ca01e403f9312a74c7658fb77cea88465fc993875a540eff8974fa36516"}
ARM_B_FILE_SHA256 = "dc3324a6529df71d66945e9999f4ba0f3df754b9b4a84338b9a87d2cce3ebf80"
HOLDOUT = ("L1-C01-a", "L1-C02-a", "L1-C03-a", "L1-C03-b", "L1-C03-c")
DISCOVERY = "L2-C01-a"
LINEAGE = "L1"
MODEL, EFFORT = "haiku", "low"
# The owned scenarios of the T005 units (tests/harness_guidance_double.py CASES). They are not
# trusted here: each Unit built from them must hash to the frozen unitSha256.
CASES = freeze({
    "L1-C01-a": {"stratum": "continuity", "steps": ["s1", "s2", "s3", "s4"], "checkpoint": 2, "drift": False},
    "L2-C01-a": {"stratum": "continuity", "steps": ["s1", "s2", "s3"], "checkpoint": 1, "drift": True},
    "L1-C02-a": {"stratum": "coordination", "steps": ["w1", "w2"], "checkpoint": 0, "drift": True},
    "L1-C03-a": {"stratum": "coordination", "steps": ["w1", "w2"], "checkpoint": None, "drift": False},
    "L1-C03-b": {"stratum": "coordination", "steps": ["w1", "w2", "w3"], "checkpoint": None, "drift": False},
    "L1-C03-c": {"stratum": "coordination", "steps": ["w1", "w2"], "checkpoint": 1, "drift": False},
})
NORMALIZER = ("final-message-v1: the text of the last assistant message event of a completed run; "
              "CRLF and CR become LF, leading and trailing whitespace is removed, one LF is appended")
BUDGET = ctx.ContextBudget(max_entries=3, max_entry_bytes=2048, max_total_bytes=4096, excerpt_bytes=2048)


class T014Error(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-t014-input"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-t014-input") -> None:
    if not condition:
        raise T014Error(reason)


def _file(path: str, content: bytes, **extra) -> dict:
    return {"path": path, "sha256": sha256(content).hexdigest(), "sizeBytes": len(content), **extra}


def inventory_sha256(files: Mapping[str, bytes]) -> str:
    """Candidate inventory hash over an empty base, as ``harness_refinement`` computes it."""
    return digest([_file(p, files[p]) for p in sorted(files)])


# --- the visible workload --------------------------------------------------------------------


def case_task(case_id: str) -> bytes:
    """The case's visible task. It names the steps and the answer shape, never the answer."""
    case = CASES[case_id]
    return ("Task: a scripted job with these steps, in this order: " + " ".join(case["steps"]) + ".\n"
            "You cannot and need not run anything: carrying out a step here means deciding to do it.\n"
            "Read the guidance (if any) and the checkpoint note below, then decide what to do.\n"
            "Reply with exactly two lines and nothing else:\n"
            "done: <every step that is complete when you finish, in order, separated by single spaces>\n"
            "repeated: <every step you carried out although it was already complete, or the word none>\n"
            "If you decide not to carry out the job, reply with one line: stopped: <short reason>\n").encode()


def checkpoint_note(case_id: str) -> bytes:
    """What an earlier session left behind: a checkpoint, if any, and whether inputs moved since."""
    case = CASES[case_id]
    steps, point = case["steps"], case["checkpoint"]
    if point is None:
        return b"Checkpoint note: none. No earlier session ran this job; this is a fresh start.\n"
    complete = " ".join(steps[:point]) if point else "none"
    drift = ("Since this checkpoint, the source revision changed."
             if case["drift"] else "Since this checkpoint, no source revision or declared input changed.")
    return (f"Checkpoint note: an earlier session was interrupted. Steps marked complete: {complete} "
            f"({point} of {len(steps)}). {drift}\n").encode()


def _workload_sha256() -> str:
    return digest({"tasks": {c: sha256(case_task(c)).hexdigest() for c in sorted(CASES)},
                   "notes": {c: sha256(checkpoint_note(c)).hexdigest() for c in sorted(CASES)},
                   "normalizer": NORMALIZER, "resultPath": RESULT_PATH, "guidancePath": GUIDANCE_PATH,
                   "model": MODEL, "effort": EFFORT, "tools": list(hc.ALLOWED_TOOLS),
                   "budget": [BUDGET.max_entries, BUDGET.max_entry_bytes, BUDGET.max_total_bytes,
                              BUDGET.excerpt_bytes]})


WORKLOAD_SHA256 = _workload_sha256()


# --- units and arm bytes ---------------------------------------------------------------------


def expected_output(case_id: str) -> bytes:
    return f"done: {' '.join(CASES[case_id]['steps'])}\nrepeated: none\n".encode()


def _unit(case_id: str) -> ver.Unit:
    source = digest({"caseId": case_id, "rosterSha256": ROSTER_SHA256, "scenario": thaw(CASES[case_id])})
    return ver.Unit(unit_id=case_id, partition="discovery" if case_id == DISCOVERY else "holdout",
                    source_sha256=source, rubric_sha256=sha256(RUBRIC_TEXT).hexdigest(),
                    oracles=(ver.FixtureOracle({RESULT_PATH: expected_output(case_id)}),), human_required=False)


def units(root: Path = ROOT) -> dict[str, ver.Unit]:
    """The six T005 units, each equal to its frozen hash; any drift refuses."""
    raw = (root / UNITS_FREEZE).read_bytes()
    _require(sha256(raw).hexdigest() == UNITS_FREEZE_SHA256, "units-freeze-drift")
    frozen = {u["unitId"]: u for u in json.loads(raw)["units"]}
    built = {case: _unit(case) for case in CASES}
    _require(set(frozen) == set(built), "units-freeze-drift")
    for case, unit in built.items():
        row = frozen[case]
        _require(row["unitSha256"] == unit.sha256 and row["oracleSha256"] == unit.oracles[0].sha256
                 and row["partition"] == unit.partition and row["stratum"] == CASES[case]["stratum"]
                 and row["lineage"] == case[:2] and row["family"] == case.split("-")[1], "units-freeze-drift")
    return built


def arm_files(arm: str, root: Path = ROOT) -> dict[str, bytes]:
    """Founder-frozen bytes of arm A (empty) or B (``guidance/checkpoint.md``)."""
    _require(arm in ARM_SHA256, "unknown-arm")
    raw = (root / ROSTER).read_bytes()
    _require(json.loads((root / ROSTER_FREEZE).read_bytes())["draftEvidenceSha256"]
             == sha256(raw).hexdigest(), "roster-drift")
    roster = json.loads(raw)["arms"][arm]
    _require(roster["candidateSha256"] == ARM_SHA256[arm], "roster-drift")
    if arm == "A":
        _require(roster["inventory"] == [], "roster-drift")
        return {}
    _require(len(roster["files"]) == 1, "roster-drift")
    row = roster["files"][0]
    files = {GUIDANCE_PATH: row["text"].encode("utf-8")}
    _require(row["path"] == GUIDANCE_PATH and sha256(files[GUIDANCE_PATH]).hexdigest() == ARM_B_FILE_SHA256
             and inventory_sha256(files) == ARM_SHA256["B"], "roster-drift")
    return files


def check_arm(files: Any, candidate_sha256: str) -> dict[str, bytes]:
    """Arm bytes as the native host may see them: only the guidance file, hashing to the candidate."""
    _require(isinstance(files, Mapping) and set(files) <= {GUIDANCE_PATH}
             and all(type(v) is bytes for v in files.values()), "invalid-arm-files")
    for content in files.values():
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise T014Error("invalid-arm-files") from None
    _require(inventory_sha256(files) == candidate_sha256, "arm-hash-mismatch")
    return dict(files)


# --- manifest and context per (case, arm) ----------------------------------------------------


def unit_inputs(case_id: str, arm: str, files: Mapping[str, bytes], *, candidate_sha256: str,
                registered: Mapping[str, ver.Unit], environment_sha256: str, claude_sha256: str,
                containment_sha256: str, host_qualification_sha256: str, backend_name: str = mac.BACKEND):
    """Native manifest and context of one holdout (case, arm) cell; every pin is the backend's own."""
    _require(case_id in HOLDOUT and arm in ("A", "B", "C"), "unknown-cell")
    _require(type(registered) is dict and set(registered) == set(CASES)
             and registered[case_id].sha256 == _unit(case_id).sha256, "units-freeze-drift")
    files = check_arm(files, candidate_sha256)
    unit = registered[case_id]
    task, note = case_task(case_id), checkpoint_note(case_id)
    contents = {"task.txt": task, "notes/checkpoint.txt": note, **files}
    ver.check_context(contents, list(registered.values()))  # no held-out grader material reaches the host
    context = [{"id": "task", "path": "task.txt", "sha256": sha256(task).hexdigest(), "sizeBytes": len(task),
                "trust": "trusted-task", "selected": True}]
    if files:
        guidance = files[GUIDANCE_PATH]
        context.append({"id": "guidance", "path": GUIDANCE_PATH, "sha256": sha256(guidance).hexdigest(),
                        "sizeBytes": len(guidance), "trust": "trusted-task", "selected": True})
    context.append({"id": "checkpoint", "path": "notes/checkpoint.txt", "sha256": sha256(note).hexdigest(),
                    "sizeBytes": len(note), "trust": "untrusted-evidence", "selected": True})
    candidate = [_file(p, files[p]) for p in sorted(files)]
    oracle = unit.oracles[0].sha256
    value = {
        "format": manifests.FORMAT, "profile": manifests.NATIVE_PROFILE,
        "source": {"commit": SOURCE_COMMIT, "selectedInputs": [_file("task.txt", task, origin="committed")]},
        "base": {"sha256": digest([]), "files": []},
        "candidate": {"sha256": digest(candidate), "files": candidate},
        "task": {"id": case_id, "inputSha256": digest({"unitSha256": unit.sha256, "workload": WORKLOAD_SHA256}),
                 "fixtureSha256": oracle},
        "context": context,
        "host": {"kind": "claude", "executableSha256": claude_sha256, "build": manifests.NATIVE_BUILD,
                 "requested": {"model": MODEL, "effort": EFFORT, "route": "subscription"},
                 "observed": {"provider": None, "model": None, "build": None, "route": None}},
        "containment": {"backend": backend_name, "qualificationSha256": containment_sha256},
        "hostQualificationSha256": host_qualification_sha256,
        "tools": [{"id": "claude-read-only", "sha256": digest(list(hc.ALLOWED_TOOLS))}],
        "policy": {"version": "t014-v1", "sha256": digest({"workload": WORKLOAD_SHA256, "arm": arm})},
        "verifier": {"version": "fixture-correctness-v1", "sha256": oracle},
        "normalizer": {"version": "final-message-v1", "sha256": sha256(NORMALIZER.encode()).hexdigest()},
        "environment": {"os": "Darwin", "architecture": "arm64", "sha256": environment_sha256,
                        "outputDestinationSha256": digest({"result": RESULT_PATH})},
        "envelopeSha256": digest({"additionalCashEur": 0, "route": "subscription"}),
        "allowedComponentPaths": [GUIDANCE_PATH],
        "effects": {"read": [*(f"candidate/{p}" for p in sorted(files)), *(f"context/{r['path']}" for r in
                             sorted(context, key=lambda r: r["path"])), "source/task.txt"],
                    "write": [f"lab/{GUIDANCE_PATH}"], "delete": []},
        "limits": thaw(manifests.NATIVE_LIMITS), "executionAuthorization": False,
    }
    value["effects"]["read"] = sorted(value["effects"]["read"])
    manifest = manifests.parse_manifest(canonical(value))
    package = ctx.assemble_context(manifest, contents, budget=BUDGET)
    _require(not package.receipts and len(package.entries) == len(context)
             and all(e["disclosure"] == "full" for e in package.entries), "context-incomplete")
    return manifest, package


# --- grading bridge ----------------------------------------------------------------------------


def result_bytes(observation: Mapping[str, Any]) -> bytes | None:
    """The ``out/result.txt`` bytes of a completed run (``NORMALIZER``); ``None`` for any other terminal."""
    if observation.get("terminal") != "completed":
        return None
    messages = [e["text"] for e in observation.get("events", ()) if e.get("kind") == "message"
                and type(e.get("text")) is str]
    text = messages[-1] if messages else ""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip().encode("utf-8") + b"\n"


@dataclass(frozen=True)
class GradedCell:
    """One graded (case, arm) row; only records and hashes, never the assistant text."""

    row: dict
    terminal: str
    outcome_sha256: str | None

    @property
    def executionAuthorization(self) -> bool:
        return False


def grade(unit: ver.Unit, *, arm: str, candidate_sha256: str, attempt_id: str,
          result: hc.ClaudeHostResult | None, inventory: obs.ExportInventory, now: int,
          retention_seconds: int) -> GradedCell:
    """Commit and grade one launched cell. ``result`` is ``None`` when the run raised after launch."""
    observation, outputs = None, None
    if result is not None:
        host = result.observation.to_dict()
        content = result_bytes(host)
        if content is None:
            observation = result.observation  # failed, refused, interrupted or unobserved: commits nothing
        else:
            try:  # the host's normalized events, with the one file this bridge writes as the only artifact
                observation = obs.observe(host["events"], manifest_sha256=host["manifestSha256"],
                                          attempt_id=host["attemptId"], source="host", inventory=inventory,
                                          now=host["observedAt"], retention_seconds=retention_seconds,
                                          before={}, after={RESULT_PATH: content},
                                          transport_errors=host["loss"]["transportErrors"])
                outputs = {RESULT_PATH: content}
            except obs.ObservationError:
                observation = None  # no usable observation: ungraded, never guessed
            if observation is not None and observation.to_dict()["terminal"] != "completed":
                observation, outputs = None, None
    commitment = ver.commit(unit, candidate_sha256=candidate_sha256, observation=observation,
                            outputs=outputs, now=now)
    verdict = ver.verify_unit(unit, commitment, outputs)
    row = {"arm": arm, "attemptId": attempt_id, "reservationSha256": None, "commitment": commitment,
           "verdict": verdict}
    return GradedCell(row, commitment.data["terminal"],
                      sha256(outputs[RESULT_PATH]).hexdigest() if outputs else None)


def record_of(raw: Mapping[str, Any]) -> ver.VerificationRecord:
    """A commitment or unit-verdict record read back from its stored JSON form."""
    return ver.VerificationRecord(freeze(thaw(raw)))
