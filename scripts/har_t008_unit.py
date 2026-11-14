#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Operator-run driver for the SPEC-048/T008 native Claude cohort (Claude profile only).

NOT an authorization. It runs as the dedicated account in that account's own ``Background`` session,
started by the root launcher ``scripts/har_t008_launch.sh`` (installed as
``/usr/local/libexec/braid/t008-launch.sh``; founder decision T008-7 of 2026-11-13). It reuses the SPEC-065
T009 pre-flight (account, session ownership, pins, config dir, operator account), then:

* ``--dry-run``: pre-flight, then every no-quota check of the cohort (``admit``): the pinned issuance, the
  environment hash recomputed in this session against the issued one, the qualified policy, the MDRV-04
  guard, the window, the hash-pinned founder record and D2 caps, and the units left; nothing native runs;
* ``--founder-go``: builds the T005 backend from the founder-issued records (not attempt records),
  and runs up to ``--units`` serial units (at most ``MAX_UNITS`` for the whole cohort, the founder's
  2026-11-06 choice kept on 2026-11-13, below the D2 maximum of 16; each attempt counts its started units in
  ``<out-dir>/t008-units.json`` before each launch, and every later attempt subtracts them). Each unit asks the
  operator for the usage card before and after (NC-6), admits through ``HostQualificationRun`` (D2 caps, stop conditions, containment verification),
  runs one read-only Haiku session through the native transport (the backend repeats the NC-11
  pre-session check) and settles against the caps. Any stop ends the cohort.

Window: a unit starts only if it can end inside ``WINDOW`` (the founder's schedule) and before the issued
records expire.
``executionAuthorization`` is false in every output; the verdict is evidence for the founder's T008 record.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import har_t009_attempt as t9  # noqa: E402
from agent_braid import harness_containment_macos as _mac  # noqa: E402
from agent_braid import harness_host_claude as hc  # noqa: E402
from agent_braid import harness_hosts as hh  # noqa: E402
from agent_braid import harness_hosts_native as hn  # noqa: E402
from agent_braid import harness_qualification_probes as _probes  # noqa: E402
from agent_braid.harness_observation import verify_inventory  # noqa: E402
from agent_braid.system_one import canonical  # noqa: E402
from hashlib import sha256  # noqa: E402

MODEL = "haiku"  # the one model the cohort requests and the report checks against
MAX_UNITS = 4  # founder, 2026-11-06 (decision 2/5), unchanged on 2026-11-13 (T008-6)
WINDOW = (datetime(2026, 11, 9, 20, 30, tzinfo=timezone.utc), datetime(2026, 11, 30, 23, 59, tzinfo=timezone.utc))
# SPEC-065 T013 issuance of 2026-11-13; it supersedes the 2026-11-06 one (void on macOS build 26B131)
TRUSTED = {"containment_sha256": "fa59fbae9286f0794331aedcebe782b99767819dc4a30f37a08713509be9fa6a",
           "host_sha256": "9022b771382a239be3a4d399dfb9c949ef29f4276aeebb0b5db735e9a67a847f"}
ISSUANCE = "specs/065-native-claude-containment/evidence/qualification/issuance-2026-11-13.json"
ISSUANCE_SHA256 = "8aa07dd42e77560b548ac35edce05d8f975f8704eeaab4452f2a17238740d510"
ENVIRONMENT = "specs/065-native-claude-containment/evidence/qualification/t009-20261113c/environment.json"
FOUNDER_DECISIONS = "specs/048-harness-variant-laboratory/evidence/founder-decisions-20261113.json"
FOUNDER_DECISIONS_SHA256 = "0132118f9d04c6c39b5b59a879343719168ccb31d2315f4b557ad85feaa6ad5c"
D2_CAPS = "specs/049-harness-evaluation-learning/evidence/registration/d2-caps-founder-decision-20261031.json"
D2_CAPS_SHA256 = "b1851e1c1e0d075368cd8193c97ae1e322fcce8a5d94f23762f3dd4aed4d2d88"
SESSION = "00000000-0000-4000-8000-%012d"
LEDGER = "t008-units.json"  # in each attempt's --out-dir: units started, counted before each launch
_CLOCK = re.compile(r"([01]?[0-9]|2[0-3]):([0-5][0-9])\Z")
_DATE_CLOCK = re.compile(r"(\d{4}-\d{2}-\d{2}) ([01]?[0-9]|2[0-3]):([0-5][0-9])\Z")


def _local(day: datetime, text: str, pattern: re.Pattern) -> int | None:
    match = pattern.fullmatch(text.strip())
    if match is None:
        return None
    tz = day.astimezone().tzinfo
    if pattern is _CLOCK:
        at = day.astimezone().replace(hour=int(match[1]), minute=int(match[2]), second=0, microsecond=0)
        if at <= day.astimezone() - timedelta(minutes=1):
            at += timedelta(days=1)
    else:
        try:
            at = datetime.strptime(f"{match[1]} {match[2]}:{match[3]}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        except ValueError:
            return None
    return int(at.timestamp())


def read_observation(reader: t9.UsageCardReader, ask, say, role: str, clock) -> hh.QuotaObservation | None:
    """NC-6 reading plus the two reset instants the D2 gate needs, all typed by the operator."""
    card = reader.read(role)
    if card is None:
        return None
    now = clock()
    try:
        five = _local(now, ask("  5-hour window resets at (local HH:MM as on the card): "), _CLOCK)
        weekly = _local(now, ask("  Weekly window resets at (local YYYY-MM-DD HH:MM): "), _DATE_CLOCK)
        plan = ask("  Plan on the card (max/pro/team, lower case): ").strip().lower()
        route = ask("  Route (type 'subscription' only if no API key or pay-per-use applies): ").strip().lower()
    except EOFError:
        say("[T008] no input: reading refused")
        return None
    if five is None or weekly is None:
        say("[T008] reset instants not understood: reading refused")
        return None
    observed = int(datetime.strptime(card["observedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
    try:
        return hh.QuotaObservation("claude", observed, plan, route, card["fiveHourPercent"], five,
                                   card["weeklyPercent"], weekly, card["extraUsageEnabled"])
    except hh.HostGateError:
        say("[T008] reading malformed: refused")
        return None


def trusted_inputs(args) -> tuple[hn.IssuedRecords, dict, object]:
    raw = (ROOT / ISSUANCE).read_bytes()
    if sha256(raw).hexdigest() != ISSUANCE_SHA256:
        raise hn.NativeWiringError("issuance-drift")
    issued = hn.issued_records(raw, **TRUSTED)
    environment = json.loads((ROOT / ENVIRONMENT).read_bytes())
    policy = hn.qualified_policy(
        environment, account=args.account, run_root=args.run_root, config_dir=args.config_dir,
        claude=args.claude, interpreter=args.interpreter, interpreter_sha256=args.interpreter_sha256 or "",
        interpreter_root=args.interpreter_root, proxy_port=args.proxy_port)
    hn.guard_unhashed(ROOT / "agent_braid")
    return issued, environment, policy


def decision_inputs() -> tuple[dict, hh.D2Caps]:
    """The founder's per-host decisions and the D2 caps, each bound by its SHA-256. The founder record names the
    issued records it authorizes (``qualificationRecords``); a test keeps it equal to ``ISSUANCE``/``TRUSTED``."""
    decisions = hh.parse_profile_decisions((ROOT / FOUNDER_DECISIONS).read_bytes(),
                                           expected_sha256=FOUNDER_DECISIONS_SHA256)
    caps = hh.parse_d2_caps((ROOT / D2_CAPS).read_bytes(), expected_sha256=D2_CAPS_SHA256)
    return decisions, caps


def check_window(now: datetime, issued: hn.IssuedRecords) -> None:
    """A unit must be able to end inside the founder's window and before the issued records expire."""
    wall = hh.D2Caps("0" * 64).unit_wall_seconds
    if not (WINDOW[0] <= now and now + timedelta(seconds=wall) <= WINDOW[1]):
        raise t9.AttemptRefused(["outside-founder-window"],
                                {"window": f"{WINDOW[0].isoformat()}..{WINDOW[1].isoformat()}"})
    if int(now.timestamp()) + wall >= issued.expires_at:
        raise t9.AttemptRefused(["qualification-expiring"])


def units_started(parent: Path) -> int:
    """Units started by every earlier T008 attempt under ``parent``: the founder's cap of four is for the whole
    cohort, not per invocation, so a new label never resets it. Anything unreadable refuses."""
    total = 0
    try:
        for entry in sorted(parent.iterdir()) if parent.exists() else []:
            ledger = entry / LEDGER
            if entry.is_symlink() or not entry.is_dir() or ledger.is_symlink():
                raise ValueError(entry.name)
            if ledger.exists():
                value = json.loads(ledger.read_bytes()).get("unitsStarted")
                if type(value) is not int or value < 0:
                    raise ValueError(entry.name)
                total += value
    except (OSError, ValueError, AttributeError):
        raise t9.AttemptRefused(["unit-ledger-unreadable"]) from None
    return total


def write_ledger(out_dir: Path, started: int, *, create: bool = False) -> None:
    """Record ``started`` units in this attempt's ledger (atomic rename). ``create`` makes the attempt's directory
    and refuses a label that was used before."""
    try:
        if create:
            out_dir.mkdir(mode=0o700)
        tmp = out_dir / (LEDGER + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump({"unitsStarted": started}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, out_dir / LEDGER)
    except FileExistsError:
        raise t9.AttemptRefused(["attempt-label-used"]) from None
    except OSError:
        raise t9.AttemptRefused(["unit-ledger-unwritable"]) from None


def admit(args, report: dict, now: datetime):
    """Every no-quota check after a ready pre-flight, shared by the dry run and the cohort."""
    try:
        issued, _, policy = trusted_inputs(args)
    except (hn.NativeWiringError, _mac.LabError) as exc:
        raise t9.AttemptRefused([f"native-wiring:{exc.reason}"]) from None
    # the hash recomputed in this session (its kind included) must be the issued one
    if report["observed"].get("environmentSha256") != issued.environment_sha256:
        raise t9.AttemptRefused(["environment-drift"])
    check_window(now, issued)
    try:
        decisions, caps = decision_inputs()
    except hh.HostGateError as exc:
        raise t9.AttemptRefused([f"decision-record:{exc.reason}"]) from None
    remaining = MAX_UNITS - units_started(Path(args.out_dir).parent)
    if remaining < 1:
        raise t9.AttemptRefused(["cohort-units-exhausted"], {"maxUnits": str(MAX_UNITS)})
    return issued, policy, decisions, caps, remaining


def host_summary(result: hc.ClaudeHostResult, requested_model: str | None = None) -> dict:
    """Fixed-field, redacted view of one host run for the published report: the terminal state, the fixed
    error codes, and the run flags. Never assistant text, prompt, tokens, paths or any host-supplied string
    beyond the version id and a model id that is the requested one or its own resolved family id."""
    data, observed = result.to_dict(), result.observation.to_dict()
    reported = data["hostModel"]
    shown_model = reported if hc.model_matches(requested_model, reported) else None
    codes = [e.get("text") for e in observed.get("events", ()) if e.get("kind") == "error"]
    return {"terminal": observed["terminal"],
            "streamErrors": sorted({c for c in codes if c in hc.TERMINAL_ERROR_CODES}),
            "transportErrors": observed["loss"]["transportErrors"],
            "exitCode": data["exitCode"], "timedOut": data["timedOut"], "cancelled": data["cancelled"],
            "settled": data["settled"], "outputTruncated": data["outputTruncated"],
            "hostVersion": data["hostVersion"], "hostModel": shown_model}


def run_cohort(args, system, *, ask=input, say=print, clock=lambda: datetime.now(timezone.utc),
               backend_factory=_mac.MacOSContainment) -> dict:
    report = t9.preflight(args, system)
    if report["verdict"] != "ready":
        raise t9.AttemptRefused(report["failed"], {c["check"]: c["detail"] for c in report["checks"] if not c["ok"]})
    issued, policy, decisions, caps, remaining = admit(args, report, clock())
    if not args.founder_go:
        raise t9.AttemptRefused(["founder-go-flag-missing"])
    units = min(args.units, remaining)
    say(f"T008 cohort {args.attempt}: up to {units} serial units, one small Haiku session each; "
        "you type the usage card before and after each.")
    if ask(f"Type the attempt name ({args.attempt}) to start, anything else cancels: ").strip() != args.attempt:
        raise t9.AttemptRefused(["operator-cancelled"])
    out_dir = Path(args.out_dir)
    write_ledger(out_dir, 0, create=True)
    reader = t9.UsageCardReader(ask, say, clock, datetime.now().astimezone().tzinfo)
    baseline = read_observation(reader, ask, say, "BASELINE (before the cohort)", clock)
    if baseline is None:
        raise t9.AttemptRefused(["baseline-reading-refused"])
    run = hh.HostQualificationRun(decisions, caps, "claude", issued.environment_sha256, baseline)
    workdir, cleanup = t9._workdirs(args.run_root)
    inventory = _probes.credential_inventory(args.config_dir)
    probe_runner = _probes.make_f4_probe_runner(arena_parent=args.arena_parent, workdir_factory=workdir)
    backend = backend_factory(policy, probe_runner=probe_runner, clock=time.time,
                              operator_account=args.operator_account,
                              qualification=issued.containment, qualification_sha256=issued.containment_sha256,
                              host_qualification=issued.host, host_qualification_sha256=issued.host_sha256)
    try:
        export = canonical({"format": "braid-harness-export-inventory/v0.1", "allowedEventFields": ["text", "state"],
                            "secrets": [value for value, _ in inventory], "maxRetentionSeconds": 3600})
        manifest, context = hn.unit_inputs(
            environment_sha256=issued.environment_sha256, claude_sha256=policy.claude_sha256,
            containment_sha256=backend.qualification.sha256,
            host_qualification_sha256=backend.host_qualification.sha256)
    except BaseException:
        backend.close()
        cleanup()
        raise
    records, stop, summaries = [], None, []
    if units < 1:
        backend.close()
        cleanup()
        raise t9.AttemptRefused(["no-units-requested"])
    try:
        for index in range(units):
            check_window(clock(), issued)  # the founder window and the issued validity hold for every unit
            before = read_observation(reader, ask, say, f"BEFORE unit {index + 1} of {units}", clock)
            if before is None:
                stop = "before-reading-refused"
                break
            write_ledger(out_dir, index + 1)  # counted before the launch, so a crash never under-counts
            try:
                outcome = hn.run_native_unit(
                    run=run, backend=backend, workdir=workdir(), containment=issued.host,
                    containment_sha256=issued.host_sha256, manifest=manifest, context=context,
                    request=hc.ClaudeRequest(session_id=SESSION % (index + int(time.time()) % 10**6),
                                             model=MODEL),
                    compatibility=hc.CompatibilityWindow((2, 1, 292), (2, 1, 293)),
                    inventory=verify_inventory(export, expected_sha256=sha256(export).hexdigest()),
                    attempt_id=f"{args.attempt}-u{index}", before=before,
                    read_after=lambda: read_observation(reader, ask, say, f"AFTER unit {index + 1}", clock),
                    now=clock, retention_seconds=3600, settle_now=lambda: int(clock().timestamp()))
            except (hh.HostGateError, hc.ClaudeHostError, _mac.LabError, hn.NativeWiringError) as exc:
                stop = exc.reason
                break
            if outcome.result is not None:
                summaries.append({"unit": index + 1, **host_summary(outcome.result, MODEL)})
            say(f"[T008] unit {index + 1}: completed={outcome.record.completed} breach={outcome.record.breach}")
            if run.stopped:
                stop = run.stopped
                break
    except BaseException as exc:  # Ctrl-C, SIGTERM-as-exception or a bug: keep the evidence, then re-raise
        stop = f"aborted:{type(exc).__name__}"
        print(json.dumps(_report(args, run, backend, stop, "cohort-aborted", summaries), indent=2, sort_keys=True))
        exc.t008_reported = True
        raise
    finally:
        backend.close()
        cleanup()
    return _report(args, run, backend, stop or run.stopped,
                   "cohort-finished" if not (stop or run.stopped) else "cohort-stopped", summaries)


def _report(args, run, backend, stopped, verdict, hosts=()) -> dict:
    host = run.verdict().to_dict()
    return {"verdict": verdict, "attempt": args.attempt, "units": host["units"], "stopped": stopped,
            "hostVerdict": host, "hostRuns": list(hosts), "backendRefusals": t9.refusal_evidence(backend),
            "executionAuthorization": False}


def parser():
    p = t9.parser()
    p.description = "SPEC-048/T008 native Claude cohort driver (Claude profile only)"
    p.add_argument("--units", type=int, default=MAX_UNITS, help=f"serial units, at most {MAX_UNITS}")
    return p


def main(argv=None, *, system=None, clock=lambda: datetime.now(timezone.utc)) -> int:
    args = parser().parse_args(argv)
    system = system or t9.System()
    if args.dry_run:
        report = t9.preflight(args, system)
        if report["verdict"] == "ready":
            try:
                issued, _, _, _, remaining = admit(args, report, clock())
                report.update(wiring="ok", issuedExpiresAt=issued.expires_at, unitsRemaining=remaining)
            except t9.AttemptRefused as exc:
                report.update(verdict="refused", wiring=exc.reasons[0])
            except (OSError, ValueError) as exc:
                report.update(verdict="refused", wiring=type(exc).__name__)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["verdict"] == "ready" else 2
    try:
        result = run_cohort(args, system, clock=clock)
    except KeyboardInterrupt as exc:  # a Ctrl-C before the unit loop still ends with a JSON report
        if not getattr(exc, "t008_reported", False):
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
