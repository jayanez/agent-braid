# SPDX-License-Identifier: AGPL-3.0-only
"""G0 pre-freeze layout census (measurement tool, not the SPEC-053 mapper).

Reads the founder's own existing Claude Code subagent transcripts locally and
prints ONLY aggregate structure: record-type, content-block-type, tool-name and
input-key-name histograms, how many tool calls are paired with a result, how
many results are errors, the number of subagents per parent session, and the
tool-class shares used to check the C3 cap. No path, file name, directory name,
hash, prompt, file content or tool output is ever printed. Tool names that are
not simple identifiers are bucketed, and every MCP tool name collapses into one
`mcp__*` bucket so that server names are not retained. Stdlib only.

Usage:
    python3 census.py [ROOT ...]

Each ROOT is searched recursively for `subagents/*.jsonl` (default:
~/.claude/projects). One subagent file is one agent; its parent session is the
directory that contains `subagents/`.
"""

import json
import os
import re
import sys

SAFE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
WRITER_CAPABLE = ("write", "bash", "mcp", "other")


def tool_class(name):
    """Mirror probe.classify without importing it, so the census stands alone."""
    if name == "Read":
        return "read"
    if name in ("Edit", "Write", "NotebookEdit"):
        return "write"
    if name == "Bash":
        return "bash"
    if name in ("Grep", "Glob"):
        return "grep_glob"
    if isinstance(name, str) and name.startswith("mcp__"):
        return "mcp"
    return "other"


def safe(label):
    return label if isinstance(label, str) and SAFE_NAME.match(label) else "unprintable"


def bump(histogram, key, amount=1):
    histogram[key] = histogram.get(key, 0) + amount


def find_transcripts(roots):
    """Yield (session_key, file_path). The session key is an index, never printed."""
    sessions = {}
    for root in roots:
        for directory, _, files in os.walk(root):
            if os.path.basename(directory) != "subagents":
                continue
            parent = os.path.dirname(directory)
            for name in sorted(files):
                if name.endswith(".jsonl"):
                    sessions.setdefault(parent, []).append(os.path.join(directory, name))
    for index, parent in enumerate(sorted(sessions)):
        for path in sessions[parent]:
            yield index, path


def scan_file(path, census):
    calls, results = {}, {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            census["lines"] += 1
            try:
                record = json.loads(line)
            except ValueError:
                census["malformed_lines"] += 1
                continue
            if not isinstance(record, dict):
                census["non_object_lines"] += 1
                continue
            bump(census["record_types"], safe(record.get("type")))
            for key in record:
                bump(census["record_keys"], safe(key))
            message = record.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(message, dict) and not isinstance(content, list):
                bump(census["message_content_shapes"], type(content).__name__)
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                kind = safe(block.get("type"))
                bump(census["block_types"], kind)
                if kind == "tool_use" and isinstance(block.get("id"), str):
                    calls.setdefault(block["id"], block)
                elif kind == "tool_result" and isinstance(block.get("tool_use_id"), str):
                    if block["tool_use_id"] not in results:
                        results[block["tool_use_id"]] = block
                        bump(census["result_is_error"], repr(block.get("is_error", "absent")))
    for call_id, call in calls.items():
        name = call.get("name")
        cls = tool_class(name)
        bump(census["class_calls"], cls)
        label = "mcp__*" if cls == "mcp" else safe(name)
        bump(census["tool_names"], label)
        if cls != "mcp":
            params = call.get("input")
            for key in params if isinstance(params, dict) else ():
                bump(census["input_keys_by_tool"].setdefault(label, {}), safe(key))
        if call_id in results:
            bump(census["paired_calls"], cls)
            if results[call_id].get("is_error") is True:
                bump(census["errored_calls"], cls)
        else:
            bump(census["unpaired_calls"], cls)


def shares(class_calls):
    """C3-shaped shares: Grep and Glob leave numerator and denominator."""
    searches = class_calls.get("grep_glob", 0)
    denominator = sum(class_calls.values()) - searches
    unknown_by_class = sum(class_calls.get(c, 0) for c in ("bash", "mcp", "other"))
    total = sum(class_calls.values())
    out = {"counted_calls": denominator, "read_only_search_calls": searches,
           "class_calls_unknown_by_definition": unknown_by_class}
    out["unknown_class_share_percent"] = (round(100 * unknown_by_class / denominator, 1)
                                          if denominator else None)
    out["read_only_search_share_percent"] = round(100 * searches / total, 1) if total else None
    out["bash_share_percent"] = (round(100 * class_calls.get("bash", 0) / total, 1)
                                 if total else None)
    return out


def census(roots):
    out = {"files": 0, "lines": 0, "malformed_lines": 0, "non_object_lines": 0,
           "record_types": {}, "record_keys": {}, "block_types": {},
           "message_content_shapes": {}, "result_is_error": {}, "tool_names": {},
           "input_keys_by_tool": {}, "class_calls": {}, "paired_calls": {},
           "errored_calls": {}, "unpaired_calls": {}}
    per_session = {}
    for session, path in find_transcripts(roots):
        out["files"] += 1
        per_session[session] = per_session.get(session, 0) + 1
        scan_file(path, out)
    out["sessions_with_subagents"] = len(per_session)
    agent_counts = {}
    for count in per_session.values():
        bump(agent_counts, str(count))
    out["subagents_per_session_histogram"] = agent_counts
    out["shares"] = shares(out["class_calls"])
    out["note"] = ("counts only; structure and tool names; no path, hash, content or "
                   "output; MCP names collapsed; subagent files, not G0 runs")
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    roots = argv or [os.path.expanduser("~/.claude/projects")]
    for root in roots:
        if not os.path.isdir(root):
            sys.stderr.write("census: a root is not a directory\n")
            return 2
    json.dump(census(roots), sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
