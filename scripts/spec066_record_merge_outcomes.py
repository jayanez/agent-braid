# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T405 (REQ-402): record the merge outcomes of one wave of the owner's parallel work.

    python -m scripts.spec066_record_merge_outcomes --repository PATH --head BRANCH_OR_SHA --head ... [--base REV]
        [--owner-email ADDRESS] [--day YYYY-MM-DD] (--dry-run | --write)

Every pair of the given heads gets the `git merge-tree --write-tree` verdict (read-only oracle in an empty
scratch repository with a sanitized environment, the same one the git-history replay uses) and the salted
pseudonym lists a System One shadow episode would record for the same pair, so the observer
(`scripts/spec066_s15b_observe.py`) can join the outcome to the episodes of the same work and measure the
false-independence rate of the DP-1 rule. `--dry-run` (default) prints counts only; `--write` stores the
structural records in the gitignored file under the admitted workspace's source root.

Refused with a closed code, never an input: a repository outside the admitted workspace (corpus gate), a
source family the T101 consent does not list, a missing store secret, an output path the repository does not
ignore. With `--write`, and only when the registry's `systemOne` consent is `shadow` or `advise`, each new
outcome also stores the replay shadow episode of the same pair, so the observer has an episode to join. Only commits authored by the owner are used (address matched in memory, never stored or printed); a
pair with any other author is skipped and counted. Records hold the verdict, the day, pseudonym lists and a
count: no path, ref, commit id, author, message or workspace id. Nothing here grants authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `python scripts/spec066_record_merge_outcomes.py` as well as `-m`
    sys.path.insert(0, str(ROOT))

from agent_braid import system_one_dp1_rule as rule, system_one_shadow as shadow  # noqa: E402
from agent_braid.git_adapter import analyze_git_with_provenance  # noqa: E402
from agent_braid.git_process import GitCommandFailure, GitInfrastructureFailure  # noqa: E402
from research import s15b_corpus_gate as gate, s15b_git_history_replay as replay  # noqa: E402
from research import s15b_merge_outcomes as outcomes, s15b_outcome_observer as observer  # noqa: E402

EVIDENCE_SCHEMA = "agent-braid-spec066-merge-outcomes-evidence/v0.1"
MAX_HEADS = 12
ERRORS = ("owner-identity-missing", "too-few-heads", "head-unresolved", "not-a-worktree", "git-unavailable",
          "secret-absent", "no-salt", "analysis-failed")
SKIPPED = ("objects-missing", "not-diverged", "author-excluded", "author-unverifiable")
UNLABELLED = ("git-too-old", "no-merge-base", "too-many-paths", "oracle-error", "analysis-error")
LIMITS = [
    "merge-tree labels textual cleanliness of the pair, not semantic independence or test success.",
    "Pseudonyms come from the Git adapter's change set of each head against the base; a pair with a deleted or "
    "unsupported path carries an operation id the live episode used, so it cannot match and stays unjoined.",
    "Only owner-authored commits are used; one person's parallel work is not a population.",
    "Records are rolling: kept 30 days from their day, identical bodies collapse.",
    "Episodes written by --write are replay episodes: built after the merge from the pair's two heads with the "
    "live analysis, so the join of these pairs holds by construction. The rule never sees the verdict. They are "
    "not distinguishable from live episodes in the shadow store.",
]


class RecordError(Exception):
    """A fixed code from `ERRORS`; the message is the code and carries nothing else."""

    def __init__(self, code: str) -> None:
        if code not in ERRORS:
            raise ValueError("unknown record error code")
        self.code = code
        super().__init__(code)


def _owner_from_config(root: Path) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), "config", "--get", "user.email"], capture_output=True,
                              text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() or None


def _resolve(ctx, root: Path, revision: str, budget) -> str:
    if not isinstance(revision, str) or not revision or revision.startswith("-") or "\0" in revision:
        raise RecordError("head-unresolved")
    done = ctx.git(root, "rev-parse", "--verify", "-q", f"{revision}^{{commit}}", budget=budget)
    oid = replay._text(done.stdout)
    if done.returncode or not replay._OID.fullmatch(oid):
        raise RecordError("head-unresolved")
    return oid


def _pair_variants(ctx, request: dict, salts, live_salt=None) -> tuple:
    """`(variants, canonicalSharedCount, episode)` as a live episode of this pair would record them.

    `episode` is the one built with `live_salt` (the salt of the registered source root), else None."""
    try:
        report, _ = analyze_git_with_provenance(request, env=ctx.env, budget=ctx.budget())
        sides = {entry["instanceId"]: entry["resources"] for entry in report["operations"]}
        variants, live = [], None
        for salt in salts:
            episode = shadow.build_episode(report, "analyze", "git", request=request, salt=salt)
            shadow.validate_episode(episode)
            if len(episode["pairs"]) != 1 or episode["pairs"][0]["resourceHashes"] is None:
                raise ValueError
            variants.append(episode["pairs"][0]["resourceHashes"])
            if salt == live_salt:
                live = episode
        shared = len(rule.shared_canonical(sides["left"], sides["right"]))
    except Exception:  # noqa: BLE001 - any analysis failure is the closed reason, never its text
        raise replay._Unlabelled("analysis-error") from None
    return variants, shared, live


def record_wave(repository, heads, *, owner_email: str | None = None, base: str | None = None,
                home: Path | None = None, consent_path: Path | None = None, run_day: date | None = None) -> dict:
    """Gate, label every pair of `heads`. Returns `{records, evidence}`; writes nothing."""
    heads = list(dict.fromkeys(heads))
    if not 2 <= len(heads) <= MAX_HEADS:
        raise RecordError("too-few-heads")
    consent = gate.load_consent(consent_path)
    gate.admit_path(repository, home=home, consent_path=consent_path)
    gate.require_source_family(outcomes.FAMILY, consent=consent)
    day = run_day or replay.today()
    with tempfile.TemporaryDirectory(prefix="agent-braid-merge-outcomes-") as directory:
        ctx = replay._Context(Path(directory).resolve())
        try:
            top = ctx.git(Path(os.path.realpath(repository)), "rev-parse", "--show-toplevel",
                          budget=ctx.budget(commands=4))
            if top.returncode or not replay._text(top.stdout):
                raise RecordError("not-a-worktree")
            root = Path(os.path.realpath(replay._text(top.stdout)))
            gate.admit_path(root, home=home, consent_path=consent_path)
            owner = (owner_email or _owner_from_config(root) or "").strip().casefold()
            if "@" not in owner:
                raise RecordError("owner-identity-missing")
            secret = observer.read_secret()
            if secret is None:
                raise RecordError("secret-absent")
            salts = observer.candidate_salts(secret, observer.candidate_roots(home=home))
            if not salts:
                raise RecordError("no-salt")
            registered = observer.registered_root(home=home)
            live_salt = shadow._repo_salt(secret, registered[0]) if registered else None
            version = replay.git_version(ctx)
            old_git = version is None or version < replay.MIN_GIT
            shallow_answer = ctx.git(root, "rev-parse", "--is-shallow-repository", budget=ctx.budget(commands=4))
            if shallow_answer.returncode or replay._text(shallow_answer.stdout) not in ("true", "false"):
                raise RecordError("git-unavailable")
            shallow = replay._text(shallow_answer.stdout) == "true"
            budget = ctx.budget(commands=64)
            oids = list(dict.fromkeys(_resolve(ctx, root, head, budget) for head in heads))
            if len(oids) < 2:
                raise RecordError("too-few-heads")
            base_oid = _resolve(ctx, root, base, budget) if base is not None else None
            records, episodes, skipped, unlabelled, enumerated = [], [], Counter(), Counter(), 0
            for left, right in itertools.combinations(oids, 2):
                enumerated += 1
                pair = replay._Pair("branch-tip", left, right)
                reason = replay._precheck(ctx, root, pair, owner, shallow, ctx.budget())
                if reason:
                    skipped[reason] += 1
                    continue
                try:
                    if old_git:
                        raise replay._Unlabelled("git-too-old")
                    if pair.base is None:
                        raise replay._Unlabelled("no-merge-base")
                    for oid in (left, right):
                        if replay._changed_paths(ctx, root, base_oid or pair.base, oid, ctx.budget()) > replay.MAX_SIDE_PATHS:
                            raise replay._Unlabelled("too-many-paths")
                    kind = replay._oracle(ctx, root, pair, ctx.budget())
                    request = replay._request(root, pair)
                    if base_oid is not None:
                        request["baseRevision"] = base_oid
                    variants, shared, episode = _pair_variants(ctx, request, salts, live_salt)
                    records.append(outcomes.make_record(kind, day, variants, shared))
                    episodes.append(episode)
                except replay._Unlabelled as exc:
                    unlabelled[exc.reason] += 1
                except (GitCommandFailure, GitInfrastructureFailure, OSError):
                    unlabelled["oracle-error"] += 1
        except (GitCommandFailure, GitInfrastructureFailure, OSError):
            raise RecordError("git-unavailable") from None
    if enumerated and not records and unlabelled["analysis-error"] == enumerated - sum(skipped.values()) > 0:
        raise RecordError("analysis-failed")
    by_kind = Counter(record["outcomeKind"] for record in records)
    evidence = {"schema": EVIDENCE_SCHEMA, "date": day.isoformat(), "executionAuthorization": False,
                "pairs": {"enumerated": enumerated, "recorded": len(records),
                          "byKind": {kind: by_kind.get(kind, 0) for kind in outcomes.KINDS},
                          "skipped": {name: skipped.get(name, 0) for name in SKIPPED},
                          "unlabelled": {name: unlabelled.get(name, 0) for name in UNLABELLED}},
                "retentionDays": gate.RETENTION_DAYS, "limits": list(LIMITS)}
    return {"records": records, "episodes": episodes, "systemOne": registered[1] if registered else "off",
            "evidence": evidence}


def new_episodes(directory: Path, result: dict, run_day: date) -> tuple:
    """`(episodes, counts)`: one replay episode per outcome record not yet stored, so a rerun never doubles a pair.

    Needs the registry's explicit `shadow` or `advise` consent (REQ-001). Call before the records are written.
    """
    if result["systemOne"] not in ("shadow", "advise"):
        return [], {"consent-off": len(result["records"])}
    known = {outcomes._body(record) for record in outcomes.read_records(directory, run_day)}
    counts, fresh = Counter(), []
    for record, episode in zip(result["records"], result["episodes"]):
        if outcomes._body(record) in known:
            counts["duplicate"] += 1
        elif episode is None:
            counts["no-episode"] += 1
        else:
            fresh.append(episode)
    return fresh, counts


def write_episodes(episodes, counts: Counter) -> dict:
    """Append the episodes to the shadow store; a refused append is counted, never raised."""
    for episode in episodes:
        try:
            shadow.append(episode)
            counts["written"] += 1
        except shadow.StoreRefused as refusal:
            counts["refused:" + str(refusal)] += 1
    return dict(counts)


def _require_ignored(directory: Path) -> None:
    """The output must be ignored by the repository that holds it, or nothing is written."""
    target = directory / outcomes.FILENAME
    probe = subprocess.run(["git", "-C", str(directory.parents[len(outcomes.DIRECTORY) - 1]), "check-ignore", "-q",
                            "--", str(target)], capture_output=True, timeout=30, check=False)
    if probe.returncode != 0:
        raise outcomes.MergeOutcomeError("output-not-ignored")


def main(argv=None, *, home: Path | None = None, consent_path: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spec066_record_merge_outcomes", description=__doc__.split("\n")[0])
    parser.add_argument("--repository", required=True, help="repository path; must pass the corpus gate")
    parser.add_argument("--head", action="append", required=True, help="branch or commit of one merged head (2+)")
    parser.add_argument("--base", help="base revision for the change sets (default: each pair's merge-base)")
    parser.add_argument("--owner-email", help="author address of the commits to use (default: git config; not stored)")
    parser.add_argument("--day", help="record day YYYY-MM-DD (default: today, UTC)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="print the counts; write nothing (default)")
    mode.add_argument("--write", action="store_true", help="store the records under the admitted source root")
    args = parser.parse_args(argv)
    try:
        run_day = date.fromisoformat(args.day) if args.day else None
        result = record_wave(args.repository, args.head, owner_email=args.owner_email, base=args.base, home=home,
                             consent_path=consent_path, run_day=run_day)
        evidence = result["evidence"]
        if args.write:
            directory = outcomes.store_directory(home=home)
            _require_ignored(directory)
            today = run_day or replay.today()
            fresh, episode_counts = new_episodes(directory, result, today)
            evidence["store"] = dict(outcomes.write_records(directory, result["records"], today))
            evidence["episodes"] = write_episodes(fresh, Counter(episode_counts))
    except (gate.GateRefusal, RecordError, outcomes.MergeOutcomeError) as refusal:
        print("refused: " + refusal.code, file=sys.stderr)
        return 2
    except (ValueError, OSError):
        print("refused: invalid-arguments-or-store", file=sys.stderr)
        return 2
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
