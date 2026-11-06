#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Operator-run driver for the SPEC-048/T008 native Claude cohort (Claude profile only).

NOT an authorization. The founder runs it inside the dedicated account's own login session through
``t008-lab.sh``. It reuses the SPEC-065 T009 pre-flight (account, pins, config dir, operator account),
then:

* ``--dry-run``: pre-flight, the issued records, the qualified policy and the MDRV-04 guard; nothing
  native runs and no quota is read;
* ``--founder-go``: builds the T005 backend from the founder-issued records (not attempt records),
  and runs up to ``--units`` serial units (at most ``MAX_UNITS``, the founder's 2026-11-06 choice,
  below the D2 maximum of 16). Each unit asks the operator for the usage card before and after
  (NC-6), admits through ``HostQualificationRun`` (D2 caps, stop conditions, containment verification),
  runs one read-only Haiku session through the native transport (the backend repeats the NC-11
  pre-session check) and settles against the caps. Any stop ends the cohort.

Window: only inside ``WINDOW`` (the founder's schedule) and before the issued records expire.
``executionAuthorization`` is false in every output; the verdict is evidence for the founder's T008 record.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
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

MAX_UNITS = 4  # founder, 2026-11-06 (decision 2/5)
WINDOW = (datetime(2026, 11, 9, 20, 30, tzinfo=timezone.utc), datetime(2026, 11, 30, 23, 59, tzinfo=timezone.utc))
TRUSTED = {"containment_sha256": "b7641c8a48b9c4a2ef6213fa42fa429ae56b279df86c5da33db07e67ff83f834",
           "host_sha256": "8c1a38fe054a09a44a29b53f9aad757500991e1d74aaa655ec4584bcd886178d"}
ISSUANCE = "specs/065-native-claude-containment/evidence/qualification/issuance-2026-11-06.json"
ENVIRONMENT = "specs/065-native-claude-containment/evidence/qualification/t009-20261106a/environment.json"
FOUNDER_DECISIONS = "specs/048-harness-variant-laboratory/evidence/founder-decisions-20261106.json"
FOUNDER_DECISIONS_SHA256 = "6f5394dae371c2c8082153db3ce3ab99fd02d86d4c5372b931c0926f5ce7b4a0"
SESSION = "00000000-0000-4000-8000-%012d"
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
    issued = hn.issued_records((ROOT / args.issuance).read_bytes(), **TRUSTED)
    environment = json.loads((ROOT / args.environment).read_bytes())
    policy = hn.qualified_policy(
        environment, account=args.account, run_root=args.run_root, config_dir=args.config_dir,
        claude=args.claude, interpreter=args.interpreter, interpreter_sha256=args.interpreter_sha256 or "",
        interpreter_root=args.interpreter_root, proxy_port=args.proxy_port)
    hn.guard_unhashed(ROOT / "agent_braid")
    return issued, environment, policy


def check_window(now: datetime, issued: hn.IssuedRecords) -> None:
    if not WINDOW[0] <= now <= WINDOW[1]:
        raise t9.AttemptRefused(["outside-founder-window"], {"window": f"{WINDOW[0].isoformat()}..{WINDOW[1].isoformat()}"})
    if int(now.timestamp()) + hh.D2Caps("0" * 64).unit_wall_seconds >= issued.expires_at:
        raise t9.AttemptRefused(["qualification-expiring"])


def run_cohort(args, system, *, ask=input, say=print, clock=lambda: datetime.now(timezone.utc),
               backend_factory=_mac.MacOSContainment) -> dict:
    report = t9.preflight(args, system)
    if report["verdict"] != "ready":
        raise t9.AttemptRefused(report["failed"], {c["check"]: c["detail"] for c in report["checks"] if not c["ok"]})
    try:
        issued, environment, policy = trusted_inputs(args)
    except (hn.NativeWiringError, _mac.LabError) as exc:
        raise t9.AttemptRefused([f"native-wiring:{exc.reason}"]) from None
    if report["observed"].get("environmentSha256") != issued.environment_sha256:
        raise t9.AttemptRefused(["environment-drift"])
    check_window(clock(), issued)
    if not args.founder_go:
        raise t9.AttemptRefused(["founder-go-flag-missing"])
    units = min(args.units, MAX_UNITS)
    say(f"T008 cohort {args.attempt}: up to {units} serial units, one small Haiku session each; "
        "you type the usage card before and after each.")
    if ask(f"Type the attempt name ({args.attempt}) to start, anything else cancels: ").strip() != args.attempt:
        raise t9.AttemptRefused(["operator-cancelled"])
    decisions_raw = (ROOT / FOUNDER_DECISIONS).read_bytes()
    decisions = hh.parse_profile_decisions(decisions_raw, expected_sha256=FOUNDER_DECISIONS_SHA256)
    caps_path = ROOT / "specs/049-harness-evaluation-learning/evidence/registration/d2-caps-founder-decision-20261031.json"
    caps = hh.parse_d2_caps(caps_path.read_bytes(), expected_sha256="b1851e1c1e0d075368cd8193c97ae1e322fcce8a5d94f23762f3dd4aed4d2d88")
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
    export = canonical({"format": "braid-harness-export-inventory/v0.1", "allowedEventFields": ["text", "state"],
                        "secrets": [value for value, _ in inventory], "maxRetentionSeconds": 3600})
    manifest, context = hn.unit_inputs(
        environment_sha256=issued.environment_sha256, claude_sha256=policy.claude_sha256,
        containment_sha256=backend.qualification.sha256,
        host_qualification_sha256=backend.host_qualification.sha256)
    records, stop = [], None
    try:
        for index in range(units):
            before = read_observation(reader, ask, say, f"BEFORE unit {index + 1} of {units}", clock)
            try:
                outcome = hn.run_native_unit(
                    run=run, backend=backend, workdir=workdir(), containment=issued.host,
                    containment_sha256=issued.host_sha256, manifest=manifest, context=context,
                    request=hc.ClaudeRequest(session_id=SESSION % (index + int(time.time()) % 10**6),
                                             model="haiku"),
                    compatibility=hc.CompatibilityWindow((2, 1, 292), (2, 1, 293)),
                    inventory=verify_inventory(export, expected_sha256=sha256(export).hexdigest()),
                    attempt_id=f"{args.attempt}-u{index}", before=before,
                    read_after=lambda: read_observation(reader, ask, say, f"AFTER unit {index + 1}", clock),
                    now=clock, retention_seconds=3600, settle_now=lambda: int(clock().timestamp()))
            except (hh.HostGateError, hc.ClaudeHostError, _mac.LabError) as exc:
                stop = exc.reason
                break
            records.append(outcome.record.to_dict())
            say(f"[T008] unit {index + 1}: completed={outcome.record.completed} breach={outcome.record.breach}")
            if run.stopped:
                stop = run.stopped
                break
    finally:
        backend.close()
        cleanup()
    return {"verdict": "cohort-finished", "attempt": args.attempt, "units": records, "stopped": stop or run.stopped,
            "hostVerdict": run.verdict().to_dict(), "backendRefusals": t9.refusal_evidence(backend),
            "executionAuthorization": False}


def parser():
    p = t9.parser()
    p.description = "SPEC-048/T008 native Claude cohort driver (Claude profile only)"
    for action in p._actions:
        if action.dest == "out_dir":
            action.required = False
    p.add_argument("--issuance", default=ISSUANCE)
    p.add_argument("--environment", default=ENVIRONMENT)
    p.add_argument("--units", type=int, default=MAX_UNITS, help=f"serial units, at most {MAX_UNITS}")
    return p


def main(argv=None, *, system=None) -> int:
    args = parser().parse_args(argv)
    system = system or t9.System()
    if args.dry_run:
        report = t9.preflight(args, system)
        try:
            issued, _, _ = trusted_inputs(args)
            report["issuedExpiresAt"] = issued.expires_at
            report["wiring"] = "ok"
        except (hn.NativeWiringError, _mac.LabError, OSError, ValueError) as exc:
            report["verdict"], report["wiring"] = "refused", getattr(exc, "reason", type(exc).__name__)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["verdict"] == "ready" else 2
    try:
        result = run_cohort(args, system)
    except t9.AttemptRefused as exc:
        print(json.dumps({"verdict": "refused", "reasons": exc.reasons, "details": exc.details, "nativeRun": False,
                          "executionAuthorization": False}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
