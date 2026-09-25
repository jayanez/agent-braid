#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run only the founder-approved, bounded ADR 0015 real-workload experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.git_integration_prototype import run_prototype
from scripts.validate_real_workload_manifest import validate_manifest


FEATURE = ROOT / "specs/013-m2-real-workload"
IMAGE = "sha256:edddb1cbcbccb0e1af6505f9ff9938905da6f79303c97d1d12092ef61508f005"
COMMAND = ["python", "-m", "unittest", "discover", "-s", "tests"]
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
BRANCHES = {
    "m2-observation-normalizer": "014-m2-observation-normalizer",
    "m2-counterexample-reducer": "015-m2-counterexample-reducer",
}

# This script is harness code, not repository code. It runs in each private
# container and invokes the sole allowed repository command exactly once.
LANE_CODE = r"""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import time

expected = sys.argv[1]
root = Path("/tmp/repository")
root.mkdir()
shutil.copytree("/source-git", root / ".git")
with tarfile.open("/tree.tar") as archive:
    members = archive.getmembers()
    if any(member.issym() or member.islnk() or member.name.startswith("/")
           or ".." in Path(member.name).parts for member in members):
        raise RuntimeError("unsafe tree archive")
    archive.extractall(root, filter="data")
def git(*args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True, timeout=30).stdout.strip()
git("add", "-A")
observed = git("write-tree")
if observed != expected:
    print(json.dumps({"status": "inconclusive", "reason": "tree-id-mismatch",
                      "expectedTree": expected, "observedTree": observed}))
    sys.exit(0)
baseline_status = git("status", "--porcelain=v1", "--untracked-files=all")
output = Path("/tmp/unit-test-output")
started = time.monotonic()
before = resource.getrusage(resource.RUSAGE_CHILDREN)
timed_out = False
with output.open("wb") as stream:
    def limit_output():
        resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    process = subprocess.Popen(
        ["python", "-m", "unittest", "discover", "-s", "tests"],
        cwd=root, stdout=stream, stderr=subprocess.STDOUT,
        start_new_session=True, preexec_fn=limit_output)
    try:
        exit_code = process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        import signal
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        exit_code = process.returncode
        timed_out = True
after = resource.getrusage(resource.RUSAGE_CHILDREN)
elapsed = time.monotonic() - started
captured = output.read_bytes()
truncated = len(captured) >= 8 * 1024 * 1024
dirty = git("status", "--porcelain=v1", "--untracked-files=all") != baseline_status
match = re.search(rb"Ran (\d+) tests? in ", captured)
test_count = int(match.group(1)) if match else None
def cgroup_number(path):
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None
def temporary_bytes(path):
    total = 0
    for base, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(base) / name).stat().st_size
            except OSError:
                pass
    return total
reason = ("timeout" if timed_out else "output-truncated" if truncated else
          "test-failed" if exit_code else "unexpected-worktree-write" if dirty else
          "missing-test-count" if test_count is None else None)
print(json.dumps({
    "status": "passed" if reason is None else "inconclusive",
    "reason": reason, "expectedTree": expected, "observedTree": observed,
    "command": "python -m unittest discover -s tests",
    "exitCode": exit_code, "testCount": test_count,
    "elapsedSeconds": round(elapsed, 6),
    "childUserCpuSeconds": round(after.ru_utime - before.ru_utime, 6),
    "childSystemCpuSeconds": round(after.ru_stime - before.ru_stime, 6),
    "peakChildRssBytes": after.ru_maxrss * 1024,
    "cgroupPeakMemoryBytes": cgroup_number("/sys/fs/cgroup/memory.peak"),
    "temporaryDataBytes": temporary_bytes("/tmp"),
    "capturedOutputBytes": len(captured),
    "capturedOutputSha256": hashlib.sha256(captured).hexdigest(),
    "outputTruncated": truncated,
    "unexpectedWorktreeWrite": bool(dirty),
    "outputTail": captured[-2048:].decode("utf-8", "replace") if reason else None,
}, sort_keys=True))
"""


class ExperimentRejected(ValueError):
    """An approved input changed or a required isolation condition is absent."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExperimentRejected(reason)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repository: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repository), *args], capture_output=True,
                            text=True, timeout=15, check=True,
                            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1",
                                 "GIT_CONFIG_GLOBAL": os.devnull,
                                 "GIT_NO_REPLACE_OBJECTS": "1",
                                 "GIT_TERMINAL_PROMPT": "0"})
    return result.stdout.strip()


def live_remote_refs(repository: Path, selection: dict) -> dict[str, str]:
    refs = ["refs/heads/develop"] + [
        "refs/heads/" + selection["branches"][item["instanceId"]]
        for item in selection["manifest"]["operations"]
    ]
    output = git(repository, "ls-remote", "origin", *refs)
    found = dict(reversed(line.split()) for line in output.splitlines())
    require(set(found) == set(refs), "live remote refs are incomplete")
    return found


def verify_inputs(repository: Path) -> tuple[dict, dict, dict]:
    decision = json.loads((FEATURE / "t003-founder-decision.json").read_text())
    require(decision["decision"] == "accepted-exact-experiment",
            "T003 founder acceptance is absent")
    require(sha(ROOT / decision["reviewedProposalPath"])
            == decision["reviewedProposalSha256"],
            "reviewed T003 proposal bytes changed")
    approved_path = ROOT / decision["approvedInputsPath"]
    require(sha(approved_path) == decision["reviewedInputFileSha256"],
            "approved input proposal changed")
    approved = json.loads(approved_path.read_text())
    require(approved["containerImage"] == {
        "os": "linux", "architecture": "arm64", "id": IMAGE},
        "image approval differs from fixed runner")
    require(approved["allowlistedCommand"] == " ".join(COMMAND),
            "approved command differs from fixed runner")
    selection_path = FEATURE / "m2-corpus-selection.json"
    manifest_path = FEATURE / "m2-corpus-manifest.json"
    require(sha(selection_path) == approved["selectionFileSha256"],
            "approved selection bytes changed")
    require(sha(manifest_path) == approved["manifestFileSha256"],
            "approved manifest bytes changed")
    selection = json.loads(selection_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    require(selection["manifest"] == manifest, "selection and manifest disagree")
    canonical = hashlib.sha256(json.dumps(selection, sort_keys=True,
                               separators=(",", ":")).encode()).hexdigest()
    require(canonical == approved["canonicalSelectionSha256"],
            "canonical selection changed")
    require(manifest["baseCommit"] == approved["baseCommit"]
            and manifest["repository"] == approved["repository"]
            and manifest["targetRef"] == approved["targetRef"],
            "approved repository or base differs")
    require(BRANCHES == selection["branches"], "approved source branches changed")
    require({(item["instanceId"], item["workstreamUrl"], item["sourceCommit"])
             for item in manifest["operations"]} ==
            {(item["instanceId"], item["pullRequest"], item["sourceCommit"])
             for item in approved["workstreams"]}, "approved workstreams changed")
    require(all(not item["dependencies"] for item in manifest["operations"]),
            "approved workstreams must be independent")
    for path, expected in approved["dependencyFilesSha256"].items():
        require(sha(ROOT / path) == expected, "dependency file changed: " + path)
        actual_at_base = subprocess.run(
            ["git", "-C", str(repository), "show", manifest["baseCommit"] + ":" + path],
            capture_output=True, check=True, timeout=15).stdout
        require(hashlib.sha256(actual_at_base).hexdigest() == expected,
                "base dependency bytes differ: " + path)
    require(validate_manifest(manifest, repository)["status"] == "preflight-valid",
            "canonical manifest preflight failed")
    for item in manifest["operations"]:
        identifier = item["instanceId"]
        declared = selection["footprints"][identifier]
        changed = git(repository, "diff", "--name-only", manifest["baseCommit"],
                      item["sourceCommit"], "--").splitlines()
        require(sorted(changed) == sorted(declared["writes"]),
                "undeclared tracked write: " + identifier)
        require(declared["footprintComplete"] is True,
                "static fixed-patch footprint incomplete: " + identifier)
        require(git(repository, "rev-parse",
                    "refs/remotes/origin/" + BRANCHES[identifier]) == item["sourceCommit"],
                "local source branch moved: " + identifier)
    require(git(repository, "rev-parse", "refs/remotes/origin/develop")
            == manifest["baseCommit"], "local origin/develop moved")
    remote = live_remote_refs(repository, selection)
    require(remote["refs/heads/develop"] == manifest["baseCommit"],
            "live origin/develop moved")
    for item in manifest["operations"]:
        require(remote["refs/heads/" + BRANCHES[item["instanceId"]]]
                == item["sourceCommit"], "live source branch moved: " + item["instanceId"])
    inspect = subprocess.run(
        ["docker", "image", "inspect", IMAGE, "--format", "{{json .}}"],
        capture_output=True, text=True, timeout=15, check=True)
    image = json.loads(inspect.stdout)
    require((image["Id"], image["Os"], image["Architecture"])
            == (IMAGE, "linux", "arm64"), "local Docker image differs")
    require((repository / ".git").is_dir(), "experiment requires a clean standalone clone")
    return approved, selection, remote


def prototype_request(repository: Path, selection: dict) -> dict:
    manifest = selection["manifest"]
    return {
        "gitIntegrationPrototypeRequestVersion": "0.1.0-alpha",
        "repository": str(repository),
        "baseRevision": manifest["baseCommit"],
        "targetRef": manifest["targetRef"],
        "operations": [
            {"instanceId": item["instanceId"], "attemptId": "t003-" + item["instanceId"],
             "source": {"kind": "commit", "revision": item["sourceCommit"]},
             "dependencies": item["dependencies"], **selection["footprints"][item["instanceId"]]}
            for item in manifest["operations"]
        ],
    }


def archive_tree(scratch: Path, tree: str, output: Path) -> None:
    with output.open("wb") as stream:
        result = subprocess.run(
            ["git", "-C", str(scratch), "-c", "core.hooksPath=/dev/null",
             "archive", "--format=tar", tree],
            stdout=stream, stderr=subprocess.PIPE, timeout=30, check=False,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1",
                 "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1"})
    require(result.returncode == 0, "private tree archive failed")
    require(0 < output.stat().st_size <= MAX_ARCHIVE_BYTES,
            "private tree archive exceeded bound")


def git_phase(repository: Path, directory: Path) -> dict:
    selection = json.loads((FEATURE / "m2-corpus-selection.json").read_text())
    request = prototype_request(repository, selection)
    reports = []
    archives = {}
    for repeat in range(2):
        destinations = {lane: directory / f"{lane}-{repeat}.tar"
                        for lane in ("candidate", "serial")}
        def consume(scratch: Path, candidate: str, serial: str) -> None:
            archive_tree(scratch, candidate, destinations["candidate"])
            archive_tree(scratch, serial, destinations["serial"])
        report = run_prototype(request, tree_consumer=consume)
        reports.append(report)
        if report["status"] != "completed" or report["comparison"]["status"] != "match":
            break
        archives[str(repeat)] = {
            lane: {"sha256": sha(path), "bytes": path.stat().st_size,
                   "tree": report["candidateIntegration" if lane == "candidate"
                                  else "serialReference"]["finalTree"]}
            for lane, path in destinations.items()
        }
    return {"gitReports": reports, "privateTreeArchives": archives}


def run_git_phase_docker(repository: Path, directory: Path) -> dict:
    args = [
        "docker", "run", "--rm", "--network=none", "--read-only",
        "--memory=2g", "--memory-swap=2g", "--cpus=2", "--pids-limit=512",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--tmpfs=/tmp:rw,nosuid,nodev,size=512m,mode=1777",
        "--mount", f"type=bind,src={repository},dst={repository},readonly",
        "--mount", f"type=bind,src={directory},dst=/artifacts",
        "--workdir", str(repository),
        "--env=HOME=/tmp/home", "--env=TMPDIR=/tmp",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        "--env=GIT_CONFIG_NOSYSTEM=1", "--env=GIT_CONFIG_GLOBAL=/dev/null",
        "--env=GIT_NO_REPLACE_OBJECTS=1", "--env=GIT_TERMINAL_PROMPT=0",
        "--env=GIT_CONFIG_COUNT=1", "--env=GIT_CONFIG_KEY_0=core.hooksPath",
        "--env=GIT_CONFIG_VALUE_0=/dev/null",
        IMAGE, "python", "scripts/run_m2_real_workload.py",
        "--git-phase", "--repository", str(repository),
        "--output", "/artifacts/git-phase.json",
    ]
    process = subprocess.run(args, capture_output=True, timeout=120, check=False)
    require(process.returncode == 0, "pinned Git preparation failed: "
            + process.stderr[-2048:].decode("utf-8", "replace"))
    return json.loads((directory / "git-phase.json").read_text())


def run_lane(repository: Path, archive: Path, tree: str) -> dict:
    container_name = "agent-braid-m2-" + uuid.uuid4().hex
    args = [
        "docker", "run", "--rm", "--name", container_name,
        "--network=none", "--read-only",
        "--memory=2g", "--memory-swap=2g", "--cpus=2", "--pids-limit=512",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--user=65534:65534", "--tmpfs=/tmp:rw,nosuid,nodev,size=512m,mode=1777",
        "--mount", f"type=bind,src={archive},dst=/tree.tar,readonly",
        "--mount", f"type=bind,src={repository / '.git'},dst=/source-git,readonly",
        "--workdir=/tmp",
        "--env=HOME=/tmp/home", "--env=TMPDIR=/tmp",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        "--env=PYTHONWARNINGS=error::ResourceWarning",
        "--env=GIT_CONFIG_NOSYSTEM=1", "--env=GIT_CONFIG_GLOBAL=/dev/null",
        "--env=GIT_NO_REPLACE_OBJECTS=1", "--env=GIT_TERMINAL_PROMPT=0",
        "--env=GIT_CONFIG_COUNT=1", "--env=GIT_CONFIG_KEY_0=core.hooksPath",
        "--env=GIT_CONFIG_VALUE_0=/dev/null",
        IMAGE, "python", "-c", LANE_CODE, tree,
    ]
    started = time.monotonic()
    try:
        process = subprocess.run(args, capture_output=True, timeout=180, check=False)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", container_name], capture_output=True,
                       timeout=15, check=False)
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True,
                       timeout=15, check=False)
        return {"status": "inconclusive", "reason": "container-timeout"}
    if process.returncode or len(process.stdout) > MAX_OUTPUT_BYTES:
        return {"status": "inconclusive", "reason": "container-failed-or-output-limit",
                "containerExitCode": process.returncode,
                "stderrTail": process.stderr[-2048:].decode("utf-8", "replace")}
    try:
        result = json.loads(process.stdout)
    except (UnicodeError, json.JSONDecodeError):
        return {"status": "inconclusive", "reason": "invalid-container-result"}
    result["containerWallSeconds"] = round(time.monotonic() - started, 6)
    result["containerExitCode"] = process.returncode
    return result


def classify(git_reports: list[dict], lanes: dict[str, list[dict]],
             remote_still_exact: bool) -> tuple[str, str | None]:
    if not remote_still_exact:
        return "rejected", "live-remote-ref-moved"
    if len(git_reports) != 2 or any(
        item["status"] != "completed"
        or item["comparison"]["status"] != "match"
        or item["unsafeAdmissionCount"] != 0
        or not item["sourceTargetRefMatchesPinnedBaseAtFinalCheck"]
        for item in git_reports
    ):
        return "inconclusive", "git-preparation-or-comparison"
    candidate = git_reports[0]["candidateIntegration"]["finalTree"]
    serial = git_reports[0]["serialReference"]["finalTree"]
    if candidate != serial or any(
        item["candidateIntegration"]["finalTree"] != candidate
        or item["serialReference"]["finalTree"] != serial
        for item in git_reports
    ):
        return "inconclusive", "nonrepeatable-git-tree"
    if set(lanes) != {"candidate", "serial"} or any(len(v) != 2 for v in lanes.values()):
        return "inconclusive", "missing-test-lane"
    results = [item for pair in lanes.values() for item in pair]
    if any(item.get("status") != "passed" for item in results):
        return "inconclusive", "test-lane-failed-or-incomplete"
    if any(item.get("observedTree") != candidate for item in results):
        return "inconclusive", "test-tree-mismatch"
    if len({item.get("testCount") for item in results}) != 1:
        return "inconclusive", "nonrepeatable-test-count"
    return "completed", None


def run(repository: Path) -> dict:
    approved, selection, remote_before = verify_inputs(repository)
    lanes: dict[str, list[dict]] = {}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="agent-braid-m2-t003-") as directory:
        temporary = Path(directory)
        phase = run_git_phase_docker(repository, temporary)
        reports = phase["gitReports"]
        archives = phase["privateTreeArchives"]
        remote_after_git = live_remote_refs(repository, selection)
        if len(reports) == 2 and all(item["status"] == "completed" for item in reports):
            for lane in ("candidate", "serial"):
                tree = reports[0]["candidateIntegration" if lane == "candidate"
                                  else "serialReference"]["finalTree"]
                lanes[lane] = [run_lane(repository, temporary / f"{lane}-{repeat}.tar", tree)
                               for repeat in range(2)]
        remote_final = live_remote_refs(repository, selection)
    status, reason = classify(reports, lanes, remote_before == remote_after_git == remote_final)
    first = reports[0] if reports else {}
    writes = [set(selection["footprints"][item["instanceId"]]["writes"])
              for item in selection["manifest"]["operations"]]
    path_waves = 1 if not (writes[0] & writes[1]) else 2
    return {
        "experimentVersion": "agent-braid-m2-t003-v1",
        "status": status, "reason": reason,
        "approvedInputsSha256": sha(FEATURE / "m2-t003-inputs.json"),
        "decisionSha256": sha(FEATURE / "t003-founder-decision.json"),
        "selectionFileSha256": sha(FEATURE / "m2-corpus-selection.json"),
        "manifestFileSha256": sha(FEATURE / "m2-corpus-manifest.json"),
        "baseCommit": approved["baseCommit"],
        "workstreams": approved["workstreams"],
        "image": IMAGE, "command": " ".join(COMMAND),
        "dependencyFilesSha256": approved["dependencyFilesSha256"],
        "resourceLimits": {"cpus": 2, "memoryBytes": 2 * 1024**3, "pids": 512,
                           "secondsPerLane": 180, "capturedOutputBytesPerLane": MAX_OUTPUT_BYTES,
                           "network": "none", "hostWrites": False},
        "remoteRefsBefore": remote_before, "remoteRefsAfterGit": remote_after_git,
        "remoteRefsFinal": remote_final,
        "gitReports": reports, "privateTreeArchives": archives, "testLanes": lanes,
        "baselines": {
            "serialWaveCount": len(first.get("operationOrder", [])),
            "pathOverlapWaveCount": path_waves,
            "candidateWaveCount": len(first.get("candidateWaves", [])),
            "candidateGitWallNanoseconds": first.get("metrics", {}).get(
                "candidateTotalWallNanoseconds"),
            "serialGitWallNanoseconds": first.get("metrics", {}).get(
                "serialTotalWallNanoseconds"),
        },
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "footprintScope": selection["footprintScope"],
        "footprintsDynamicallyObserved": False,
        "negativeControls": {
            "selection": ["moved-base", "substituted-source", "duplicate-pr",
                          "undeclared-tracked-write"],
            "stage": ["missing-lane", "failed-test", "tree-mismatch",
                      "nonrepeatable-tree", "remote-ref-moved"],
        },
        "executionAuthorization": False, "promotionPerformed": False,
        "externalHumanValidation": "pending", "m2Closure": False,
        "limits": [
            "Finite static tracked-path and unit-test observation only.",
            "No live agents, dynamic external-effect discovery or runtime admission.",
            "Container test output digest and bounded tail retained; full output is ephemeral.",
            "Source ref checks are snapshots and cannot detect transient move-and-restore.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--git-phase", action="store_true",
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    repository = args.repository.resolve()
    if args.git_phase:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(git_phase(repository, args.output.parent),
                                          sort_keys=True, indent=2) + "\n")
        return 0
    try:
        report = run(repository)
    except (ExperimentRejected, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, OSError, KeyError, ValueError) as exc:
        report = {"experimentVersion": "agent-braid-m2-t003-v1",
                  "status": "rejected", "reason": str(exc),
                  "executionAuthorization": False, "promotionPerformed": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "reason": report.get("reason"),
                      "output": str(args.output)}, sort_keys=True))
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
