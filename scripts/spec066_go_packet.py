# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T406: the owner GO decision packet for the System One DP-1 rule.

    python -m scripts.spec066_go_packet            # plain-language packet
    python -m scripts.spec066_go_packet --json     # the same facts, machine readable

Read-only and offline. It reads the local shadow episodes, the stored joined outcomes (written by
`scripts/spec066_s15b_observe.py --write`) and the promotion registry; it creates, changes and records
nothing, and it never records a go: the go stays the owner's two-step `system-one promote` command.
Counts only; no path, resource or identifier is printed. It grants no execution authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `python scripts/spec066_go_packet.py` as well as `-m`
    sys.path.insert(0, str(ROOT))

from agent_braid import system_one_dp1_rule as rule, system_one_promotion as promotion, system_one_shadow as shadow  # noqa: E402
from research import s15b_outcome_observer as observer  # noqa: E402

SCHEMA = "agent-braid-spec066-go-packet/v0.1"
POINT = observer.DECISION_POINT
PACKET_DATE, LIVE_DATE, REVIEW_DATE = "2026-11-28", "2026-11-30", "2026-12-31"
RISK = ("DP-1 advise lets the rule tell agents that two tasks are likely independent when System 2 cannot "
        "decide. A wrong answer can send two agents to edit the same files and cause a merge conflict. It "
        "advises only: it never blocks or runs anything. The first joined merge conflict on an advised "
        "likely-independent pair rolls DP-1 back to shadow by itself.")


def _stored_outcomes() -> list:
    """Joined outcome records, read without the observer's lock or expiry purge (it deletes old files)."""
    root = observer._open_store(create=False)
    return [] if root is None else observer._read_store(root)


def build_packet(today: date, *, home: Path | None = None) -> dict:
    counts = Counter()
    observer.read_episodes(today, counts)
    shadow_report = shadow.report()
    advised = counts["advised-pairs"]
    unknown = shadow_report["unknownPairs"]
    outcomes = observer.false_independence(_stored_outcomes(), advised)
    records = promotion.load(home)
    latest = next((r for r in reversed(records) if r["decisionPoint"] == POINT), None)
    active = promotion.resolve("advise", records, rule.manifest_digest())["decisionPoints"][POINT]
    trials = outcomes["falseIndependent"] + outcomes["advisedMergeClean"]
    if outcomes["falseIndependent"]:
        verdict = "blocked-false-independence"
    elif not trials:
        verdict = "no-evidence"
    else:
        verdict = "ready-for-owner-decision"
    return {"schema": SCHEMA, "today": today.isoformat(), "decisionPoint": POINT,
            "shadowEpisodes": shadow_report["totals"]["episodes"],
            "unknownPairs": unknown, "advisedPairs": advised,
            "coverage": round(advised / unknown, 6) if unknown else None,
            "joinedOutcomes": outcomes["joinedOutcomes"], "advisedTrials": trials,
            "falseIndependent": outcomes["falseIndependent"], "wilson95Upper": outcomes["wilson95Upper"],
            "registry": {"records": len(records),
                         "latest": None if latest is None else {"decision": latest["decision"],
                                                                "decidedOn": latest["decidedOn"],
                                                                "reason": latest.get("reason")},
                         "ifConfigured": {"advise": active}},
            "verdict": verdict, "risk": RISK,
            "dates": {"packet": PACKET_DATE, "adviseLive": LIVE_DATE, "mandatoryReview": REVIEW_DATE},
            "executionAuthorization": False}


def _go_steps(packet: dict) -> list:
    latest = packet["registry"]["latest"]
    if latest is not None and latest["decision"] == "go":
        return [f"A go is already recorded (decided {latest['decidedOn']}). Do not record another.",
                "Effective only when the installed rule manifest still matches it; status above shows "
                f"DP-1 would run as '{packet['registry']['ifConfigured']['advise']['activeMode']}' "
                f"(reason {packet['registry']['ifConfigured']['advise']['reason']})."]
    prefix = ["Previous record: " + ("rollback" + (f" ({latest['reason']})" if latest["reason"] else "")
                                     + f" on {latest['decidedOn']}; a new go supersedes it.")] if latest else []
    return prefix + [
        "1. agent-braid plugin setup --system-one advise",
        f"2. agent-braid system-one promote --decision-point {POINT} --go",
        "   It prints a previewDigest and records nothing.",
        f"3. agent-braid system-one promote --decision-point {POINT} --go --confirm <previewDigest>",
        "   Only this step records the go.",
        "4. Reconnect the Agent Braid MCP server so it reads the new registry.",
    ]


def render(packet: dict) -> str:
    bound, trials = packet["wilson95Upper"], packet["advisedTrials"]
    cover = "none (no unknown pairs recorded)" if packet["coverage"] is None else (
        f"{packet['advisedPairs']} advised of {packet['unknownPairs']} unknown ({packet['coverage']:.1%})")
    registry = packet["registry"]
    latest = registry["latest"]
    lines = [f"System One {POINT} GO decision packet ({packet['schema']}), read {packet['today']}",
             "This packet records nothing. A go is recorded only by the owner's commands below.", "",
             "EVIDENCE",
             f"- Shadow episodes: {packet['shadowEpisodes']}",
             f"- Advised pairs recorded in shadow (rule said likely-independent): {packet['advisedPairs']}",
             f"- Coverage: {cover}",
             f"- Joined outcomes: {packet['joinedOutcomes']} ({trials} with a merge verdict on an advised pair)",
             f"- False independent (advised pair that then conflicted): {packet['falseIndependent']}",
             "- Wilson 95% upper bound on the false-independence rate: "
             + ("uninformative: no advised pair has a joined merge verdict yet" if bound is None
                else f"{bound:.1%} from {trials} advised trial{'s' if trials != 1 else ''}"),
             "", "STATE",
             "- Promotion registry: " + ("empty, DP-1 stays shadow (no owner go)" if latest is None else
                                         f"{registry['records']} record(s), latest {latest['decision']} on {latest['decidedOn']}"),
             f"- Verdict: {packet['verdict']}"
             + {"no-evidence": " (a go would rest on no measured outcome)",
                "blocked-false-independence": " (a false independence exists; review it before any go)",
                "ready-for-owner-decision": " (evidence exists; the decision and its risk are the owner's)"}[packet["verdict"]],
             "", "RISK", packet["risk"], "", "TO GO (owner)", *_go_steps(packet), "",
             "TO UNDO (owner)",
             f"- agent-braid system-one promote --decision-point {POINT} --rollback, then the same command with --confirm <previewDigest>",
             "- agent-braid plugin setup --system-one shadow   (keep recording, advise nothing)",
             "- agent-braid plugin setup --system-one off      (stop recording)",
             "", "DATES",
             f"- Packet {packet['dates']['packet']}; advise live {packet['dates']['adviseLive']} only on a recorded go; "
             f"mandatory review {packet['dates']['mandatoryReview']}."]
    return "\n".join(lines)


def main(argv=None, *, today: date | None = None, home: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spec066_go_packet", description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="print the facts as JSON")
    args = parser.parse_args(argv)
    try:
        packet = build_packet(today or observer.utc_today(), home=home)
    except (observer.ObserverRefused, promotion.PromotionError, shadow.StoreRefused, OSError, ValueError):
        print("refused: the System One state is unavailable or unsafe", file=sys.stderr)
        return 2
    print(json.dumps(packet, indent=2, sort_keys=True) if args.json else render(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
