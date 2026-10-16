#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Resolve frozen commit identities across the reviewed attribution correction.

ADR 0022 rewrote public history to remove a co-author identity that belonged to
an unrelated account. Trees were preserved; commit identities changed. Frozen
records keep naming the original commits. This module maps exactly the listed
identities to their published equivalents and verifies each target by tree and
public reachability. Original objects are never required. Unlisted identities
resolve to themselves, so every other validation path is unchanged.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


EQUIVALENCE = "docs/releases/publication/history-rewrite-equivalence-20261013.json"
CORRECTION = "docs/releases/publication/history-rewrite-equivalence-20261016.json"
RECORD_VERSION = "0.1.0"
FIELDS = {"recordVersion", "adr", "reason", "entries", "tags", "limits"}
ENTRY_FIELDS = {"old", "new", "tree"}
TAG_FIELDS = {"oldName", "oldTagObject", "oldCommit", "newName", "newTagObject",
              "newCommit", "tree"}
HEX40 = re.compile(r"[0-9a-f]{40}")
TAG_NAME = re.compile(r"[a-z0-9][a-z0-9.-]*")


def _git(root: Path, *args: str, allow_failure: bool = False) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_GRAFT_FILE"] = os.devnull
    process = subprocess.run(["git", *args], cwd=root, capture_output=True,
                             check=False, env=environment)
    if process.returncode and not allow_failure:
        raise ValueError(f"Git failed while validating history equivalence: {args[0]}")
    return process


def _canonical(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_equivalence(root: Path) -> dict:
    """Return the validated record, or an empty mapping before its introduction."""
    root = Path(root).resolve()
    path = root / EQUIVALENCE
    head = _git(root, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    if not path.is_file():
        introduced = _git(root, "log", "--format=%H", "--diff-filter=A", head,
                          "--", EQUIVALENCE).stdout.decode("ascii").split()
        if introduced:
            raise ValueError("history equivalence record is missing after introduction")
        return {"entries": {}, "tags": ()}
    payload = path.read_bytes()
    legacy = _validated(str(root), head, hashlib.sha256(payload).hexdigest())
    correction_path = root / CORRECTION
    if not correction_path.is_file():
        if _git(root, "log", "--format=%H", "--diff-filter=A", head, "--", CORRECTION).stdout.strip():
            raise ValueError("history correction record is missing after introduction")
        return legacy
    correction = _validated_correction(str(root), head, hashlib.sha256(correction_path.read_bytes()).hexdigest())
    if any(e['new'] in legacy['entries'] for e in correction['entries'].values()):
        raise ValueError('history correction creates a cross-layer cycle')
    entries = dict(correction['entries'])
    for old, entry in legacy['entries'].items():
        if old in entries:
            raise ValueError("history corrections cannot replace original mapping keys")
        replacement = correction['entries'].get(entry['new'])
        if replacement and replacement['tree'] != entry['tree']:
            raise ValueError("history correction changed a recorded tree")
        entries[old] = {**entry, 'new': replacement['new']} if replacement else entry
    tags = []
    legacy_names = {t['newName'] for t in legacy['tags']}
    if any(t['newName'] in legacy_names and t['oldName'] != t['newName']
           for t in correction['tags']):
        raise ValueError('history correction collides with an original tag name')
    for item in legacy['tags']:
        replacements = [t for t in correction['tags'] if t['oldName'] == item['newName']]
        if not replacements:
            tags.append(item)
            continue
        replacement = replacements[0]
        if (replacement['oldCommit'], replacement['oldTagObject'], replacement['tree']) != (
                item['newCommit'], item['newTagObject'], item['tree']):
            raise ValueError("history correction changed an original tag binding")
        tags.append({**item, 'newName': replacement['newName'],
                     'newCommit': replacement['newCommit'], 'newTagObject': replacement['newTagObject']})
    names = {t['newName'] for t in tags}
    tags.extend(t for t in correction['tags'] if t['newName'] not in names)
    return {'entries': entries, 'tags': tuple(tags)}


@lru_cache(maxsize=16)
def _validated(root_name: str, head: str, payload_hash: str) -> dict:
    return _read_record(root_name, head, payload_hash, EQUIVALENCE,
                        "docs/adr/0022-attribution-correction-history-equivalence.md")


@lru_cache(maxsize=16)
def _validated_correction(root_name: str, head: str, payload_hash: str) -> dict:
    return _read_record(root_name, head, payload_hash, CORRECTION,
                        "docs/adr/0023-second-history-correction-equivalence.md", same_names=True)


def _read_record(root_name, head, payload_hash, relative, adr, same_names=False):
    root = Path(root_name)
    payload = (root / relative).read_bytes()
    if hashlib.sha256(payload).hexdigest() != payload_hash:
        raise ValueError("history equivalence record changed during validation")
    try:
        data = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("history equivalence record is invalid") from exc
    if not isinstance(data, dict) or set(data) != FIELDS \
            or data["recordVersion"] != RECORD_VERSION \
            or data["adr"] != adr \
            or not isinstance(data["reason"], str) or not data["reason"].strip():
        raise ValueError("history equivalence record identity is invalid")
    if payload != _canonical(data):
        raise ValueError("history equivalence record is not canonical JSON")
    if not isinstance(data["limits"], list) or not data["limits"] \
            or any(not isinstance(item, str) or not item.strip() for item in data["limits"]):
        raise ValueError("history equivalence limits are required")
    entries, tags = data["entries"], data["tags"]
    if not isinstance(entries, list) or not entries or not isinstance(tags, list) or not tags:
        raise ValueError("history equivalence inventory is empty")
    for item in entries:
        if not isinstance(item, dict) or set(item) != ENTRY_FIELDS \
                or any(not HEX40.fullmatch(str(item[name])) for name in ENTRY_FIELDS) \
                or item["old"] == item["new"]:
            raise ValueError("history equivalence entry is invalid")
    for item in tags:
        if not isinstance(item, dict) or set(item) != TAG_FIELDS \
                or any(not HEX40.fullmatch(str(item[name]))
                       for name in TAG_FIELDS - {"oldName", "newName"}) \
                or any(not TAG_NAME.fullmatch(str(item[name])) for name in ("oldName", "newName")) \
                or (item["oldName"] == item["newName"] and not same_names) \
                or item["oldTagObject"] == item["newTagObject"]:
            raise ValueError("history equivalence tag is invalid")
    olds = [item["old"] for item in entries]
    news = [item["new"] for item in entries]
    names = [item["newName"] for item in tags]
    old_names = [item['oldName'] for item in tags]
    if olds != sorted(set(olds)) or len(news) != len(set(news)) \
            or names != sorted(set(names)) or set(olds) & set(news) \
            or (same_names and len(old_names) != len(set(old_names))):
        raise ValueError("history equivalence identities must be unique and sorted")
    mapping = {item["old"]: item for item in entries}
    for item in tags:
        entry = mapping.get(item["oldCommit"])
        if entry is not None and (entry["new"], entry["tree"]) != (item["newCommit"], item["tree"]):
            raise ValueError("history equivalence tag contradicts its entry")
    introduced = _git(root, "log", "--format=%H", "--diff-filter=A", head,
                      "--", relative).stdout.decode("ascii").split()
    if len(introduced) != 1 \
            or _git(root, "show", f"{introduced[0]}:{relative}").stdout != payload:
        raise ValueError("history equivalence record must be unchanged since introduction")
    return {"entries": mapping, "tags": tuple(tags)}


def retained_tag_binding(root: Path, ref: str, candidate: str, tag_object: str) -> tuple[str, str]:
    """Resolve only a listed exact old tag binding; never trust a local tag's value."""
    name = ref.removeprefix('refs/tags/')
    # Read the second record directly: composing must retain legacy old bindings.
    root = Path(root).resolve()
    load_equivalence(root)
    path = root / CORRECTION
    if not path.is_file():
        load_equivalence(root)  # missing-after-introduction remains terminal
        return candidate, tag_object
    head = _git(root, 'rev-parse', 'HEAD').stdout.decode().strip()
    correction = _validated_correction(str(root), head, hashlib.sha256(path.read_bytes()).hexdigest())
    matches = [t for t in correction['tags'] if t['oldName'] == name]
    if not matches:
        return candidate, tag_object
    item = matches[0]
    if (candidate, tag_object) != (item['oldCommit'], item['oldTagObject']):
        raise ValueError('history correction does not match retained tag pin')
    return item['newCommit'], item['newTagObject']


def _verified_tag(root: Path, item: dict) -> bool:
    ref = f"refs/tags/{item['newName']}"
    def rev(spec: str) -> str:
        return _git(root, "rev-parse", "--verify", spec, allow_failure=True).stdout.decode().strip()
    return (rev(ref) == item["newTagObject"]
            and _git(root, "cat-file", "-t", ref, allow_failure=True).stdout.decode().strip() == "tag"
            and rev(f"{ref}^{{commit}}") == item["newCommit"]
            and rev(f"{item['newCommit']}^{{tree}}") == item["tree"])


def recorded_equivalent(root: Path, recorded: str) -> str:
    """Return the listed equivalent identity without requiring its objects.

    For preflight before restoration fetches the target; validation must still
    call resolve_public_commit, which verifies tree and reachability.
    """
    entry = load_equivalence(Path(root).resolve())["entries"].get(recorded)
    return recorded if entry is None else entry["new"]


def resolve_public_commit(root: Path, recorded: str, tree: str | None = None) -> str:
    """Map a listed frozen identity to its verified published equivalent.

    Membership in the reviewed record alone decides the route; a locally present
    original object never changes it. Unlisted identities are returned unchanged.
    """
    root = Path(root).resolve()
    entry = load_equivalence(root)["entries"].get(recorded)
    if entry is None:
        return recorded
    new = entry["new"]
    observed = _git(root, "rev-parse", "--verify", f"{new}^{{tree}}",
                    allow_failure=True).stdout.decode("ascii").strip()
    if observed != entry["tree"] or (tree is not None and tree != entry["tree"]):
        raise ValueError(f"history equivalence tree does not match: {recorded}")
    if _git(root, "merge-base", "--is-ancestor", new, "HEAD", allow_failure=True).returncode == 0:
        return new
    for item in load_equivalence(root)["tags"]:
        if _verified_tag(root, item) and _git(
                root, "merge-base", "--is-ancestor", new, item["newCommit"],
                allow_failure=True).returncode == 0:
            return new
    raise ValueError(f"history equivalence target is not in public ancestry: {recorded}")
