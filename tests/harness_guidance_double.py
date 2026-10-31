# SPDX-License-Identifier: AGPL-3.0-only
"""Guidance-reading solver double for SPEC-049 T005 R13: a ``synthetic-control`` only.

An engineering positive control, not native evidence and never a D4 verdict input. It
shows that candidate guidance can reach a solver, so arms A (empty inventory) and B
(``guidance/checkpoint.md``) become distinguishable on the frozen roster cases. It does
not show that any guidance is better.

The closed grammar, its mapping to behaviour switches, the directive-absent defaults, the
per-case scenarios and the code applying them are frozen in ``CONTROL_SHA256`` at import
and re-checked on every run. Only exact
directive lines switch behaviour; unknown or reworded lines change nothing. The double
reads only ``GUIDANCE_PATH`` from a candidate whose inventory hash the caller declares,
and refuses a mismatch. Scenarios are owned abstractions of the anchor tests, not the
anchors themselves. No host, model, network, clock or paid route is used, and records
carry ``verdictEligible`` and ``executionAuthorization`` false.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import inspect
import json
from pathlib import Path
from typing import Any

from agent_braid.system_one import canonical, digest, freeze, thaw

FORMAT = "braid-harness-guidance-double/v0.1"
LABEL = "synthetic-control"
GUIDANCE_PATH = "guidance/checkpoint.md"
_REGISTRATION = (Path(__file__).resolve().parents[1]
                 / "specs/049-harness-evaluation-learning/evidence/registration")
ROSTER = _REGISTRATION / "t005-roster-draft.json"  # arm bytes; frozen by hash in FREEZE
FREEZE = _REGISTRATION / "t005-roster-founder-freeze-20261030.json"
ARM_B_FILE_SHA256 = "dc3324a6529df71d66945e9999f4ba0f3df754b9b4a84338b9a87d2cce3ebf80"
ARM_SHA256 = {"A": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
              "B": "4bc36ca01e403f9312a74c7658fb77cea88465fc993875a540eff8974fa36516"}

# Exact arm-B directive lines -> behaviour switch. Its other lines map to nothing.
GRAMMAR = freeze({
    "- After an interruption, read the latest checkpoint and resume at the first step it "
    "does not mark complete. Do not repeat completed steps.": "resume-from-checkpoint",
    "- If the source revision or a declared input changed since the checkpoint, stop and "
    "report the drift instead of continuing.": "stop-on-drift",
})
DEFAULTS = freeze({"resume-from-checkpoint": False, "stop-on-drift": False})
# checkpoint: steps complete before an interruption (None: fresh start); drift: an input
# changed since that checkpoint. Strata follow roster R4; L3-C02-a is unassigned (R3).
CASES = freeze({
    "L1-C01-a": {"stratum": "continuity", "steps": ["s1", "s2", "s3", "s4"],
                 "checkpoint": 2, "drift": False},
    "L2-C01-a": {"stratum": "continuity", "steps": ["s1", "s2", "s3"],
                 "checkpoint": 1, "drift": True},
    "L1-C02-a": {"stratum": "coordination", "steps": ["w1", "w2"],
                 "checkpoint": 0, "drift": True},
    "L1-C03-a": {"stratum": "coordination", "steps": ["w1", "w2"],
                 "checkpoint": None, "drift": False},
    "L1-C03-b": {"stratum": "coordination", "steps": ["w1", "w2", "w3"],
                 "checkpoint": None, "drift": False},
    "L1-C03-c": {"stratum": "coordination", "steps": ["w1", "w2"],
                 "checkpoint": 1, "drift": False},
})


class GuidanceDoubleError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise GuidanceDoubleError(reason)


@dataclass(frozen=True)
class GuidanceDoubleRecord:
    """Immutable synthetic-control result; ``sha256`` binds its canonical bytes."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        return thaw(self.data)


def inventory_sha256(files: Mapping[str, bytes]) -> str:
    """Inventory hash over an empty base, as ``harness_refinement._candidate_hash`` computes."""
    return digest([{"path": p, "sha256": sha256(files[p]).hexdigest(), "sizeBytes": len(files[p])}
                   for p in sorted(files)])


def arm_files(arm: str) -> dict[str, bytes]:
    """Founder-frozen bytes for arm A or B, read from the draft the freeze record binds."""
    _require(arm in ARM_SHA256, "unknown-arm")
    raw = ROSTER.read_bytes()
    freeze_record = json.loads(FREEZE.read_text(encoding="utf-8"))
    _require(freeze_record["draftEvidenceSha256"] == sha256(raw).hexdigest(), "roster-drift")
    roster = json.loads(raw)["arms"][arm]
    _require(roster["candidateSha256"] == ARM_SHA256[arm], "roster-drift")
    if arm == "A":
        _require(roster["inventory"] == [], "roster-drift")
        return {}
    _require(len(roster["files"]) == 1, "roster-drift")
    row = roster["files"][0]
    content = row["text"].encode("utf-8")
    files = {GUIDANCE_PATH: content}
    _require(row["path"] == GUIDANCE_PATH and row["sizeBytes"] == len(content)
             and sha256(content).hexdigest() == ARM_B_FILE_SHA256
             and inventory_sha256(files) == ARM_SHA256["B"], "roster-drift")
    return files


def _switches(files: Mapping[str, bytes]) -> dict[str, bool]:
    switches = dict(DEFAULTS)
    if GUIDANCE_PATH not in files:
        return switches
    try:
        text = files[GUIDANCE_PATH].decode("utf-8")
    except UnicodeDecodeError:
        raise GuidanceDoubleError("invalid-guidance") from None
    for line in text.split("\n"):  # only LF ends a line
        if line in GRAMMAR:
            switches[GRAMMAR[line]] = True
    return switches


def _simulate(case: Mapping[str, Any], switches: Mapping[str, bool]) -> dict:
    steps, checkpoint = case["steps"], case["checkpoint"]
    events: list[dict] = [{"kind": "start"}]
    if checkpoint is not None and case["drift"] and switches["stop-on-drift"]:
        events.append({"kind": "message", "text": "drift-reported"})
        executed, terminal = [], "interrupted"
    else:
        start = checkpoint if checkpoint is not None and switches["resume-from-checkpoint"] else 0
        executed, terminal = list(steps[start:]), "completed"
        events += [{"kind": "message", "text": f"run:{step}"} for step in executed]
    events.append({"kind": "terminal", "state": terminal})
    done = steps[:checkpoint or 0]
    return {"events": [{"seq": i, **e} for i, e in enumerate(events)], "terminal": terminal,
            "executed": executed, "repeated": [s for s in executed if s in done]}


def _control_sha256() -> str:
    """Digest of the grammar, mapping, defaults, cases and the code that applies them."""
    return digest({"format": FORMAT, "label": LABEL, "guidancePath": GUIDANCE_PATH,
                   "grammar": GRAMMAR, "defaults": DEFAULTS, "cases": CASES,
                   "code": [inspect.getsource(f) for f in (_switches, _simulate)]})


CONTROL_SHA256 = _control_sha256()


def run(case_id: str, files: Mapping[str, bytes], *, candidate_sha256: str
        ) -> GuidanceDoubleRecord:
    """Run one frozen case against candidate guidance; refuse, never repair."""
    _require(_control_sha256() == CONTROL_SHA256, "control-drift")
    _require(case_id in CASES, "unknown-case")
    _require(isinstance(files, Mapping) and all(type(v) is bytes for v in files.values()),
             "invalid-candidate")
    _require(set(files) <= {GUIDANCE_PATH}, "path-not-allowed")
    _require(inventory_sha256(files) == candidate_sha256, "guidance-hash-mismatch")
    switches = _switches(files)
    case = CASES[case_id]
    record = {"format": FORMAT, "label": LABEL, "caseId": case_id, "stratum": case["stratum"],
              "candidateSha256": candidate_sha256, "controlSha256": CONTROL_SHA256,
              "switches": sorted(k for k, v in switches.items() if v),
              **_simulate(case, switches),
              "verdictEligible": False, "executionAuthorization": False}
    return GuidanceDoubleRecord(freeze(record), canonical(record))


def blind_fixture(case_id: str) -> bytes:
    """A ``harness_lab`` fixture replaying the case's default behaviour; it reads no input."""
    _require(case_id in CASES, "unknown-case")
    events = _simulate(CASES[case_id], DEFAULTS)["events"]
    source = f"import json\nfor e in json.loads({json.dumps(events)!r}):\n    print(json.dumps(e))\n"
    return source.encode()
