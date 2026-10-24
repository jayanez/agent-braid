# SPDX-License-Identifier: AGPL-3.0-only
"""G0 transcript read/write probe (measurement tool, not the SPEC-053 mapper).

Reads Claude Code subagent transcript JSONL files locally and in memory and
prints ONLY integer counts: per agent and tool class, and per run the number of
ordered agent pairs and distinct paths with a read/write overlap. No path, path
hash, prompt, file content or tool output is ever written. Stdlib only.

Usage (agents in preregistered ordinal order):
    python3 probe.py --agent WORKTREE_ROOT TRANSCRIPT.jsonl \
                     --agent WORKTREE_ROOT TRANSCRIPT.jsonl ...

Transcript shape (observed by the pre-freeze census, see census.py): one JSON
object per line; assistant lines carry message.content blocks of
{"type": "tool_use", "id", "name", "input"}; user lines carry blocks of
{"type": "tool_result", "tool_use_id", "is_error"?}. A missing is_error means
success; only is_error true is an error. Repeated tool_use ids are counted
once. Records whose message.content is a string, and every other record or
block kind, are ignored. A layout that differs from the census at run time is
recorded as probe-unavailable by the founder; this file is never patched after
its hash is recorded.

Counting rules (preregistered, see the proposal):
- A call with no result record, or with is_error true, is a failed call. A
  failed call is never an effect (never a read or a write for the overlap).
- unknown_writer_calls (C3 numerator): every Bash, mcp__* and other call, plus
  every failed write-class call (Edit, Write, NotebookEdit), including a write
  request that has no result record.
- denominator_calls (C3 denominator): every counted call except Grep and Glob.
- Grep and Glob are read-only searches: they leave numerator and denominator
  and are reported separately as read_only_search_calls. Failed Read calls are
  reported separately as failed_read_calls and are not unknown writers.
- Paths must be absolute and under the worktree root after lexical
  normalization (no filesystem access, no symlink following); anything else
  counts as outside_worktree and is never matched.
"""

import argparse
import json
import posixpath
import sys

WRITE_TOOLS = {"Edit": "file_path", "Write": "file_path", "NotebookEdit": "notebook_path"}
READ_TOOLS = {"Read": "file_path"}
CLASSES = ("read", "write", "bash", "grep_glob", "mcp", "other")
# Writer-capable classes that are unknown by definition (C3 numerator).
UNKNOWN_CLASSES = ("bash", "mcp", "other")


def classify(name):
    if name in READ_TOOLS:
        return "read"
    if name in WRITE_TOOLS:
        return "write"
    if name == "Bash":
        return "bash"
    if name in ("Grep", "Glob"):
        return "grep_glob"
    if isinstance(name, str) and name.startswith("mcp__"):
        return "mcp"
    return "other"


def relative_path(root, value):
    """Repository-relative path, or None when not absolute and inside root."""
    if not isinstance(value, str) or not value.startswith("/"):
        return None
    root = posixpath.normpath(root)
    path = posixpath.normpath(value)
    prefix = root.rstrip("/") + "/"
    if not path.startswith(prefix):
        return None
    return path[len(prefix):]


def _blocks(record):
    message = record.get("message") if isinstance(record, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return content if isinstance(content, list) else []


def scan_agent(root, lines):
    """Return (counts, read_paths, written_paths). Paths stay in memory only."""
    calls = {}
    results = {}
    malformed = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        for block in _blocks(record):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and isinstance(block.get("id"), str):
                calls.setdefault(block["id"], block)
            elif block.get("type") == "tool_result" and isinstance(block.get("tool_use_id"), str):
                results.setdefault(block["tool_use_id"], block.get("is_error") is True)
    counts = {name: 0 for name in CLASSES}
    counts.update(total_calls=0, denominator_calls=0, unknown_writer_calls=0,
                  read_only_search_calls=0, failed_read_calls=0, failed_write_calls=0,
                  failed_or_unpaired_calls=0, outside_worktree=0, malformed_lines=malformed)
    reads, writes = set(), set()
    for call_id, call in calls.items():
        cls = classify(call.get("name"))
        counts[cls] += 1
        counts["total_calls"] += 1
        failed = call_id not in results or results[call_id]
        if failed:
            counts["failed_or_unpaired_calls"] += 1
        if cls == "grep_glob":
            counts["read_only_search_calls"] += 1
            continue
        counts["denominator_calls"] += 1
        if cls in UNKNOWN_CLASSES or (failed and cls == "write"):
            counts["unknown_writer_calls"] += 1
        if failed and cls == "read":
            counts["failed_read_calls"] += 1
        if failed and cls == "write":
            counts["failed_write_calls"] += 1
        if failed or cls not in ("read", "write"):
            continue
        field = (READ_TOOLS if cls == "read" else WRITE_TOOLS)[call["name"]]
        params = call.get("input")
        rel = relative_path(root, params.get(field)) if isinstance(params, dict) else None
        if rel is None:
            counts["outside_worktree"] += 1
        else:
            (reads if cls == "read" else writes).add(rel)
    return counts, reads, writes


def overlaps(agents):
    """Count ordered pairs (i, j) and distinct paths where i read p, j wrote p, i never wrote p."""
    pairs = 0
    distinct = set()
    for i, (_, reads_i, writes_i) in enumerate(agents):
        for j, (_, _, writes_j) in enumerate(agents):
            if i == j:
                continue
            hit = (reads_i & writes_j) - writes_i
            if hit:
                pairs += 1
                distinct |= hit
    return {"ordered_pairs_with_overlap": pairs, "distinct_paths_with_overlap": len(distinct)}


def probe(specs):
    """specs: [(worktree_root, iterable_of_lines)] in ordinal order."""
    agents = [scan_agent(root, lines) for root, lines in specs]
    run = overlaps(agents)
    for key in ("denominator_calls", "unknown_writer_calls", "read_only_search_calls"):
        run[key] = sum(a[0][key] for a in agents)
    return {
        "agents": [dict(ordinal=n + 1, **a[0]) for n, a in enumerate(agents)],
        "run": run,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--agent", nargs=2, action="append", required=True,
                        metavar=("WORKTREE_ROOT", "TRANSCRIPT"))
    args = parser.parse_args(argv)
    specs = []
    for root, path in args.agent:
        with open(path, encoding="utf-8", errors="replace") as handle:
            specs.append((root, handle.read().splitlines()))
    json.dump(probe(specs), sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
