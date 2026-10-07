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
TRACE_FALLBACK = "- Trace: See the parent issue and assurance record."
LEGACY_TRACE_FALLBACK = "- Trace: No direct REQ/SC reference in tasks.md; see the parent issue and assurance record."


def validate_milestone_numbers(config: dict) -> dict:
    numbers = config.get("milestone_numbers", {})
    if not isinstance(numbers, dict) or not set(numbers) <= set(config["milestones"]):
        raise ValueError("milestone numbers must name declared milestones")
    if any(type(number) is not int or number <= 0 for number in numbers.values()):
        raise ValueError("milestone numbers must be positive integers")
    if len(set(numbers.values())) != len(numbers):
        raise ValueError("duplicate configured milestone number")
    return numbers


def resolve_milestones(config: dict, milestones: dict) -> dict:
    numbers = validate_milestone_numbers(config)
    by_number = {item["number"]: item for item in milestones.values()}
    if len(by_number) != len(milestones):
        raise ValueError("duplicate remote milestone number")
    resolved = {}
    for name in config["milestones"]:
        if name in numbers:
            number = numbers[name]
            if number not in by_number:
                raise ValueError(f"registered milestone #{number} is missing; never recreate it")
            milestone = by_number[number]
            if name in milestones and milestones[name]["number"] != number:
                raise ValueError(f"milestone title collision: {name!r}")
        else:
            milestone = milestones.get(name)
        if milestone is not None:
            resolved[name] = milestone
    if len({item["number"] for item in resolved.values()}) != len(resolved):
        raise ValueError("multiple configured names resolve to one milestone")
    return resolved


def source_inventory(root: Path = ROOT, config_path: Path = CONFIG) -> tuple[dict, list[dict]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_milestone_numbers(config)
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


def remote_inventory(repo: str, *, milestone_titles_only: bool = False) -> tuple[dict, dict, dict]:
    records = pages(f"repos/{repo}/milestones?state=all")
    milestones = {m["title"]: m for m in records}
    if len(milestones) != len(records):
        raise ValueError("duplicate remote milestone title")
    if milestone_titles_only:
        return milestones, {}, {}
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
               issues: dict, extra: dict, *, milestone_titles_only: bool = False) -> list[dict]:
    operations: list[dict] = []
    numbers = validate_milestone_numbers(config)
    if milestone_titles_only and set(numbers) != set(config["milestones"]):
        raise ValueError("title-only reconciliation requires a number for every milestone")
    resolved = resolve_milestones(config, milestones)
    for name in config["milestones"]:
        milestone = resolved.get(name)
        if milestone is None:
            operations.append({"action": "create_milestone", "name": name})
            continue
        if milestone.get("title", name) != name:
            operations.append({"action": "rename_milestone", "number": milestone["number"],
                               "from": milestone["title"], "to": name})
        if not milestone_titles_only and milestone["state"] != ("closed" if name in config["closed_milestones"] else "open"):
            operations.append({"action": "set_milestone_state", "name": name,
                               "from": milestone["state"],
                               "to": "closed" if name in config["closed_milestones"] else "open"})
    if milestone_titles_only:
        return operations
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
            actual = issue.get("milestone") or {}
            actual_milestone = actual.get("title")
            matches = (actual.get("number") == numbers[item["milestone"]]
                       if item["milestone"] in numbers else actual_milestone == item["milestone"])
            if not matches:
                operations.append({"action": "update_milestone", "key": key, "from": actual_milestone, "to": item["milestone"]})
            if issue["state"] != item["state"]:
                operations.append({"action": "set_state", "key": key, "from": issue["state"], "to": item["state"]})
            if item["kind"] == "task":
                body = issue.get("body") or ""
                task_match = re.search(r"## Task\n\n(.*?)\n\n- Source:", body, re.S)
                expected_trace = re.search(r"^- Trace: .*$", item.get("body", ""), re.M)
                actual_traces = re.findall(r"^- Trace: .*$", body, re.M)
                trace_changed = expected_trace and actual_traces != [expected_trace.group()] and not (
                    expected_trace.group() == TRACE_FALLBACK and actual_traces == [LEGACY_TRACE_FALLBACK]
                )
                if not task_match or (expected_trace and len(actual_traces) != 1):
                    operations.append({"action": "review_body", "key": key})
                elif task_match.group(1) != item["task_text"] or trace_changed:
                    operation = {"action": "update_task_text", "key": key}
                    if trace_changed:
                        operation.update(trace_from=actual_traces[0], trace_to=expected_trace.group())
                    operations.append(operation)
        if item["parent"]:
            parent = issues.get(item["parent"])
            if parent is None or issue is None or issue["id"] not in extra["children"].get(item["parent"], set()):
                operations.append({"action": "link_subissue", "key": key, "parent": item["parent"]})
        if issue is None and item["state"] == "closed":
            operations.append({"action": "set_state", "key": key, "from": "open", "to": "closed"})
    return operations


def milestone_plan(config: dict, desired: list[dict], milestones: dict,
                  issues: dict, extra: dict, milestone_number: int,
                  new_record_keys: set[str] | None = None) -> tuple[dict, list[dict], dict, list[dict]]:
    """Build a fail-closed plan for one registered milestone and its managed issues."""
    names = [name for name, number in validate_milestone_numbers(config).items()
             if number == milestone_number]
    if len(names) != 1:
        raise ValueError(f"milestone number #{milestone_number} is not uniquely registered")
    name = names[0]
    selected = [item for item in desired if item["milestone"] == name]
    selected_keys = {item["key"] for item in selected}
    new_record_keys = new_record_keys or set()
    desired_by_key = {item["key"]: item for item in desired}
    if not selected:
        raise ValueError(f"milestone #{milestone_number} has no configured source records")
    for key in sorted(new_record_keys):
        if key not in desired_by_key:
            raise ValueError(f"new-record allowlist contains unknown source record: {key}")
        if key not in selected_keys:
            raise ValueError(f"new-record allowlist contains a record outside milestone #{milestone_number}: {key}")
        if key in issues:
            raise ValueError(f"new-record allowlist entry already exists remotely: {key}")

    # The remote inventory is intentionally complete. Check every issue currently
    # assigned here before narrowing, so a moved/deleted/unknown managed ID cannot
    # disappear behind the selected source filter.
    for key, issue in issues.items():
        actual = issue.get("milestone") or {}
        if actual.get("number") == milestone_number and key not in selected_keys:
            raise ValueError(f"unknown or out-of-scope managed issue #{issue['number']} is assigned to milestone #{milestone_number}: {key}")
    for item in selected:
        issue = issues.get(item["key"])
        if issue is None:
            if item["key"] not in new_record_keys:
                raise ValueError(f"managed issue is missing for selected source record {item['key']}")
            continue
        actual = issue.get("milestone") or {}
        if actual.get("number") != milestone_number:
            raise ValueError(f"selected issue {item['key']} moved from registered milestone #{milestone_number}")

    scoped_config = {
        **config,
        "milestones": {name: config["milestones"][name]},
        "closed_milestones": [name] if name in config["closed_milestones"] else [],
        "milestone_numbers": {name: milestone_number},
    }
    scoped_desired = selected
    scoped_issues = {key: issues[key] for key in selected_keys if key in issues}
    scoped_extra = {
        "children": {key: value for key, value in extra.get("children", {}).items() if key in selected_keys},
        "unmarked_titles": extra.get("unmarked_titles", set()),
    }
    scoped_milestones = {title: milestone for title, milestone in milestones.items()
                         if milestone.get("number") == milestone_number}
    operations = build_plan(scoped_config, scoped_desired, scoped_milestones,
                            scoped_issues, scoped_extra)
    return scoped_config, scoped_desired, scoped_issues, operations


def apply_plan(repo: str, config: dict, desired: list[dict], milestones: dict,
               issues: dict, operations: list[dict]) -> None:
    by_key = {item["key"]: item for item in desired}
    milestones = resolve_milestones(config, milestones)
    for operation in operations:
        action = operation["action"]
        if action.startswith("review_"):
            raise ValueError(f"manual review required before apply: {operation}")
    for operation in operations:
        action = operation["action"]
        if action == "rename_milestone":
            milestones[operation["to"]] = gh_api(
                f"repos/{repo}/milestones/{operation['number']}", method="PATCH",
                body={"title": operation["to"]})
        elif action == "create_milestone":
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
                if "trace_to" in operation:
                    expected_trace = re.search(r"^- Trace: .*$", item["body"], re.M)
                    if not expected_trace or expected_trace.group() != operation["trace_to"] \
                            or re.findall(r"^- Trace: .*$", original, re.M) != [operation["trace_from"]]:
                        raise ValueError(f"reviewed task trace changed before apply: {key}")
                    updated = re.sub(r"^- Trace: .*$", lambda m: operation["trace_to"],
                                     updated, count=1, flags=re.M)
                payload = {"body": updated}
            issues[key] = gh_api(f"repos/{repo}/issues/{issue['number']}", method="PATCH", body=payload)
        elif action == "link_subissue":
            parent = issues[operation["parent"]]
            child = issues[operation["key"]]
            gh_api(f"repos/{repo}/issues/{parent['number']}/sub_issues", method="POST",
                   body={"sub_issue_id": child["id"]})
        print(f"applied {action}: {operation.get('key', operation.get('name', operation.get('to')))}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["source", "audit", "apply"])
    parser.add_argument("--confirm-repository", help="Required exact owner/repo for remote writes")
    parser.add_argument("--plan-sha256", help="Digest from a reviewed audit; required for apply")
    parser.add_argument("--milestone-titles-only", action="store_true",
                        help="Audit/apply only registered milestone titles; never write issues or states")
    parser.add_argument("--milestone-number", type=int,
                        help="Audit/apply only source records assigned to this registered milestone number")
    parser.add_argument("--new-record-key", action="append", default=[], metavar="ID",
                        help="Explicitly authorize creation of this missing managed ID within --milestone-number (repeatable)")
    args = parser.parse_args(argv)
    if args.mode == "source" and (args.milestone_titles_only or args.milestone_number is not None):
        parser.error("milestone scopes are available only for audit/apply")
    if args.milestone_titles_only and args.milestone_number is not None:
        parser.error("--milestone-titles-only and --milestone-number are mutually exclusive")
    if args.new_record_key and args.milestone_number is None:
        parser.error("--new-record-key requires --milestone-number")
    if len(args.new_record_key) != len(set(args.new_record_key)):
        parser.error("--new-record-key entries must be unique")
    if args.milestone_number is not None and args.milestone_number <= 0:
        parser.error("--milestone-number must be a positive integer")
    config, desired = source_inventory()
    if args.mode == "source":
        print(json.dumps({"specs": sum(x["kind"] == "spec" for x in desired),
                          "tasks": sum(x["kind"] == "task" for x in desired),
                          "milestones": len(config["milestones"]),
                          "project_review_pending": len(config["project_review_pending"]),
                          "project_url": config["project_url"]}, indent=2))
        return 0
    repo = config["repository"]
    milestones, issues, extra = remote_inventory(repo, milestone_titles_only=args.milestone_titles_only)
    if args.milestone_number is not None:
        scoped_config, scoped_desired, scoped_issues, operations = milestone_plan(
            config, desired, milestones, issues, extra, args.milestone_number,
            set(args.new_record_key))
        scoped_milestones = {title: milestone for title, milestone in milestones.items()
                             if milestone.get("number") == args.milestone_number}
        scope = f"milestone:{args.milestone_number}"
        digest_payload = {"repository": repo, "scope": scope,
                          "milestone_number": args.milestone_number,
                          "new_record_keys": sorted(args.new_record_key), "operations": operations}
    else:
        scoped_config, scoped_desired, scoped_issues, scoped_milestones = config, desired, issues, milestones
        operations = build_plan(config, desired, milestones, issues, extra,
                                milestone_titles_only=args.milestone_titles_only)
        scope = "milestone-titles" if args.milestone_titles_only else "full"
        digest_payload = {"repository": repo, "scope": scope, "operations": operations}
    plan_digest = hashlib.sha256(json.dumps(digest_payload,
                                            sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()
    print(json.dumps({"repository": repo, "project_url": config["project_url"],
                      "scope": scope,
                      **({"milestone_number": args.milestone_number} if args.milestone_number is not None else {}),
                      **({"new_record_keys": sorted(args.new_record_key)} if args.milestone_number is not None else {}),
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
    apply_plan(repo, scoped_config, scoped_desired, scoped_milestones, scoped_issues, operations)
    if args.milestone_titles_only:
        print("Registered milestone titles reconciled; issue and milestone states were outside this scope.")
    elif args.milestone_number is not None:
        print(f"Registered milestone #{args.milestone_number} reconciled within its reviewed scope.")
    else:
        print("Repository issues and milestones reconciled. Verify private Project membership and Review pending status in the Project UI.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError) as exc:
        print(f"tracking sync: {exc}", file=sys.stderr)
        sys.exit(2)
