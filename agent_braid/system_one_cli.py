# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in offline decision command; file acquisition precedes core ingress."""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys


def read_input(path: Path) -> bytes:
    """Read at most 1 MiB from one regular local file, refusing symlink/FIFO."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 1_048_576:
            raise ValueError("invalid local input")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError("invalid local input")
        return raw
    finally:
        os.close(descriptor)


def run(args) -> int:
    # Imports remain lazy: legacy commands do not instantiate a decision runtime.
    from .system_one import canonical, thaw
    from .system_one_backends import DecisionRuntime, capabilities

    if args.decision_command in {"report", "purge"}:
        return _store_command(args)
    if args.decision_command == "promote":
        return _promote_command(args)
    if args.decision_command == "capabilities":
        print(canonical(thaw(capabilities())).decode("utf-8"))
        return 0
    try:
        raw = read_input(args.input)
    except (OSError, ValueError):
        print('{"error":"system-one requires a bounded regular local input file"}')
        return 2
    with DecisionRuntime() as runtime:
        response = runtime.evaluate(raw)
    print(canonical(response).decode("utf-8"))
    return {"answered": 0, "abstain": 1, "defer": 1, "refused": 2}[response["status"]]


def _store_command(args) -> int:
    """Shadow-store maintenance: counts and deletion only, never episode bodies."""
    import json
    from . import system_one_shadow as shadow
    try:
        if args.decision_command == "report":
            value = shadow.report()
            print(json.dumps(value, sort_keys=True, indent=2) if args.format == "json"
                  else shadow.render_report(value))
            return 0
        if not args.yes:
            try:
                answer = input("Delete all retained System One shadow episodes? [y/N] ")
            except EOFError:
                answer = ""
            if answer.strip().lower() not in {"y", "yes"}:
                print("purge cancelled")
                return 1
        print(json.dumps(shadow.purge(), sort_keys=True))
        return 0
    except shadow.StoreRefused as exc:
        print("system-one refused: " + ("the store is in use by another process; retry shortly"
                                        if str(exc) == "busy" else "the store is unavailable"), file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        # strerror carries no path; ValueError messages are System One wording without paths.
        print(f"system-one refused: {exc.strerror if isinstance(exc, OSError) else exc}", file=sys.stderr)
        return 2


def _promote_command(args, home=None, today=None) -> int:
    """Owner decision for DP-1: preview first, then record only with the previewed digest.

    A go pins the current shadow evidence digest and the installed rule manifest digest; a rollback
    demotes the decision point to off. Nothing here grants execution authority.
    """
    import hashlib
    import json
    from datetime import date
    from . import system_one_dp1_rule as rule, system_one_promotion as promotion, system_one_shadow as shadow

    def digest(value) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    point = args.decision_point
    try:
        records = promotion.load(home)
        if args.go:
            report = shadow.report()
            if not report["totals"]["episodes"]:
                print("system-one refused: no shadow episodes to pin; run shadow mode first", file=sys.stderr)
                return 2
            evidence = digest({key: value for key, value in report.items() if key != "refusalsThisProcess"})
            plan = {"decision": "go", "decisionPoint": point, "evidenceDigest": evidence,
                    "manifestDigest": rule.manifest_digest(), "ruleId": rule.RULE_ID,
                    "backendKind": rule.BACKEND_KIND, "episodes": report["totals"]["episodes"]}
        else:
            latest = records[-1]["recordDigest"] if records else None
            plan = {"decision": "rollback", "decisionPoint": point, "previousRecordDigest": latest}
        preview = digest(plan)
        if args.confirm is None:
            print(json.dumps(dict(plan, previewDigest=preview, executionAuthorization=False,
                                  next="re-run with --confirm <previewDigest> to record this decision"),
                             sort_keys=True, indent=2))
            return 0
        if args.confirm != preview:
            print("system-one refused: the confirmation does not match the current preview", file=sys.stderr)
            return 2
        decided_on = (today or date.today()).isoformat()
        if args.go:
            promotion.owner_go(home, point, backend_kind=rule.BACKEND_KIND, evidence_digest=plan["evidenceDigest"],
                               manifest_digest=plan["manifestDigest"], decided_on=decided_on)
        else:
            promotion.rollback(home, point, decided_on=decided_on)
        print(json.dumps({"recorded": plan["decision"], "decisionPoint": point, "previewDigest": preview,
                          "executionAuthorization": False}, sort_keys=True))
        return 0
    except shadow.StoreRefused:
        print("system-one refused: the store is unavailable or in use; retry shortly", file=sys.stderr)
        return 2
    except (promotion.PromotionError, OSError, ValueError) as exc:
        print(f"system-one refused: {getattr(exc, 'code', 'promotion-failed')}", file=sys.stderr)
        return 2
