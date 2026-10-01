# SPDX-License-Identifier: AGPL-3.0-only
"""Operate the private M3.5 authoring sidecar on one local host.

The command is a controlled interface, not a security boundary against a user
who can read the private journal directly. Never put its state in a Git tree.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from agent_braid.m35_source_window import (
    audit_window, canonical, close_session, create_window, final_seal_payload, mark_external_observation,
    open_session, propose, reveal, seal_payload, utc, validate_window, view_base,
)


AUDIT_REPO = "jayanez/agent-braid-m35-audit"


def _json_from_gh(*arguments: str) -> dict:
    result = subprocess.run(["gh", *arguments], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def verify_registration(manifest: dict, repository: str = AUDIT_REPO) -> None:
    """Require a real runner result and the exact registered window artifact."""
    run_id = manifest["registrationRunId"]
    run = _json_from_gh("api", f"repos/{repository}/actions/runs/{run_id}")
    if (run.get("status") != "completed" or run.get("conclusion") != "success"
            or run.get("event") != "workflow_dispatch"
            or not str(run.get("path", "")).split("@", 1)[0].endswith(".github/workflows/m35-seal.yml")
            or run.get("head_branch") != "main"
            or run.get("head_repository", {}).get("full_name") != repository):
        raise ValueError("registration workflow did not complete successfully")
    jobs = _json_from_gh("api", f"repos/{repository}/actions/runs/{run_id}/jobs")
    if not any(job.get("conclusion") == "success" and job.get("runner_name")
               and job.get("steps") for job in jobs.get("jobs", [])):
        raise ValueError("registration has no executed runner and steps")
    if utc(manifest["startUtc"]) < utc(run["updated_at"].replace("+00:00", "Z")) + timedelta(hours=24):
        raise ValueError("window starts less than 24 hours after registration")
    with TemporaryDirectory() as directory:
        subprocess.run(["gh", "run", "download", str(run_id), "--repo", repository,
                        "--name", "m35-seal", "--dir", directory],
                       check=True, capture_output=True, text=True)
        registered = json.loads((Path(directory) / "seal.json").read_text(encoding="utf-8"))
    expected = {"format": "m35-seal-v1", "mode": "register", "windowId": manifest["windowId"],
                "familyId": manifest["familyId"], "startUtc": manifest["startUtc"],
                "endUtc": manifest["endUtc"], "protocolCommit": manifest["protocolCommit"]}
    if registered != expected:
        raise ValueError("remote registration differs from local source window")


def verify_permission_record(path: Path, manifest: dict) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))
    required = {"format", "windowId", "sourceOwner", "workflow", "permissionGranted",
                "participantRightsReviewed", "privacyApproved", "labExportReviewed",
                "approvedAtUtc"}
    if (type(record) is not dict or set(record) != required
            or record["format"] != "m35-source-permission-v1"
            or record["windowId"] != manifest["windowId"]
            or any(record[key] is not True for key in (
                "permissionGranted", "participantRightsReviewed", "privacyApproved", "labExportReviewed"))
            or any(type(record[key]) is not str or not record[key] for key in (
                "sourceOwner", "workflow"))
            or utc(record["approvedAtUtc"]) >= utc(manifest["startUtc"])
            or utc(record["approvedAtUtc"]) > datetime.now(timezone.utc)):
        raise ValueError("source permission and privacy record is incomplete")


def _outside_git(path: Path) -> None:
    parent = path.parent.resolve()
    while not parent.exists():
        parent = parent.parent
    result = subprocess.run(["git", "-C", str(parent), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, check=False)
    if result.returncode == 0:
        raise ValueError("private capture directory must be outside every Git worktree")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="private local capture directory outside Git")
    commands = parser.add_subparsers(dest="command", required=True)
    registration = commands.add_parser("registration")
    registration.add_argument("manifest", type=Path)
    registration.add_argument("--permission-record", type=Path, required=True)
    init = commands.add_parser("init")
    init.add_argument("manifest", type=Path)
    init.add_argument("--permission-record", type=Path)
    init.add_argument("--registration-run-id", type=int)
    opened = commands.add_parser("open")
    opened.add_argument("session_id")
    opened.add_argument("session", type=Path, help="private JSON with participants, base, contextSha, sourceRef")
    viewed = commands.add_parser("view")
    viewed.add_argument("session_id")
    viewed.add_argument("actor_id")
    proposed = commands.add_parser("propose")
    proposed.add_argument("session_id")
    proposed.add_argument("actor_id")
    proposed.add_argument("proposal", type=Path, help="private JSON with operation and sourceRef")
    observed = commands.add_parser("external-observation")
    observed.add_argument("session_id")
    observed.add_argument("actor_id")
    revealed = commands.add_parser("reveal")
    revealed.add_argument("session_id")
    revealed.add_argument("actor_id")
    closed = commands.add_parser("close")
    closed.add_argument("session_id")
    closed.add_argument("outcome", choices=("accepted", "rejected", "cancelled", "unresolved"))
    commands.add_parser("audit")
    seal = commands.add_parser("seal")
    seal.add_argument("day_index", type=int)
    seal.add_argument("--previous-run-id", required=True, type=int)
    final_seal = commands.add_parser("final-seal")
    final_seal.add_argument("--previous-run-id", required=True, type=int)
    args = parser.parse_args()
    directory = args.directory
    if args.command == "registration":
        _outside_git(args.permission_record)
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if type(manifest) is not dict or manifest.get("sourceKind") != "prospective" or manifest.get("registrationRunId") is not None:
            raise ValueError("registration requires a prospective manifest with an unbound run")
        validate_window({**manifest, "registrationRunId": 1})
        verify_permission_record(args.permission_record, manifest)
        result = {"format": "m35-seal-v1", "mode": "register", "windowId": manifest["windowId"],
                  "familyId": manifest["familyId"], "startUtc": manifest["startUtc"],
                  "endUtc": manifest["endUtc"], "protocolCommit": manifest["protocolCommit"]}
    elif args.command == "init":
        _outside_git(directory)
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.registration_run_id is not None:
            if (type(manifest) is not dict or manifest.get("sourceKind") != "prospective"
                    or manifest.get("registrationRunId") is not None or args.registration_run_id <= 0):
                raise ValueError("registration run can bind only an unbound prospective window")
            manifest = {**manifest, "registrationRunId": args.registration_run_id}
        validate_window(manifest)
        real = manifest["sourceKind"] == "prospective"
        if real:
            if args.permission_record is None:
                raise ValueError("prospective capture requires a local permission record")
            _outside_git(args.permission_record)
            verify_permission_record(args.permission_record, manifest)
            verify_registration(manifest)
        create_window(directory, manifest, registration_verified=real, permission_reviewed=real)
        result = {"created": True, "sourceKind": manifest["sourceKind"], "windowId": manifest["windowId"]}
    elif args.command == "open":
        data = json.loads(args.session.read_text(encoding="utf-8"))
        if type(data) is not dict or set(data) != {"participants", "base", "contextSha", "sourceRef"}:
            raise ValueError("session input shape is invalid")
        record = open_session(directory, args.session_id, **{
            "participants": data["participants"], "base": data["base"],
            "context_sha": data["contextSha"], "source_ref": data["sourceRef"]})
        result = {"sessionId": args.session_id, "eventId": record["eventId"]}
    elif args.command == "view":
        result = view_base(directory, args.session_id, args.actor_id)
    elif args.command == "propose":
        data = json.loads(args.proposal.read_text(encoding="utf-8"))
        if type(data) is not dict or set(data) != {"operation", "sourceRef"}:
            raise ValueError("proposal input shape is invalid")
        record = propose(directory, args.session_id, args.actor_id, data["operation"], data["sourceRef"])
        result = {"eventId": record["eventId"], "acceptedForAudit": True}
    elif args.command == "external-observation":
        record = mark_external_observation(directory, args.session_id, args.actor_id)
        result = {"eventId": record["eventId"]}
    elif args.command == "reveal":
        result = reveal(directory, args.session_id, args.actor_id)
    elif args.command == "close":
        record = close_session(directory, args.session_id, args.outcome)
        result = {"eventId": record["eventId"]}
    elif args.command == "audit":
        result = audit_window(directory)
    elif args.command == "seal":
        result = seal_payload(directory, args.day_index)
        if args.previous_run_id <= 0:
            raise ValueError("previous run ID must be positive")
        result["previousRunId"] = args.previous_run_id
        # The remote validator checks the predecessor artifact and its real runner.
    else:
        result = final_seal_payload(directory)
        if args.previous_run_id <= 0:
            raise ValueError("previous run ID must be positive")
        result["previousRunId"] = args.previous_run_id
    print(canonical(result).decode("utf-8"))


if __name__ == "__main__":
    main()
