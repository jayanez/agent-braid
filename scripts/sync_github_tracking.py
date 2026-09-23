#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Audit and explicitly reconcile Spec Kit IDs with GitHub tracking issues.

The repository records are authoritative. This script deliberately does not
infer founder approval, delete issues, or mutate the private Project directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docs/development/github-tracking.json"
TASK_LINE = re.compile(r"^- \[([ x])\] (T\d{3})(?: \(([^)]+)\))?: (.*)$")
MARKER = re.compile(r"<!-- agent-braid-(?:spec|task)-id: ([^ ]+) -->")


def source_inventory(root: Path = ROOT, config_path: Path = CONFIG) -> tuple[dict, list[dict]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    folders = sorted(path for path in (root / "specs").glob("[0-9]*") if (path / "spec.md").is_file())
    configured = set(config["specs"])
    actual = {path.name for path in folders}
    if configured != actual:
        raise ValueError(f"spec mapping mismatch: missing={sorted(actual-configured)}, stale={sorted(configured-actual)}")
    if any(item["milestone"] not in config["milestones"] for item in config["specs"].values()):
        raise ValueError("a spec names an undeclared milestone")
    if not set(config["closed_milestones"]) <= set(config["milestones"]):
        raise ValueError("a closed milestone is undeclared")
    base = f"https://github.com/{config['repository']}/blob/develop/"
    desired: list[dict] = []
    task_keys: set[str] = set()
    for folder in folders:
        spec_id = f"SPEC-{folder.name[:3]}"
        if not re.fullmatch(r"SPEC-\d{3}", spec_id):
            raise ValueError(f"invalid spec directory: {folder.name}")
        spec_text = (folder / "spec.md").read_text(encoding="utf-8")
        first = spec_text.splitlines()[0]
        if not first.startswith("# "):
            raise ValueError(f"missing spec title: {folder}")
        metadata = config["specs"][folder.name]
        if metadata["state"] not in {"open", "closed"}:
            raise ValueError(f"invalid parent state: {folder.name}")
        assurance = json.loads((folder / "assurance.json").read_text(encoding="utf-8"))
        reqs = ", ".join(req["id"] for req in assurance["requirements"])
        common = f"[spec.md]({base}specs/{folder.name}/spec.md) · [tasks.md]({base}specs/{folder.name}/tasks.md) · [assurance.json]({base}specs/{folder.name}/assurance.json)"
        desired.append({
            "key": spec_id, "kind": "spec", "parent": None,
            "title": f"[{spec_id}] {first[2:].strip()}",
            "body": f"<!-- agent-braid-spec-id: {spec_id} -->\n\nSource: {common}\n\nRequirements: {reqs}.\n\nIssue state is a bounded tracking record, not a scientific or founder approval.\n",
            "milestone": metadata["milestone"], "state": metadata["state"],
        })
        lines = (folder / "tasks.md").read_text(encoding="utf-8").splitlines()
        task_ids: set[str] = set()
        for index, line in enumerate(lines):
            match = TASK_LINE.match(line)
            if not match:
                if re.match(r"^- \[[ x]\] T\d+", line):
                    raise ValueError(f"unparseable task in {folder.name}: {line}")
                continue
            checked, task_id, refs, start = match.groups()
            if task_id in task_ids:
                raise ValueError(f"duplicate task {spec_id}/{task_id}")
            task_ids.add(task_id)
            continuation = []
            for following in lines[index + 1:]:
                if not following.strip() or following.startswith("- [") or following.startswith("## "):
                    break
                if not following.startswith("  "):
                    break
                continuation.append(following.strip())
            task_text = " ".join([start] + continuation)
            key = f"{spec_id}/{task_id}"
            task_keys.add(key)
            if checked == "x" and key in config["task_state_overrides"]:
                raise ValueError(f"remove now-redundant state override: {key}")
            closed = checked == "x" or key in config["task_state_overrides"]
            short = re.sub(r"[`\n]+", "", task_text).strip().rstrip(".")
            if len(short) > 105:
                short = short[:102].rstrip() + "..."
            note = config["task_state_overrides"].get(key, "Source checkbox in tasks.md.")
            desired.append({
                "key": key, "kind": "task", "parent": spec_id,
                "title": f"[{spec_id} {task_id}] {short}",
                "body": f"<!-- agent-braid-task-id: {key} -->\n\n## Task\n\n{task_text}\n\n- Source: {common}\n- Trace: {refs or 'See the parent issue and assurance record.'}\n- State basis: {note}\n\nPlanned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.\n",
                "milestone": metadata["milestone"], "state": "closed" if closed else "open",
                "task_text": task_text,
            })
        if not task_ids:
            raise ValueError(f"no tasks found in {folder.name}")
    unknown_overrides = set(config["task_state_overrides"]) - task_keys
    if unknown_overrides:
        raise ValueError(f"unknown task overrides: {sorted(unknown_overrides)}")
    if any(not reason.strip() for reason in config["task_state_overrides"].values()):
        raise ValueError("task state overrides need a recorded reason")
    by_key = {item["key"]: item for item in desired}
    pending = set(config["project_review_pending"])
    if len(pending) != len(config["project_review_pending"]) or any(
        key not in by_key or by_key[key]["state"] != "open" for key in pending
    ):
        raise ValueError("Project Review pending must name unique open tracked issues")
    return config, desired


def gh_api(path: str, *, method: str = "GET", body: dict | None = None) -> Any:
    command = ["gh", "api", path]
    if method != "GET":
        command.extend(["-X", method])
    if body is not None:
        command.extend(["--input", "-"])
    result = subprocess.run(command, input=json.dumps(body) if body is not None else None,
                            text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"GitHub {method} {path}: {result.stderr.strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def pages(path: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        separator = "&" if "?" in path else "?"
        batch = gh_api(f"{path}{separator}per_page=100&page={page}")
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def remote_inventory(repo: str) -> tuple[dict, dict, dict]:
    milestones = {m["title"]: m for m in pages(f"repos/{repo}/milestones?state=all")}
    issues: dict[str, dict] = {}
    title_without_marker: set[str] = set()
    for issue in pages(f"repos/{repo}/issues?state=all"):
        if "pull_request" in issue:
            continue
        match = MARKER.search(issue.get("body") or "")
        if match:
            key = match.group(1)
            if key in issues:
                raise ValueError(f"duplicate GitHub marker {key}: #{issues[key]['number']} and #{issue['number']}")
            issues[key] = issue
        else:
            title_without_marker.add(issue["title"])
    children: dict[str, set[int]] = {}
    for key, issue in issues.items():
        if re.fullmatch(r"SPEC-\d{3}", key):
            children[key] = {item["id"] for item in pages(f"repos/{repo}/issues/{issue['number']}/sub_issues")}
    return milestones, issues, {"children": children, "unmarked_titles": title_without_marker}


def build_plan(config: dict, desired: list[dict], milestones: dict,
               issues: dict, extra: dict) -> list[dict]:
    operations: list[dict] = []
    for name in config["milestones"]:
        if name not in milestones:
            operations.append({"action": "create_milestone", "name": name})
        elif milestones[name]["state"] != ("closed" if name in config["closed_milestones"] else "open"):
            operations.append({"action": "set_milestone_state", "name": name,
                               "from": milestones[name]["state"],
                               "to": "closed" if name in config["closed_milestones"] else "open"})
    desired_keys = {item["key"] for item in desired}
    for key in sorted(set(issues) - desired_keys):
        operations.append({"action": "review_orphan", "key": key, "issue": issues[key]["number"]})
    for item in desired:
        key = item["key"]
        issue = issues.get(key)
        if issue is None:
            if item["title"] in extra["unmarked_titles"]:
                raise ValueError(f"unmarked issue has desired title {item['title']!r}; review before creating")
            operations.append({"action": "create_issue", "key": key})
        else:
            if issue["title"] != item["title"]:
                operations.append({"action": "update_title", "key": key, "from": issue["title"], "to": item["title"]})
            actual_milestone = (issue.get("milestone") or {}).get("title")
            if actual_milestone != item["milestone"]:
                operations.append({"action": "update_milestone", "key": key, "from": actual_milestone, "to": item["milestone"]})
            if issue["state"] != item["state"]:
                operations.append({"action": "set_state", "key": key, "from": issue["state"], "to": item["state"]})
            if item["kind"] == "task":
                body = issue.get("body") or ""
                task_match = re.search(r"## Task\n\n(.*?)\n\n- Source:", body, re.S)
                if not task_match:
                    operations.append({"action": "review_body", "key": key})
                elif task_match.group(1) != item["task_text"]:
                    operations.append({"action": "update_task_text", "key": key})
        if item["parent"]:
            parent = issues.get(item["parent"])
            if parent is None or issue is None or issue["id"] not in extra["children"].get(item["parent"], set()):
                operations.append({"action": "link_subissue", "key": key, "parent": item["parent"]})
        if issue is None and item["state"] == "closed":
            operations.append({"action": "set_state", "key": key, "from": "open", "to": "closed"})
    return operations


def apply_plan(repo: str, config: dict, desired: list[dict], milestones: dict,
               issues: dict, operations: list[dict]) -> None:
    by_key = {item["key"]: item for item in desired}
    for operation in operations:
        action = operation["action"]
        if action.startswith("review_"):
            raise ValueError(f"manual review required before apply: {operation}")
    for operation in operations:
        action = operation["action"]
        if action == "create_milestone":
            name = operation["name"]
            milestones[name] = gh_api(f"repos/{repo}/milestones", method="POST",
                                      body={"title": name, "description": config["milestones"][name],
                                            "state": "closed" if name in config["closed_milestones"] else "open"})
        elif action == "set_milestone_state":
            name = operation["name"]
            milestone = milestones[name]
            milestones[name] = gh_api(f"repos/{repo}/milestones/{milestone['number']}", method="PATCH",
                                      body={"state": operation["to"]})
        elif action == "create_issue":
            item = by_key[operation["key"]]
            issue = gh_api(f"repos/{repo}/issues", method="POST", body={
                "title": item["title"], "body": item["body"],
                "milestone": milestones[item["milestone"]]["number"],
                "labels": [item["kind"]],
            })
            issues[item["key"]] = issue
        elif action in {"update_title", "update_milestone", "set_state", "update_task_text"}:
            key = operation["key"]
            issue = issues[key]
            item = by_key[key]
            if action == "update_title":
                payload = {"title": item["title"]}
            elif action == "update_milestone":
                payload = {"milestone": milestones[item["milestone"]]["number"]}
            elif action == "set_state":
                payload = {"state": item["state"]}
                if item["state"] == "closed":
                    payload["state_reason"] = "completed"
            else:
                original = issue["body"]
                updated = re.sub(r"(## Task\n\n).*?(\n\n- Source:)",
                                 lambda m: m.group(1) + item["task_text"] + m.group(2), original, count=1, flags=re.S)
                payload = {"body": updated}
            issues[key] = gh_api(f"repos/{repo}/issues/{issue['number']}", method="PATCH", body=payload)
        elif action == "link_subissue":
            parent = issues[operation["parent"]]
            child = issues[operation["key"]]
            gh_api(f"repos/{repo}/issues/{parent['number']}/sub_issues", method="POST",
                   body={"sub_issue_id": child["id"]})
        print(f"applied {action}: {operation.get('key', operation.get('name'))}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["source", "audit", "apply"])
    parser.add_argument("--confirm-repository", help="Required exact owner/repo for remote writes")
    parser.add_argument("--plan-sha256", help="Digest from a reviewed audit; required for apply")
    args = parser.parse_args(argv)
    config, desired = source_inventory()
    if args.mode == "source":
        print(json.dumps({"specs": sum(x["kind"] == "spec" for x in desired),
                          "tasks": sum(x["kind"] == "task" for x in desired),
                          "milestones": len(config["milestones"]),
                          "project_review_pending": len(config["project_review_pending"]),
                          "project_url": config["project_url"]}, indent=2))
        return 0
    repo = config["repository"]
    milestones, issues, extra = remote_inventory(repo)
    operations = build_plan(config, desired, milestones, issues, extra)
    plan_digest = hashlib.sha256(json.dumps(operations, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()
    print(json.dumps({"repository": repo, "project_url": config["project_url"],
                      "plan_sha256": plan_digest, "operations": operations}, indent=2, ensure_ascii=False))
    if args.mode == "audit":
        return 1 if operations else 0
    if args.confirm_repository != repo:
        parser.error(f"apply requires --confirm-repository {repo} after reviewing the audit output")
    if args.plan_sha256 != plan_digest:
        parser.error("apply requires --plan-sha256 from the reviewed audit; rerun audit if the plan changed")
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, text=True,
                            capture_output=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                           capture_output=True, check=True).stdout.strip()
    if branch != "develop" or dirty:
        parser.error("apply requires a clean develop checkout containing the reviewed source records")
    apply_plan(repo, config, desired, milestones, issues, operations)
    print("Repository issues and milestones reconciled. Verify private Project membership and Review pending status in the Project UI.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError) as exc:
        print(f"tracking sync: {exc}", file=sys.stderr)
        sys.exit(2)
