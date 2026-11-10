# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5b T106: one command for git-history replay labels (REQ-104).

    python -m scripts.spec066_s15b_replay_labels --repository PATH --owner-email ADDRESS --dry-run
    python -m scripts.spec066_s15b_replay_labels --repository PATH --owner-email ADDRESS --write \
        [--addendum FILE]

The repository must pass the W0 corpus gate (consent, plugin registry, admitted workspace) and the
`git-history-replay` source family must be admitted by a digest-bound consent addendum. The T101
record does not list that family, so until the owner records an addendum every real repository is
refused (`source-family-not-admitted`); the tool is exercised on temporary repositories by its tests.
`--dry-run` prints the counts-only evidence JSON and writes nothing. `--write` stores the structural
records in the private S1.5b store (30-day retention) and writes
`specs/066-system-one-shadow/evidence/s15b-replay-<date>.json`. The owner address only selects
commits in memory; it is never stored, printed or sent. A refusal prints its closed code only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `python scripts/spec066_s15b_replay_labels.py` as well as `-m`
    sys.path.insert(0, str(ROOT))

from research import s15b_corpus_gate as gate, s15b_git_history_replay as replay  # noqa: E402

EVIDENCE = ROOT / "specs/066-system-one-shadow/evidence"


def _load_addendum(path: str | None) -> dict | None:
    if path is None:
        return None
    try:
        raw = gate._read_record(Path(path))
        value = json.loads(raw) if len(raw) <= gate.MAX_RECORD_BYTES else None
    except (ValueError, RecursionError, gate.GateRefusal):
        raise gate.GateRefusal("source-family-not-admitted") from None
    return value if isinstance(value, dict) else None


def main(argv=None, *, output_dir: Path = EVIDENCE, home: Path | None = None, consent_path: Path | None = None,
         salt_dir: Path | None = None, store: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spec066_s15b_replay_labels", description=__doc__.split("\n")[0])
    parser.add_argument("--repository", required=True, help="repository path; must pass the corpus gate")
    parser.add_argument("--owner-email", required=True, help="author address of the commits to replay (not stored)")
    parser.add_argument("--addendum", help="digest-bound consent addendum adding the git-history-replay family")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="print the evidence; write nothing")
    mode.add_argument("--write", action="store_true", help="write the records and the evidence file")
    args = parser.parse_args(argv)
    try:
        result = replay.replay(args.repository, owner_email=args.owner_email, addendum=_load_addendum(args.addendum),
                               home=home, consent_path=consent_path, salt_dir=salt_dir)
        if args.write:
            replay.write_records(result["records"], store=store)
    except (gate.GateRefusal, replay.ReplayError) as refusal:
        print("refused: " + refusal.code, file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - a closed message only: a traceback would echo the repository path
        print("refused: internal-error", file=sys.stderr)
        return 2
    text = json.dumps(result["evidence"], indent=2, sort_keys=True) + "\n"
    if args.write:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"s15b-replay-{result['evidence']['date']}.json").write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
