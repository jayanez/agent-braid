# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5b T102: one-command outcome observer and its evidence.

    python -m scripts.spec066_s15b_observe                 # --yield-report: print counts, write nothing
    python -m scripts.spec066_s15b_observe --write         # append joined records; write the evidence JSON
    python -m scripts.spec066_s15b_observe --purge         # revocation path for the S1.5b store

`--purge` removes only the S1.5b outcome store (`system-one-s15b/`). The shadow store has
its own revocation command, `agent-braid system-one purge`; both are needed to revoke
everything. Evidence holds counts by closed key only: no path, workspace id, resource
name or identifier. Observational, one owner; it measures no accuracy and grants nothing.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `python scripts/spec066_s15b_observe.py` as well as `-m`
    sys.path.insert(0, str(ROOT))

from research import s15b_outcome_observer as observer  # noqa: E402

EVIDENCE = ROOT / "specs/066-system-one-shadow/evidence"
EVIDENCE_SCHEMA = "agent-braid-spec066-s15b-observe-evidence/v0.1"
LIMITS = [
    "Observational real use of one owner; no accuracy, utility or calibration is measured.",
    "Outcome kinds only; labels come from the frozen rubric (T103), never from this observer.",
    "Plan assumption A1 (a real source retains pair-level resource sets) is unverified; yield 0 is valid.",
    "Aggregate-only sources (SPEC-047, SPEC-053, SPEC-059) are not wired: no outcome is inferred from them.",
    "A pair analysed twice within the window is ambiguous and unlabelled; identical outcomes on one pair, kind and day collapse to one record.",
    "Pairs with 32 or more resources on a side cannot be matched (pseudonym lists are truncated) and stay unlabelled.",
    "Episodes of workspaces other than the admitted one are never joined, persisted or purged.",
]


def default_sources() -> list:
    """No real source retains pair-level resource sets today (plan A1, expected zero)."""
    return []


def build_evidence(mode: str, today, *, sources=None, home=None, consent_path=None, locations=None) -> tuple:
    result = observer.observe(default_sources() if sources is None else sources, today,
                              home=home, consent_path=consent_path)
    counts = {name: result.counts[name] for name in observer.COUNTERS}
    counts.update({key: value for key, value in sorted(result.counts.items()) if key.startswith("refused:")})
    evidence = {"schema": EVIDENCE_SCHEMA, "date": today.isoformat(), "mode": mode,
                "counts": counts, "joinedByOutcomeKind": {
                    kind: sum(1 for record in result.records if record["outcomeKind"] == kind)
                    for kind in observer.OUTCOME_KINDS},
                "inventory": observer.inventory(home=home, consent_path=consent_path, locations=locations),
                "positiveControl": observer.positive_control(),
                "limits": list(LIMITS), "executionAuthorization": False}
    return evidence, result


def write_evidence(evidence: dict, directory: Path) -> Path:
    target = directory / f"s15b-observe-{evidence['date']}.json"
    descriptor, name = tempfile.mkstemp(dir=directory, prefix=".s15b-observe-")
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    os.chmod(name, 0o644)
    os.replace(name, target)
    return target


def main(argv=None, *, today=None, evidence_directory: Path = EVIDENCE, **options) -> int:
    parser = argparse.ArgumentParser(prog="spec066_s15b_observe", description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--yield-report", action="store_true", help="print counts, write nothing (default)")
    mode.add_argument("--write", action="store_true", help="append joined records and write the evidence JSON")
    mode.add_argument("--purge", action="store_true", help="remove the S1.5b outcome store")
    args = parser.parse_args(argv)
    today = today or observer.utc_today()
    try:
        if args.purge:
            print(json.dumps(observer.purge(), sort_keys=True))
            return 0
        evidence, result = build_evidence("write" if args.write else "yield-report", today, **options)
        if args.write:
            for key, value in observer.write_records(result.records, today).items():
                evidence["counts"][key] = evidence["counts"].get(key, 0) + value
            write_evidence(evidence, evidence_directory)
    except (observer.ObserverRefused, OSError):
        print("refused: the S1.5b store is unavailable or unsafe", file=sys.stderr)
        return 2
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if all(evidence["positiveControl"].values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
