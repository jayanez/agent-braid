# SPDX-License-Identifier: AGPL-3.0-only
"""Restore exact already-public reviewed and draft candidates for portable validation.

Some squash-merged public candidates and their reviewed tags are omitted by
clones. Restore the exact SPEC-012 candidate and the pinned annotated tags used
by historical assurance, preserving the records and the public-root boundary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ASSURANCE = ROOT / "specs/012-m2-git-replay-planner/assurance.json"
REF = "refs/remotes/origin/spec-012-reviewed-candidate"
PUBLIC_ROOT_COMMIT = "9b84467d54444138db8c000f442d9aea6040cab2"
# Immutable annotated tag objects already published in the public repository.
# These restore public history, never grant a new review or import private roots.
REVIEWED_TAGS = (
    ("016-m2-partial-order-reduction", "0974739ae4dc6784ff3c21a34745655a38dd4943",
     "5d6744217595027df87d56fa307a069941af1263"),
    ("018-structured-exchange", "2656924e51cccf4017a31563ae044c47efcc395d",
     "75f2a98f038a233540f0d83ed0fe68646435f792"),
    ("020-m4-local-git-runtime", "853df7432dd4700aa411f1f13b324a0b7beecd02",
     "6248172cb38b0d6a3ce1d077ad64544380bd1f0e"),
)
# Already-public approved metadata, as published in merged develop c51c91e.
# Freezing a candidate initially records pending review; these commitments retain
# the subsequently published reviewed metadata without inventing new approval.
# Tuple: feature, assurance SHA256, review record path, review SHA256.
PUBLIC_REVIEW_RECORDS = (
    ("016-m2-partial-order-reduction",
     "0d2007d2515e871c41d7c86e9afc0f1a2a2e022cd461d24966b954f4dae67764",
     "specs/016-m2-partial-order-reduction/founder-review.json",
     "03eb634a8562b9c20cdb4475dfb8aaa06938d80eec5009d1b7015880767e0d51"),
    ("018-structured-exchange",
     "9a0b3ee082b70ecc402897473927cbe39cb20997ef7be599e258c669c4cf3fa7",
     "specs/018-structured-exchange/founder-review.json",
     "3653a6f784211f4f3cb1618c1cd57728f8b367f7b52bd70941f7b085b804a3e3"),
    ("020-m4-local-git-runtime",
     "f09968de6e77bfd93793100ae2ddd14f1563ff7a2f3df8e6f7429b34d0e57c29",
     "specs/020-m4-local-git-runtime/founder-review-corrected.json",
     "f0654f1e2bc48cc9b777cd4afdc463a085a7b38e5d90fab98f5fb09f59b58732"),
)
# Exact already-public draft candidate; retention is not reviewer approval.
# Tuple: record path, tag ref, peeled candidate, immutable annotated tag object.
PRESERVED_DRAFT_TAGS = (
    ("specs/019-native-predictor/assurance.json",
     "refs/tags/spec-019-software-candidate-c30e8bc",
     "c30e8bcfb572afba4447767fc2b51dd2c3320766",
     "04f89c868406193be104c1f66360223907db4c38"),
    ("specs/044-ai-tooling-evaluation/assurance.json",
     "refs/tags/m45-tooling-candidate-8df6c9f",
     "8df6c9f410f0559dc667833b8a4f71f1685d3ea0",
     "2f2f6f4ec199d43ecc9ec3e2597875ab7547257a"),
)


def git(*args: str, allow_failure: bool = False) -> str:
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_GRAFT_FILE"] = os.devnull
    result = subprocess.run(["git", "-C", str(ROOT), *args], env=environment,
                            capture_output=True, check=False, text=True, timeout=90)
    if result.returncode and not allow_failure:
        raise ValueError(f"Git public-history check failed: {args[0]}")
    return result.stdout.strip() if result.returncode == 0 else ""


def reviewed_tag_ref(feature: str, candidate: str, tag_object: str,
                     public_root: str) -> str:
    record = json.loads((ROOT / "specs" / feature / "assurance.json").read_text())
    if (record.get("human_review") != "approved"
            or record.get("authority_snapshot", {}).get("mode") != "historical"
            or record["authority_snapshot"].get("commit") != candidate
            or record.get("evidence_snapshot") != {"mode": "historical", "commit": candidate}):
        raise ValueError(f"SPEC-{feature[:3]} record does not match the pinned reviewed candidate")
    review_path = (ROOT / record.get("review_record", "")).resolve()
    if (not review_path.is_relative_to(ROOT.resolve()) or not review_path.is_file()
            or json.loads(review_path.read_text()).get("reviewedCommit") != candidate):
        raise ValueError(f"SPEC-{feature[:3]} review does not match the pinned candidate")
    ref = f"refs/tags/spec-{feature[:3]}-reviewed-{candidate[:7]}"
    existing = git("rev-parse", "--verify", ref, allow_failure=True)
    if existing and existing != tag_object:
        raise ValueError(f"reviewed tag has an unexpected local identity: {ref}")
    if not existing:
        remote = dict(line.split("\t") for line in git(
            "ls-remote", "--tags", "origin", ref, ref + "^{}",
        ).splitlines())
        if remote.get(tag_object) != ref or remote.get(candidate) != ref + "^{}":
            raise ValueError(f"reviewed tag has an unexpected public identity: {ref}")
    if git("rev-parse", "--verify", f"{candidate}^{{commit}}", allow_failure=True) \
            and git("merge-base", public_root, candidate, allow_failure=True) != public_root:
        raise ValueError(f"reviewed candidate does not descend from the public root: {ref}")
    return ref


def verify_reviewed_tag(ref: str, candidate: str, tag_object: str, public_root: str) -> None:
    if (git("rev-parse", "--verify", ref) != tag_object
            or git("cat-file", "-t", ref) != "tag"
            or git("rev-parse", f"{ref}^{{commit}}") != candidate):
        raise ValueError(f"reviewed annotated tag does not match its pinned target: {ref}")
    if git("merge-base", public_root, candidate, allow_failure=True) != public_root:
        raise ValueError(f"reviewed candidate does not descend from the public root: {ref}")


def restore_reviewed_tag(feature: str, candidate: str, tag_object: str,
                         public_root: str) -> str:
    ref = reviewed_tag_ref(feature, candidate, tag_object, public_root)
    if not git("rev-parse", "--verify", ref, allow_failure=True):
        git("fetch", "--atomic", "--quiet", "--no-tags", "origin", f"{tag_object}:{ref}")
    verify_reviewed_tag(ref, candidate, tag_object, public_root)
    return ref


def preserved_tag_ref(ref: str, candidate: str, tag_object: str,
                      public_root: str) -> str:
    """Preflight one literal public draft pin without granting any review."""
    existing = git("rev-parse", "--verify", ref, allow_failure=True)
    if existing and existing != tag_object:
        raise ValueError(f"preserved tag has an unexpected local identity: {ref}")
    if not existing:
        remote = dict(line.split("\t") for line in git(
            "ls-remote", "--tags", "origin", ref, ref + "^{}",
        ).splitlines())
        if remote.get(tag_object) != ref or remote.get(candidate) != ref + "^{}":
            raise ValueError(f"preserved tag has an unexpected public identity: {ref}")
    if git("rev-parse", "--verify", f"{candidate}^{{commit}}", allow_failure=True) \
            and git("merge-base", public_root, candidate, allow_failure=True) != public_root:
        raise ValueError(f"preserved candidate does not descend from the public root: {ref}")
    return ref


def main() -> int:
    record = json.loads(ASSURANCE.read_text())
    authority = record["authority_snapshot"]
    evidence = record["evidence_snapshot"]
    candidate = authority.get("commit")
    if (authority.get("mode") != "historical"
            or evidence.get("mode") != "historical"
            or evidence.get("commit") != candidate
            or not isinstance(candidate, str)
            or not re.fullmatch(r"[0-9a-f]{40}", candidate)):
        raise ValueError("SPEC-012 reviewed candidate is not consistently frozen")
    origin = git("remote", "get-url", "origin")
    if origin not in {
        "https://github.com/jayanez/agent-braid",
        "https://github.com/jayanez/agent-braid.git",
        "git@github.com:jayanez/agent-braid.git",
    }:
        raise ValueError("origin must be the public Agent Braid repository")
    roots = git("rev-list", "--max-parents=0", "HEAD").splitlines()
    if roots != [PUBLIC_ROOT_COMMIT]:
        raise ValueError("public checkout must have the pinned clean public root")
    if git("rev-list", "--max-parents=0", "--all").splitlines() != roots:
        raise ValueError("public checkout contains an additional root; refs not changed")
    existing_candidate_ref = git("rev-parse", "--verify", REF, allow_failure=True)
    if existing_candidate_ref and existing_candidate_ref != candidate:
        raise ValueError("SPEC-012 local ref has an unexpected identity; not overwritten")
    # Preflight every record and advertised identity before changing any refs.
    reviewed = [(reviewed_tag_ref(feature, commit, oid, roots[0]), commit, oid)
                for feature, commit, oid in REVIEWED_TAGS]
    preserved = [(preserved_tag_ref(ref, commit, oid, roots[0]), commit, oid)
                 for _, ref, commit, oid in PRESERVED_DRAFT_TAGS]
    refspecs = [] if existing_candidate_ref else [f"{candidate}:{REF}"]
    refspecs.extend(f"{oid}:{ref}" for ref, _, oid in reviewed + preserved
                    if not git("rev-parse", "--verify", ref, allow_failure=True))
    if refspecs:
        # Fetch immutable object IDs with one atomic ref update. A later missing
        # object or conflicting tag cannot leave earlier refs partially installed.
        git("fetch", "--atomic", "--quiet", "--no-tags", "origin", *refspecs)
    if git("rev-parse", "--verify", f"{candidate}^{{commit}}") != candidate:
        raise ValueError("reviewed candidate is unavailable after fetch")
    if git("merge-base", roots[0], candidate, allow_failure=True) != roots[0]:
        raise ValueError("reviewed candidate does not descend from the public root")
    print(f"SPEC-012 historical candidate reachable at {REF}; no remote ref changed.")
    for ref, reviewed_commit, tag_object in reviewed:
        verify_reviewed_tag(ref, reviewed_commit, tag_object, roots[0])
        print(f"Public reviewed candidate restored at {ref}; no approval inferred.")
    for ref, preserved_commit, tag_object in preserved:
        verify_reviewed_tag(ref, preserved_commit, tag_object, roots[0])
        print(f"Public draft candidate preserved at {ref}; no approval inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
