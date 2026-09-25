#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only preflight for the frozen, still-unapproved M2 performance retest.

This command checks inputs and fail-closed controls. It never prepares Git
lanes, runs repository code, or grants execution authority.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_real_workload_manifest import _validate_manifest, PUBLIC_ROOT


PROPOSAL_COMMIT = "87640e950d0ac3231a93446225ef7608ebe3d980"
INPUT_PATH = "docs/experiments/m2-real-corpus-retest-inputs.json"
PROPOSAL_PATH = "docs/experiments/M2_REAL_CORPUS_RETEST_PROPOSAL.md"
INPUT_SHA256 = "fcf9ce54184e4e0528f46b3ef0da2be4c9678a940cdf99d6afa58a805ee5ff31"
PROPOSAL_SHA256 = "5c5eb4384fd8e5978a2bbe5da0212aa7796f7e7f0badbba2b42784e70093bcc9"
FEATURE = "specs/013-m2-real-workload"
IMAGE = "sha256:edddb1cbcbccb0e1af6505f9ff9938905da6f79303c97d1d12092ef61508f005"
PERFORMANCE_PR_BASE = "3b51fb6335400c5673f1ba40cf028a6ac6d525ca"
EXPECTED_LIMITS = {
    "cpusPerContainer": 2,
    "memoryBytesPerContainer": 2 * 1024**3,
    "pidsPerContainer": 512,
    "secondsPerContainer": 180,
    "capturedOutputBytesPerLane": 8 * 1024**2,
    "network": "none",
    "hostWrites": False,
    "sourceRepositoryReadOnly": True,
    "explicitEvidenceArtifactDirectoryOnly": True,
    "repositoryRefPromotion": False,
}
EXPECTED_PROTOCOL = {
    "version": "m2-real-corpus-performance-retest-v1",
    "gitOnlyBatches": 2,
    "pairedSamplesPerBatch": 30,
    "order": "alternate-current-vs-path-and-candidate-vs-serial-each-pair",
    "statistic": "median-of-paired-fractional-improvements",
    "bootstrapResamples": 10000,
    "bootstrapSeed": 20260925,
    "confidence": 0.95,
    "requiredMedianImprovementPerBatch": 0.1,
    "requiredBootstrapLowerBoundPerBatch": "greater-than-zero",
    "requiredComparisons": ["serial", "timed-path-overlap"],
    "fullProjectValidationPairs": 2,
    "requiredTreeChecks": "candidate-serial-path-equal-and-source-unchanged-in-every-pair",
    "unsafeAdmissionCount": 0,
}
EXPECTED_DEPENDENCIES = {
    "scripts/docker/t013/Dockerfile": "d96d3e097d01b98bb7cc40f5575cb0d1b7b23a4ae66a6882b41196b0284b12f5",
    "scripts/docker/t013/apt-packages.lock": "db23b2947328c4407d0d055c4ef9081e584b0662ec0102a8b2d5281457bd335c",
    "scripts/docker/t013/constraints-t013.txt": "b12b51229e18fa1ca35c7bd1404f2359debb1d877203c1e37bab685111accad5",
    "requirements-dev.txt": "24a8316f230a1f408b5c953bf0217968f7ccab452594e774a1771ae28df86448",
    "requirements-speckit.txt": "daa35d1e5551fba64cada1787b2646c283f9fb56ddc00b48f9b596b68134c392",
}
CODE_FILES = {
    "prototypeSha256": "agent_braid/git_integration_prototype.py",
    "gitProcessSha256": "agent_braid/git_process.py",
    "benchmarkScriptSha256": "scripts/benchmark_m2_parallel_preparation.py",
}


class RetestPreflightRejected(ValueError):
    """A frozen input or required read-only observation failed."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RetestPreflightRejected(reason)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repository: Path, *args: str) -> bytes:
    environment = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1",
                   "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(
        ["git", "-C", str(repository), "-c", "core.hooksPath=/dev/null", *args],
        env=environment, capture_output=True, check=False, timeout=20,
    )
    require(result.returncode == 0, "Git check failed: " + args[0])
    return result.stdout


def git_text(repository: Path, *args: str) -> str:
    return git(repository, *args).decode("utf-8", "strict").strip()


def frozen_files(repository: Path, root: Path = ROOT) -> tuple[dict, dict, dict]:
    """Load only the exact proposal and corpus selected at the reviewed commit."""
    for path, expected in ((INPUT_PATH, INPUT_SHA256), (PROPOSAL_PATH, PROPOSAL_SHA256)):
        current = (root / path).read_bytes()
        require(sha(current) == expected, "frozen proposal bytes changed: " + path)
        require(git(repository, "show", f"{PROPOSAL_COMMIT}:{path}") == current,
                "proposal is not the reviewed commit: " + path)
    proposal = json.loads((root / INPUT_PATH).read_bytes())
    manifest_path = f"{FEATURE}/m2-corpus-manifest.json"
    selection_path = f"{FEATURE}/m2-corpus-selection.json"
    for path, key in ((manifest_path, "manifestFileSha256"),
                      (selection_path, "selectionFileSha256")):
        require(sha((root / path).read_bytes()) == proposal[key],
                "frozen corpus bytes changed: " + path)
    manifest = json.loads((root / manifest_path).read_bytes())
    selection = json.loads((root / selection_path).read_bytes())
    require(selection["manifest"] == manifest, "selection and manifest disagree")
    canonical = json.dumps(selection, sort_keys=True, separators=(",", ":")).encode()
    require(sha(canonical) == proposal["canonicalSelectionSha256"],
            "canonical selection changed")
    return proposal, manifest, selection


def check_controls(proposal: dict) -> None:
    require(proposal["recordVersion"] == "agent-braid-m2-real-corpus-retest-input-proposal-1",
            "proposal version changed")
    require(proposal["status"] == "pending-founder-decision", "proposal status changed")
    require(proposal["repository"] == "jayanez/agent-braid"
            and proposal["targetRef"] == "refs/heads/develop"
            and proposal["validationProfile"] == "m2-real-read-only-v1",
            "repository or profile changed")
    require(proposal["resourceLimits"] == EXPECTED_LIMITS, "resource limits changed")
    require(proposal["measurementProtocol"] == EXPECTED_PROTOCOL,
            "measurement protocol changed")
    require(proposal["allowlistedCommand"] == "python -m unittest discover -s tests",
            "allowlisted command changed")
    require(proposal["containerImage"] == {
        "os": "linux", "architecture": "arm64", "id": IMAGE}, "image changed")
    require(proposal["dependencyFilesSha256"] == EXPECTED_DEPENDENCIES,
            "dependency set changed")
    require(proposal["executionAuthorization"] is False
            and proposal["projectValidationExecuted"] is False
            and proposal["m2Closure"] is False
            and proposal["externalHumanValidation"] == "pending",
            "proposal falsely claims authorization or validation")


def check_workstreams(proposal: dict, manifest: dict, selection: dict) -> None:
    require(manifest["baseCommit"] == proposal["baseCommit"]
            and manifest["repository"] == proposal["repository"]
            and manifest["targetRef"] == proposal["targetRef"],
            "manifest identity changed")
    workstreams = proposal["workstreams"]
    operations = manifest["operations"]
    require(len(workstreams) == len(operations) == 2, "workstream count changed")
    require(len({item["pullRequest"] for item in workstreams}) == 2,
            "duplicate workstream PR")
    require(len({item["branch"] for item in workstreams}) == 2,
            "duplicate workstream branch")
    require({(item["instanceId"], item["sourceCommit"], item["pullRequest"])
             for item in workstreams} ==
            {(item["instanceId"], item["sourceCommit"], item["workstreamUrl"])
             for item in operations}, "source commit or PR substituted")
    require({item["instanceId"]: item["branch"] for item in workstreams}
            == selection["branches"], "source branch substituted")
    require(all(item["dependencies"] == [] for item in workstreams + operations),
            "workstream dependencies changed")
    require(set(selection["footprints"]) == {item["instanceId"] for item in operations},
            "footprint inventory changed")


def expected_refs(proposal: dict) -> dict[str, str]:
    return {
        "refs/heads/develop": proposal["baseCommit"],
        **{"refs/heads/" + item["branch"]: item["sourceCommit"]
           for item in proposal["workstreams"]},
        "refs/heads/" + proposal["candidate"]["branch"]:
            proposal["candidate"]["codeCommit"],
        "refs/heads/work/m2-performance-retest-decision-20260925": PROPOSAL_COMMIT,
    }


def check_refs(proposal: dict, observed: dict[str, str]) -> None:
    require(observed == expected_refs(proposal), "remote ref moved or disappeared")


def check_footprints(selection: dict, observed_writes: dict[str, list[str]]) -> None:
    require(set(observed_writes) == set(selection["footprints"]),
            "tracked-write inventory incomplete")
    for identifier, footprint in selection["footprints"].items():
        require(footprint["footprintComplete"] is True
                and footprint["sharedResources"] == []
                and sorted(footprint["writes"]) == sorted(observed_writes[identifier]),
                "undeclared tracked write or incomplete footprint: " + identifier)


def check_code_hashes(proposal: dict, observed: dict[str, str]) -> None:
    require(observed == {key: proposal["candidate"][key] for key in CODE_FILES},
            "candidate code hash changed")


def check_dependency_hashes(proposal: dict, current: dict[str, str],
                            at_base: dict[str, str]) -> None:
    require(proposal["dependencyFilesSha256"] == EXPECTED_DEPENDENCIES
            and current == EXPECTED_DEPENDENCIES
            and at_base == EXPECTED_DEPENDENCIES, "dependency bytes changed")


def check_image(image: dict) -> None:
    require((image["Id"], image["Os"], image["Architecture"])
            == (IMAGE, "linux", "arm64"), "local pinned image changed")


def live_remote_refs(repository: Path, proposal: dict) -> dict[str, str]:
    refs = sorted(expected_refs(proposal))
    lines = git_text(repository, "ls-remote", "origin", *refs).splitlines()
    observed = {ref: oid for oid, ref in (line.split() for line in lines)}
    check_refs(proposal, observed)
    return observed


def live_pr(number: int) -> dict:
    result = subprocess.run(
        ["gh", "pr", "view", str(number), "--repo", "jayanez/agent-braid",
         "--json", "number,url,headRefOid,headRefName,baseRefOid,state"],
        capture_output=True, text=True, check=False, timeout=20,
    )
    require(result.returncode == 0, "PR metadata unavailable: " + str(number))
    return json.loads(result.stdout)


def check_prs(proposal: dict, observed: dict[int, dict]) -> None:
    entries = [(137, proposal["workstreams"][0], proposal["baseCommit"]),
               (138, proposal["workstreams"][1], proposal["baseCommit"]),
               (140, proposal["candidate"], PERFORMANCE_PR_BASE),
               (141, {"pullRequest": "https://github.com/jayanez/agent-braid/pull/141",
                      "branch": "work/m2-performance-retest-decision-20260925",
                      "sourceCommit": PROPOSAL_COMMIT},
                proposal["candidate"]["codeCommit"])]
    require(set(observed) == {137, 138, 140, 141}, "PR metadata incomplete")
    for number, item, base in entries:
        expected_head = item.get("sourceCommit", item.get("codeCommit"))
        pr = observed[number]
        require(pr == {"number": number, "url": item["pullRequest"],
                       "headRefOid": expected_head, "headRefName": item["branch"],
                       "baseRefOid": base, "state": "OPEN"},
                "PR identity or head changed: " + str(number))


def inspect_image() -> dict:
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE, "--format", "{{json .}}"],
        capture_output=True, text=True, check=False, timeout=20,
    )
    require(result.returncode == 0, "pinned image unavailable")
    return json.loads(result.stdout)


def negative_controls(proposal: dict, manifest: dict, selection: dict,
                      refs: dict[str, str], writes: dict[str, list[str]],
                      code_hashes: dict[str, str]) -> list[str]:
    """Exercise six rejection paths in memory, without changing the repository."""
    cases: list[tuple[str, Callable[[], None]]] = []
    moved = dict(refs)
    moved["refs/heads/develop"] = "f" * 40
    cases.append(("moved-base", lambda: check_refs(proposal, moved)))
    substituted = deepcopy(manifest)
    substituted["operations"][0]["sourceCommit"] = "f" * 40
    cases.append(("substituted-commit",
                  lambda: check_workstreams(proposal, substituted, selection)))
    duplicate = deepcopy(proposal)
    duplicate["workstreams"][1]["pullRequest"] = duplicate["workstreams"][0]["pullRequest"]
    cases.append(("duplicate-pr", lambda: check_workstreams(duplicate, manifest, selection)))
    extra = deepcopy(writes)
    extra[next(iter(extra))].append("unexpected-tracked-write.txt")
    cases.append(("undeclared-write", lambda: check_footprints(selection, extra)))
    altered = dict(code_hashes)
    altered["prototypeSha256"] = "f" * 64
    cases.append(("changed-code-hash", lambda: check_code_hashes(proposal, altered)))
    relaxed = deepcopy(proposal)
    relaxed["resourceLimits"]["cpusPerContainer"] += 1
    cases.append(("breached-resource-limit", lambda: check_controls(relaxed)))
    passed = []
    for name, check in cases:
        try:
            check()
        except RetestPreflightRejected:
            passed.append(name)
        else:
            raise RetestPreflightRejected("negative control was admitted: " + name)
    return passed


def validate_proposal(
    repository: Path, *, root: Path = ROOT,
    remote_reader: Callable[[Path, dict], dict[str, str]] = live_remote_refs,
    pr_reader: Callable[[int], dict] = live_pr,
    image_reader: Callable[[], dict] = inspect_image,
    expected_public_root: str = PUBLIC_ROOT,
) -> dict:
    """Check frozen inputs and live identity; return a non-authorizing record."""
    require((repository / ".git").is_dir(), "standalone clone required")
    require(git_text(repository, "status", "--porcelain=v1", "--untracked-files=all") == "",
            "source repository is not clean")
    source_head_before = git_text(repository, "rev-parse", "HEAD")
    proposal, manifest, selection = frozen_files(repository, root)
    check_controls(proposal)
    check_workstreams(proposal, manifest, selection)
    require(_validate_manifest(manifest, repository, expected_public_root)["status"]
            == "preflight-valid", "manifest preflight failed")
    require(git_text(repository, "rev-parse", "refs/remotes/origin/develop")
            == proposal["baseCommit"], "local origin/develop moved")
    require(git_text(repository, "rev-parse", "refs/heads/develop")
            == proposal["baseCommit"], "local develop moved")
    for item in proposal["workstreams"] + [proposal["candidate"]]:
        commit = item.get("sourceCommit", item.get("codeCommit"))
        require(git_text(repository, "rev-parse", "refs/remotes/origin/" + item["branch"])
                == commit, "local source or candidate branch moved: " + item["branch"])
    require(git_text(repository, "rev-parse",
                     "refs/remotes/origin/work/m2-performance-retest-decision-20260925")
            == PROPOSAL_COMMIT, "local proposal branch moved")
    refs_before = remote_reader(repository, proposal)
    check_refs(proposal, refs_before)
    prs = {number: pr_reader(number) for number in (137, 138, 140, 141)}
    check_prs(proposal, prs)
    writes = {}
    for item in manifest["operations"]:
        raw = git(repository, "diff", "--name-only", "-z", proposal["baseCommit"],
                  item["sourceCommit"], "--")
        writes[item["instanceId"]] = [os.fsdecode(path) for path in raw.split(b"\0") if path]
    check_footprints(selection, writes)
    code_hashes = {}
    for key, path in CODE_FILES.items():
        code_hashes[key] = sha((root / path).read_bytes())
        require(sha(git(repository, "show", proposal["candidate"]["codeCommit"] + ":" + path))
                == code_hashes[key], "candidate commit code differs: " + path)
    check_code_hashes(proposal, code_hashes)
    baseline = proposal["pathOverlapBaseline"]
    require(baseline["prototypeCommit"] == proposal["priorT003"]["reviewedCommit"]
            and baseline["scheduler"] == "conservative-tracked-write-overlap-v1"
            and baseline["gitProcessPollSeconds"] == 0.01
            and baseline["gitProcessHelperSha256"] == proposal["candidate"]["gitProcessSha256"]
            and sha(git(repository, "show", baseline["prototypeCommit"]
                       + ":agent_braid/git_integration_prototype.py"))
            == baseline["prototypeSha256"], "timed path baseline changed")
    prior = proposal["priorT003"]
    require(prior["outcome"] == "no-performance-improvement-on-reviewed-corpus"
            and sha((root / f"{FEATURE}/t006-founder-review.json").read_bytes())
            == prior["founderReviewSha256"]
            and sha((root / f"{FEATURE}/evidence/reproduction.json").read_bytes())
            == prior["reproductionSha256"], "prior negative T003 evidence changed")
    current_dependencies = {path: sha((root / path).read_bytes())
                            for path in EXPECTED_DEPENDENCIES}
    base_dependencies = {
        path: sha(git(repository, "show", proposal["baseCommit"] + ":" + path))
        for path in EXPECTED_DEPENDENCIES
    }
    check_dependency_hashes(proposal, current_dependencies, base_dependencies)
    check_image(image_reader())
    controls = negative_controls(proposal, manifest, selection, refs_before,
                                 writes, code_hashes)
    refs_after = remote_reader(repository, proposal)
    check_refs(proposal, refs_after)
    require(refs_after == refs_before, "remote refs moved during preflight")
    source_head_after = git_text(repository, "rev-parse", "HEAD")
    require(source_head_after == source_head_before,
            "source HEAD changed during preflight")
    require(git_text(repository, "status", "--porcelain=v1", "--untracked-files=all") == "",
            "source repository changed during preflight")
    return {
        "recordVersion": "agent-braid-m2-retest-read-only-preflight-1",
        "status": "proposal-preflight-valid",
        "proposalCommit": PROPOSAL_COMMIT,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "inputProposalSha256": INPUT_SHA256,
        "sourceHead": source_head_after,
        "baseCommit": proposal["baseCommit"],
        "candidateCodeCommit": proposal["candidate"]["codeCommit"],
        "remoteRefsBefore": refs_before,
        "remoteRefsAfter": refs_after,
        "negativeControlsRejected": controls,
        "containerImage": proposal["containerImage"],
        "executionAuthorization": False,
        "projectValidationExecuted": False,
        "externalHumanValidation": "pending",
        "m2Closure": False,
        "limits": "Read-only identity and byte checks; no Git preparation or project command was run.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(validate_proposal(args.repository.resolve()), sort_keys=True, indent=2))
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"M2 retest preflight rejected: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
