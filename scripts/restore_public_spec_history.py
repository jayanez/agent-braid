# SPDX-License-Identifier: AGPL-3.0-only
"""Restore exact already-public reviewed candidates for portable validation.

The public repository squash-merged its implementation PR, so a normal clone
does not retain the candidate commit named by historical assurance. This tool
fetches only that exact public commit and adds a local remote-tracking ref.
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


def git(*args: str, allow_failure: bool = False) -> str:
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
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
    if len(roots) != 1:
        raise ValueError("public checkout must have one clean root")
    existing_candidate_ref = git("rev-parse", "--verify", REF, allow_failure=True)
    if existing_candidate_ref and existing_candidate_ref != candidate:
        raise ValueError("SPEC-012 local ref has an unexpected identity; not overwritten")
    # Preflight every record and advertised identity before changing any refs.
    reviewed = [(reviewed_tag_ref(feature, commit, oid, roots[0]), commit, oid)
                for feature, commit, oid in REVIEWED_TAGS]
    refspecs = [] if existing_candidate_ref else [f"{candidate}:{REF}"]
    refspecs.extend(f"{oid}:{ref}" for ref, _, oid in reviewed
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
