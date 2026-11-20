#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Operator-run driver for the SPEC-049/T014 native cohort (Claude profile, Haiku, read-only host).

NOT an authorization. Sibling of ``scripts/har_t008_unit.py``: it runs as the dedicated lab account in that
account's own ``Background`` session, started by the root launcher ``scripts/har_t014_launch.sh`` (installed as
``/usr/local/libexec/braid/t014-launch.sh``). It reuses the SPEC-065 T009 pre-flight, then:

* ``--dry-run``: pre-flight, then every no-quota check (``admit``): the pinned issuance, its environment hash
  recomputed in this session, the qualified policy, the MDRV-04 guard, the hash-pinned T004 admission and T014
  terms records and their cross-references, the founder's host-profile decision and the D2 caps, the registration
  (the frozen T005 units, arms A/B/C, the native profile), the window, the cohort unit cap and the slots left.
  Nothing native runs;
* ``--founder-go``: runs the registered Latin-square order (``harness_evaluation.register``: units by id, arms
  rotated within each task family), at most ``--units`` slots this attempt. Each slot asks for the usage card
  before and after, admits through ``HostQualificationRun``, runs one read-only Haiku session on the
  ``harness_t014_native`` workload and grades it in-process with the frozen ``FixtureOracle``. Any stop ends the
  attempt; a later label resumes at the first slot no attempt started.

Pins: the SPEC-065 issuance (with its environment document and trusted record hashes), the SPEC-049/T004
admission record, the T014 terms record and the host-profile decision record are each bound by a SHA-256 below.
The issuance is the 2026-11-17 one (the same pins as SPEC-048/T008). The admission, terms and host-profile
records are the owner's 2026-11-20 records (``evidence/native-admission/`` and ``evidence/registration/``); a
placeholder (``pending``) still refuses as ``<name>-not-pinned``. The unit cap is the pinned input ``UNIT_CAP`` = 16 (owner decision 2026-11-17, D2
per-cohort cap: T014 has its own 16 and SPEC-048/T008 units do not count toward it); the terms record must repeat
it, and the D2 cap-scope record that carries it is pinned by SHA-256 (``CAP_DECISION``). Every
attempt counts its started units and slots in ``<out-dir>/t014-units.json`` right before each launch, and every
later attempt subtracts them.

Output: the JSON report carries the fixed host summary of each run, the slot outcomes (``correct``, ``incorrect``,
``ungraded``, ``not-completed``) and the ``harness_evaluation.evaluate`` report over every row of every attempt so
far, with ``verdictEligible`` false and every cost ``unknown``. Assistant text is never printed or stored outside
the lab process. ``executionAuthorization`` is false in every output.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import har_t008_unit as t8  # noqa: E402  (reused unchanged: usage readings and the host summary)
import har_t009_attempt as t9  # noqa: E402
from agent_braid import harness_containment_macos as _mac  # noqa: E402
from agent_braid import harness_evaluation as ev  # noqa: E402
from agent_braid import harness_host_claude as hc  # noqa: E402
from agent_braid import harness_hosts as hh  # noqa: E402
from agent_braid import harness_hosts_native as hn  # noqa: E402
from agent_braid import harness_qualification_probes as _probes  # noqa: E402
from agent_braid import harness_t014_native as tn  # noqa: E402
from agent_braid.harness_observation import verify_inventory  # noqa: E402
from agent_braid.harness_refinement import RefinementDecision  # noqa: E402
from agent_braid.system_one import InvalidDecision, canonical, freeze, parse_json  # noqa: E402

PENDING = "pending"  # a placeholder: not 64 hex, so the record it stands for refuses
# SPEC-065 T015 issuance of 2026-11-17 (attempt t009-20261117c); the same pins SPEC-048/T008 uses
ISSUANCE, ISSUANCE_SHA256 = t8.ISSUANCE, t8.ISSUANCE_SHA256
ENVIRONMENT = t8.ENVIRONMENT
TRUSTED = dict(t8.TRUSTED)
_EVIDENCE = "specs/049-harness-evaluation-learning/evidence/"
# the host-profile decisions for T014: the SPEC-048/T008 Claude verdict T008-11 (qualified with limits), 2026-11-20
PROFILE_DECISIONS = _EVIDENCE + "registration/t014-profile-decisions-20261120.json"
PROFILE_DECISIONS_SHA256 = "36149af6808b1f71bc869e2d4bddc53002c12cca44e45d40680bf13ae2675806"
# SPEC-049/T004 admission (owner, "Admit", 2026-11-20) and the T014 cohort terms (owner, plan P2, 2026-11-20)
ADMISSION = _EVIDENCE + "native-admission/t004-admission-20261120.json"
ADMISSION_SHA256 = "7a1b1a5a18949f54bad47e1805760f1bf917d7b339ae2550eebc1fa17c1d83f3"
TERMS = _EVIDENCE + "registration/t014-terms-20261120.json"
TERMS_SHA256 = "ef68417637be2c5b881ce95227eb0943ad4fedd98bb5498d1506b910612c68f1"
D2_CAPS = t8.D2_CAPS
D2_CAPS_SHA256 = t8.D2_CAPS_SHA256
ADMISSION_FORMAT = "spec049-t004-admission-v1"
TERMS_FORMAT = "spec049-t014-terms-v1"
# owner decision 2026-11-17, D2 per-cohort cap: 16 units for this cohort; T008 units are not charged to it.
UNIT_CAP = 16
CAP_DECISION = "specs/049-harness-evaluation-learning/evidence/registration/d2-caps-scope-founder-decision-20261117.json"
CAP_DECISION_SHA256 = "9e83093d6bf5e66a0c771d50ed9d10c94995c8859f93460212df8ab443e324cd"
PLANS = {"P2": 15}  # arm C frozen from the offline round + 5 holdout cases x A/B/C
LEDGER = "t014-units.json"  # in each attempt's --out-dir: units and slots started, written before each launch
ROWS = "t014-rows.json"  # in each attempt's --out-dir: graded rows (records and hashes only)
SESSION = "00000000-0000-4000-8000-%012d"
COST_KEYS = ("cash", "quota", "wall", "cpu", "rss", "disk", "journal", "processes", "human")
UNKNOWN_COST = {"status": "unknown", "reason": "native-cost-unobserved"}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_STAMP = "%Y-%m-%dT%H:%M:%SZ"


def pinned(path: str, expected: str, name: str) -> bytes:
    """Bytes of a repository record bound by its SHA-256; a placeholder or any drift refuses."""
    if not (_HEX.fullmatch(expected) and path != PENDING):
        raise t9.AttemptRefused([f"{name}-not-pinned"])
    try:
        raw = (ROOT / path).read_bytes()
    except OSError:
        raise t9.AttemptRefused([f"{name}-missing"]) from None
    if sha256(raw).hexdigest() != expected:
        raise t9.AttemptRefused([f"{name}-drift"])
    return raw


def _record(raw: bytes, fmt: str, name: str) -> dict:
    try:
        value = parse_json(raw)
    except InvalidDecision:
        value = None
    if not (type(value) is dict and value.get("recordVersion") == fmt and value.get("executionAuthorization") is False):
        raise t9.AttemptRefused([f"{name}-invalid"])
    return value


def _hex(value) -> bool:
    return type(value) is str and _HEX.fullmatch(value) is not None


def _instant(value) -> datetime:
    return datetime.strptime(value, _STAMP).replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Terms:
    """The owner's T014 terms as this driver applies them."""

    plan: str
    window: tuple[datetime, datetime]
    arms: dict
    arm_c_files: dict
    refinement: RefinementDecision
    profile_sha256: str

    @property
    def cohort_units(self) -> int:
        """Units this cohort may start across every attempt."""
        return min(UNIT_CAP, PLANS[self.plan])


def parse_terms(raw: bytes) -> Terms:
    """``spec049-t014-terms-v1``: the plan, the pinned cap, the window, the arms, arm C's bytes and its round."""
    value = _record(raw, TERMS_FORMAT, "terms")
    try:
        cap = value["unitCap"]
        window = (_instant(value["window"]["start"]), _instant(value["window"]["end"]))
        arms = value["arms"]
        files = {row["path"]: row["text"].encode("utf-8") for row in value["armC"]["files"]}
        decision = value["armC"]["refinementDecision"]
        refinement = RefinementDecision(freeze(decision), canonical(decision))
        ok = (value["plan"] in PLANS and type(cap) is int and cap == UNIT_CAP <= hh.D2Caps("0" * 64).max_units
              and window[0] < window[1]
              and type(arms) is dict and set(arms) == set(ev.ARMS) and all(_hex(h) for h in arms.values())
              and arms["A"] == tn.ARM_SHA256["A"] and arms["B"] == tn.ARM_SHA256["B"]
              and len(files) == len(value["armC"]["files"])
              and value["workloadSha256"] == tn.WORKLOAD_SHA256 and value["model"] == tn.MODEL
              and value["issuanceSha256"] == ISSUANCE_SHA256 and value["admissionSha256"] == ADMISSION_SHA256
              and _hex(value["profileSha256"]))
        tn.check_arm(files, arms.get("C"))
    except (KeyError, TypeError, ValueError, AttributeError, tn.T014Error):
        ok = False
    if not ok:
        raise t9.AttemptRefused(["terms-invalid"])
    return Terms(value["plan"], window, dict(arms), files, refinement, value["profileSha256"])


def check_admission(raw: bytes, terms: Terms) -> None:
    """``spec049-t004-admission-v1``: admitted, for this issuance, route, cash and these candidates."""
    value = _record(raw, ADMISSION_FORMAT, "admission")
    route = {"host": "claude", "model": tn.MODEL, "route": "subscription", "additionalCashEur": 0}
    if not (value.get("disposition") == "admitted" and value.get("issuanceSha256") == ISSUANCE_SHA256
            and value.get("route") == route and value.get("candidates") == terms.arms
            and value.get("unitsFreezeSha256") == tn.UNITS_FREEZE_SHA256):
        raise t9.AttemptRefused(["admission-mismatch"])


def register(units: dict, terms: Terms) -> ev.Registration:
    """The native registration: frozen holdout units, arms A/B/C, the owner's arm-C round and native profile."""
    holdout = [units[c] for c in tn.HOLDOUT]
    try:
        return ev.register(holdout, lineages={c: tn.LINEAGE for c in tn.HOLDOUT},
                           families={c: c.split("-")[1] for c in tn.HOLDOUT},
                           strata={c: tn.CASES[c]["stratum"] for c in tn.HOLDOUT},
                           candidates=terms.arms, refinement=terms.refinement,
                           profile_sha256=terms.profile_sha256, cohort="native")
    except ev.EvaluationError as exc:
        raise t9.AttemptRefused([f"registration:{exc.reason}"]) from None


def slots(registration: ev.Registration) -> list[tuple[str, str]]:
    """Every (case, arm) cell in the registered order: units by id, each in its Latin-square arm order."""
    order = registration.to_dict()["order"]
    return [(case, arm) for case in sorted(order) for arm in order[case]]


# --- ledger and rows across attempts ---------------------------------------------------------


def _ledgers(parent: Path, name: str) -> list[object]:
    values = []
    try:
        for entry in sorted(parent.iterdir()) if parent.exists() else []:
            path = entry / name
            if entry.is_symlink() or not entry.is_dir() or path.is_symlink():
                raise ValueError(entry.name)
            if path.exists():
                values.append(json.loads(path.read_bytes()))
    except (OSError, ValueError):
        raise t9.AttemptRefused([f"{name}-unreadable"]) from None
    return values


def started(parent: Path) -> tuple[int, list[str]]:
    """Units and slots started by every earlier attempt under ``parent``; anything unreadable refuses."""
    total, seen = 0, []
    for value in _ledgers(parent, LEDGER):
        units = value.get("unitsStarted") if type(value) is dict else None
        names = value.get("slots") if type(value) is dict else None
        if type(units) is not int or units < 0 or type(names) is not list or len(names) != units \
                or not all(type(n) is str for n in names):
            raise t9.AttemptRefused([f"{LEDGER}-unreadable"])
        total += units
        seen += names
    if len(set(seen)) != len(seen):
        raise t9.AttemptRefused([f"{LEDGER}-unreadable"])
    return total, seen


def _atomic(out_dir: Path, name: str, value) -> None:
    tmp = out_dir / (name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, out_dir / name)


def write_ledger(out_dir: Path, names: list[str], *, create: bool = False) -> None:
    """Record the slots this attempt started (atomic rename); ``create`` refuses a label used before."""
    try:
        if create:
            out_dir.mkdir(mode=0o700)
        _atomic(out_dir, LEDGER, {"unitsStarted": len(names), "slots": list(names)})
    except FileExistsError:
        raise t9.AttemptRefused(["attempt-label-used"]) from None
    except OSError:
        raise t9.AttemptRefused(["unit-ledger-unwritable"]) from None


def write_rows(out_dir: Path, rows: list[dict]) -> None:
    try:
        _atomic(out_dir, ROWS, [{"slot": r["slot"], "arm": r["arm"], "attemptId": r["attemptId"],
                                 "commitment": r["commitment"].to_dict(), "verdict": r["verdict"].to_dict()}
                                for r in rows])
    except OSError:
        raise t9.AttemptRefused(["rows-unwritable"]) from None


def earlier_rows(parent: Path) -> list[dict]:
    rows = []
    for value in _ledgers(parent, ROWS):
        try:
            rows += [{"slot": r["slot"], "arm": r["arm"], "attemptId": r["attemptId"],
                      "commitment": tn.record_of(r["commitment"]), "verdict": tn.record_of(r["verdict"])}
                     for r in value]
        except (KeyError, TypeError):
            raise t9.AttemptRefused([f"{ROWS}-unreadable"]) from None
    return rows


def evaluation(registration: ev.Registration, rows: list[dict]) -> dict:
    """The T014 report over every graded row so far: verdict-ineligible, costs unknown."""
    graded = [{k: r[k] for k in ("arm", "attemptId", "commitment", "verdict")} | {"reservationSha256": None}
              for r in rows]
    entries = [{"id": f"cost-{r['attemptId']}", "phase": "verification", "attempt": r["attemptId"],
                "measures": {k: dict(UNKNOWN_COST) for k in COST_KEYS}} for r in rows]
    report = ev.evaluate(registration, graded, cost_entries=entries, reservations=[])
    data = report.to_dict()
    return {"reportSha256": report.sha256, "registrationSha256": registration.sha256,
            "rows": [{"unitId": r["unitId"], "arm": r["arm"], "outcome": r["outcome"], "terminal": r["terminal"]}
                     for r in data["rows"]],
            "strata": data["strata"], "costs": {"claimBlocked": data["costs"]["economic"]["claimBlocked"]},
            "pendingEndpoints": data["pendingEndpoints"], "verdictEligible": False,
            "executionAuthorization": False}


# --- admission -------------------------------------------------------------------------------


def trusted_inputs(args) -> tuple[hn.IssuedRecords, object]:
    raw = pinned(ISSUANCE, ISSUANCE_SHA256, "issuance")
    if not all(_hex(TRUSTED[k]) for k in TRUSTED) or ENVIRONMENT == PENDING:
        raise t9.AttemptRefused(["issuance-not-pinned"])
    try:
        issued = hn.issued_records(raw, **TRUSTED)
        environment = json.loads((ROOT / ENVIRONMENT).read_bytes())
        policy = hn.qualified_policy(
            environment, account=args.account, run_root=args.run_root, config_dir=args.config_dir,
            claude=args.claude, interpreter=args.interpreter, interpreter_sha256=args.interpreter_sha256 or "",
            interpreter_root=args.interpreter_root, proxy_port=args.proxy_port)
        hn.guard_unhashed(ROOT / "agent_braid")
    except (hn.NativeWiringError, _mac.LabError) as exc:
        raise t9.AttemptRefused([f"native-wiring:{exc.reason}"]) from None
    except (OSError, ValueError):
        raise t9.AttemptRefused(["native-wiring:environment-unreadable"]) from None
    return issued, policy


def check_window(now: datetime, issued: hn.IssuedRecords, terms: Terms) -> None:
    """A unit must be able to end inside the owner's window and before the issued records expire."""
    wall = hh.D2Caps("0" * 64).unit_wall_seconds
    if not (terms.window[0] <= now and now + timedelta(seconds=wall) <= terms.window[1]):
        raise t9.AttemptRefused(["outside-owner-window"],
                                {"window": f"{terms.window[0].isoformat()}..{terms.window[1].isoformat()}"})
    if int(now.timestamp()) + wall >= issued.expires_at:
        raise t9.AttemptRefused(["qualification-expiring"])


def cohort_left(terms: Terms, registration: ev.Registration, parent: Path) -> tuple[list, int]:
    """Slots no attempt started, in the registered order, and the units this cohort may still start. The ledger
    counts every label under ``parent``; at ``UNIT_CAP`` started units nothing more starts (no 17th unit)."""
    count, names = started(parent)
    pending = [s for s in slots(registration) if f"{s[0]}:{s[1]}" not in names]
    remaining = min(terms.cohort_units - count, UNIT_CAP - count, len(pending))
    if remaining < 1:
        raise t9.AttemptRefused(["cohort-units-exhausted"], {"cohortUnits": str(UNIT_CAP)})
    return pending, remaining


@dataclass(frozen=True)
class Admitted:
    issued: hn.IssuedRecords
    policy: object
    decisions: dict
    caps: hh.D2Caps
    terms: Terms
    units: dict
    registration: ev.Registration
    pending: list  # (case, arm) slots no attempt started, in the registered order
    remaining: int  # units this cohort may still start


def admit(args, report: dict, now: datetime) -> Admitted:
    """Every no-quota check after a ready pre-flight, shared by the dry run and the cohort."""
    issued, policy = trusted_inputs(args)
    if report["observed"].get("environmentSha256") != issued.environment_sha256:
        raise t9.AttemptRefused(["environment-drift"])
    terms = parse_terms(pinned(TERMS, TERMS_SHA256, "terms"))
    check_admission(pinned(ADMISSION, ADMISSION_SHA256, "admission"), terms)
    check_window(now, issued, terms)
    try:
        decisions = hh.parse_profile_decisions(pinned(PROFILE_DECISIONS, PROFILE_DECISIONS_SHA256, "profile-decisions"),
                                               expected_sha256=PROFILE_DECISIONS_SHA256)
        caps = hh.parse_d2_caps((ROOT / D2_CAPS).read_bytes(), expected_sha256=D2_CAPS_SHA256)
    except hh.HostGateError as exc:
        raise t9.AttemptRefused([f"decision-record:{exc.reason}"]) from None
    try:
        units = tn.units(ROOT)
    except tn.T014Error as exc:
        raise t9.AttemptRefused([exc.reason]) from None
    registration = register(units, terms)
    pinned(CAP_DECISION, CAP_DECISION_SHA256, "cap-decision")  # the owner's D2 per-cohort cap record
    pending, remaining = cohort_left(terms, registration, Path(args.out_dir).parent)
    return Admitted(issued, policy, decisions, caps, terms, units, registration, pending, remaining)


# --- the cohort ------------------------------------------------------------------------------


def run_cohort(args, system, *, ask=input, say=print, clock=lambda: datetime.now(timezone.utc),
               backend_factory=_mac.MacOSContainment, run_unit=hn.run_native_unit) -> dict:
    report = t9.preflight(args, system)
    if report["verdict"] != "ready":
        raise t9.AttemptRefused(report["failed"], {c["check"]: c["detail"] for c in report["checks"] if not c["ok"]})
    a = admit(args, report, clock())
    if not args.founder_go:
        raise t9.AttemptRefused(["founder-go-flag-missing"])
    count = min(args.units, a.remaining)
    if count < 1:
        raise t9.AttemptRefused(["no-units-requested"])
    plan = a.pending[:count]
    say(f"T014 cohort {args.attempt}: up to {count} serial units ({', '.join(f'{c}/{m}' for c, m in plan)}), one "
        "small Haiku session each; you type the usage card before and after each.")
    if ask(f"Type the attempt name ({args.attempt}) to start, anything else cancels: ").strip() != args.attempt:
        raise t9.AttemptRefused(["operator-cancelled"])
    out_dir = Path(args.out_dir)
    parent_rows = earlier_rows(out_dir.parent)
    write_ledger(out_dir, [], create=True)
    reader = t9.UsageCardReader(ask, say, clock, datetime.now().astimezone().tzinfo)
    baseline = t8.read_observation(reader, ask, say, "BASELINE (before the cohort)", clock)
    if baseline is None:
        raise t9.AttemptRefused(["baseline-reading-refused"])
    run = hh.HostQualificationRun(a.decisions, a.caps, "claude", a.issued.environment_sha256, baseline)
    workdir, cleanup = t9._workdirs(args.run_root)
    inventory = _probes.credential_inventory(args.config_dir)
    probe_runner = _probes.make_f4_probe_runner(arena_parent=args.arena_parent, workdir_factory=workdir)
    backend = backend_factory(a.policy, probe_runner=probe_runner, clock=time.time,
                              operator_account=args.operator_account,
                              qualification=a.issued.containment, qualification_sha256=a.issued.containment_sha256,
                              host_qualification=a.issued.host, host_qualification_sha256=a.issued.host_sha256)
    files = {"A": tn.arm_files("A", ROOT), "B": tn.arm_files("B", ROOT), "C": a.terms.arm_c_files}
    export = canonical({"format": "braid-harness-export-inventory/v0.1", "allowedEventFields": ["text", "state"],
                        "secrets": [value for value, _ in inventory], "maxRetentionSeconds": 3600})
    names, rows, summaries, stop = [], [], [], None
    try:
        for index, (case, arm) in enumerate(plan):
            slot = f"{case}:{arm}"
            check_window(clock(), a.issued, a.terms)
            manifest, context = tn.unit_inputs(
                case, arm, files[arm], candidate_sha256=a.terms.arms[arm], registered=a.units,
                environment_sha256=a.issued.environment_sha256, claude_sha256=a.policy.claude_sha256,
                containment_sha256=backend.qualification.sha256,
                host_qualification_sha256=backend.host_qualification.sha256)
            before = t8.read_observation(reader, ask, say, f"BEFORE unit {index + 1} of {count} ({slot})", clock)
            if before is None:
                stop = "before-reading-refused"
                break
            launched = []
            inv = verify_inventory(export, expected_sha256=sha256(export).hexdigest())
            attempt_id = f"{args.attempt}-{case}-{arm}"

            def on_launch(slot=slot):
                write_ledger(out_dir, names + [slot])  # counted before the host may launch; never undercounts
                names.append(slot)
                launched.append(True)

            outcome, error = None, None
            try:
                outcome = run_unit(
                    run=run, backend=backend, workdir=workdir(), containment=a.issued.host,
                    containment_sha256=a.issued.host_sha256, manifest=manifest, context=context,
                    request=hc.ClaudeRequest(session_id=SESSION % (index + int(time.time()) % 10**6), model=tn.MODEL),
                    compatibility=hc.CompatibilityWindow((2, 1, 292), (2, 1, 293)), inventory=inv,
                    attempt_id=attempt_id, before=before,
                    read_after=lambda: t8.read_observation(reader, ask, say, f"AFTER unit {index + 1}", clock),
                    now=clock, retention_seconds=3600, settle_now=lambda: int(clock().timestamp()),
                    on_launch=on_launch)
            except (hh.HostGateError, hc.ClaudeHostError, _mac.LabError, hn.NativeWiringError) as exc:
                error = exc.reason
            if launched:  # a launched slot always gets a graded row, even when the run raised
                cell = tn.grade(a.units[case], arm=arm, candidate_sha256=a.terms.arms[arm], attempt_id=attempt_id,
                                result=outcome.result if outcome is not None else None, inventory=inv,
                                now=int(clock().timestamp()), retention_seconds=3600)
                rows.append({"slot": slot, **cell.row})
                write_rows(out_dir, rows)
                outcome_label = _outcome_of(a.units[case], cell)
                summary = {"unit": index + 1, "slot": slot, "outcome": outcome_label, "terminal": cell.terminal}
                if outcome is not None and outcome.result is not None:
                    summary |= t8.host_summary(outcome.result, tn.MODEL)
                summaries.append(summary)
                say(f"[T014] unit {index + 1} {slot}: terminal={cell.terminal} outcome={outcome_label}")
            if error is not None:
                stop = error
                break
            if run.stopped:
                stop = run.stopped
                break
    except BaseException as exc:  # Ctrl-C, SIGTERM-as-exception or a bug: keep the evidence, then re-raise
        stop = f"aborted:{type(exc).__name__}"
        print(json.dumps(_report(args, run, backend, stop, "cohort-aborted", summaries,
                                 _safe_evaluation(a.registration, parent_rows + rows)), indent=2, sort_keys=True))
        exc.t014_reported = True
        raise
    finally:
        backend.close()
        cleanup()
    final = stop or run.stopped
    return _report(args, run, backend, final, "cohort-stopped" if final else "cohort-finished", summaries,
                   _safe_evaluation(a.registration, parent_rows + rows))


def _outcome_of(unit, cell: tn.GradedCell) -> str:
    """The evaluation outcome of one cell, as ``harness_evaluation`` classifies it."""
    verdict = cell.row["verdict"].to_dict()
    return ev._outcome(unit, verdict)[0]


def _safe_evaluation(registration, rows) -> dict:
    try:
        return evaluation(registration, rows)
    except (ev.EvaluationError, ValueError) as exc:
        return {"refused": getattr(exc, "reason", type(exc).__name__), "verdictEligible": False,
                "executionAuthorization": False}


def _report(args, run, backend, stopped, verdict, hosts=(), evaluated=None) -> dict:
    host = run.verdict().to_dict()
    return {"verdict": verdict, "attempt": args.attempt, "units": host["units"], "stopped": stopped,
            "hostVerdict": host, "hostRuns": list(hosts), "backendRefusals": t9.refusal_evidence(backend),
            "evaluation": evaluated, "verdictEligible": False, "executionAuthorization": False}


def parser():
    p = t9.parser()
    p.description = "SPEC-049/T014 native cohort driver (Claude profile only)"
    p.add_argument("--units", type=int, default=PLANS["P2"], help="serial units this attempt (capped by the terms)")
    return p


def main(argv=None, *, system=None, clock=lambda: datetime.now(timezone.utc)) -> int:
    args = parser().parse_args(argv)
    system = system or t9.System()
    if args.dry_run:
        report = t9.preflight(args, system)
        if report["verdict"] == "ready":
            try:
                a = admit(args, report, clock())
                report.update(wiring="ok", issuedExpiresAt=a.issued.expires_at, unitsRemaining=a.remaining,
                              nextSlots=[f"{c}:{m}" for c, m in a.pending[:a.remaining]],
                              registrationSha256=a.registration.sha256)
            except t9.AttemptRefused as exc:
                report.update(verdict="refused", wiring=exc.reasons[0])
            except (OSError, ValueError) as exc:
                report.update(verdict="refused", wiring=type(exc).__name__)
        report["executionAuthorization"] = False
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["verdict"] == "ready" else 2
    try:
        result = run_cohort(args, system, clock=clock)
    except KeyboardInterrupt as exc:
        if not getattr(exc, "t014_reported", False):
            print(json.dumps({"verdict": "cohort-aborted", "reasons": ["interrupted"], "nativeRun": False,
                              "executionAuthorization": False}, indent=2, sort_keys=True))
        return 130
    except t9.AttemptRefused as exc:
        print(json.dumps({"verdict": "refused", "reasons": exc.reasons, "details": exc.details, "nativeRun": False,
                          "executionAuthorization": False}, indent=2, sort_keys=True))
        return 2
    except (OSError, ValueError, hn.NativeWiringError, _mac.LabError, hh.HostGateError) as exc:
        print(json.dumps({"verdict": "refused", "reasons": [getattr(exc, "reason", type(exc).__name__)],
                          "nativeRun": False, "executionAuthorization": False}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "cohort-finished" else 2


if __name__ == "__main__":
    sys.exit(main())
