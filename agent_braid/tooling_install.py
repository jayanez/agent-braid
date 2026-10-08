# SPDX-License-Identifier: AGPL-3.0-only
"""Receipt-owned, previewed local host configuration. No host/model sessions."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import metadata
from importlib import resources
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import tomllib
from typing import Callable

SCHEMA = "agent-braid-installation/v0.1"
MAX_CONFIG = 2 * 1024 * 1024
NAME = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")


class InstallationRefused(ValueError):
    """An ambiguous target or ownership change prevents a local transaction."""


def _require(value, message):
    if not value:
        raise InstallationRefused(message)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON member")
        result[key] = value
    return result


def _parse_json(raw: bytes):
    _require(len(raw) <= MAX_CONFIG, "configuration exceeds 2 MiB")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              InstallationRefused("nonfinite JSON value")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InstallationRefused("invalid UTF-8 JSON configuration") from exc


def _read(path: Path) -> bytes | None:
    _check_path(path)
    try:
        with path.open("rb") as stream:
            value = stream.read(MAX_CONFIG + 1)
    except FileNotFoundError:
        return None
    _require(len(value) <= MAX_CONFIG, "owned/configuration file exceeds 2 MiB")
    return value


def _check_path(path: Path) -> None:
    _require(path.is_absolute(), "destination must be absolute")
    for part in (path, *path.parents):
        _require(not part.is_symlink(), "symlink destinations are not owned")
    if path.exists():
        _require(path.is_file(), "destination is not a regular file")


def _canonical(path: Path) -> Path:
    # Reject symlink spellings rather than granting an alias a wider root.
    absolute = path.expanduser().absolute()
    for part in (absolute, *absolute.parents):
        _require(not part.is_symlink(), "root must use its canonical path")
    _require(absolute.is_dir(), "configured root must be an existing directory")
    resolved = absolute.resolve(strict=True)
    _require(resolved == absolute, "root must use its canonical path")
    return resolved


@dataclass(frozen=True)
class Selection:
    host: str
    scope: str
    source_root: Path
    result_root: Path
    name: str = "agent-braid"
    home: Path | None = None
    codex_home: Path | None = None
    destination: Path | None = None
    receipt: Path | None = None
    executable: Path | None = None
    enable_runtime: bool = False
    grant_store: Path | None = None

    def paths(self) -> tuple[Path, Path, Path]:
        _require(self.host in {"codex", "claude"}, "unsupported host")
        _require(self.scope in {"user", "project"}, "unsupported scope")
        _require(NAME.fullmatch(self.name), "invalid server name")
        home = (self.home or Path.home()).expanduser().absolute()
        source = _canonical(self.source_root)
        results = _canonical(self.result_root)
        _require(not results.is_relative_to(source), "result root overlaps source")
        _require(not source.is_relative_to(results), "source overlaps result root")
        if self.enable_runtime:
            _require(self.grant_store is not None, "runtime requires explicit grant store")
        if self.grant_store is not None:
            grant = self.grant_store.expanduser().absolute()
            _check_path(grant)
            _require(not grant.is_relative_to(source), "grant store overlaps source")
            _require(not grant.is_relative_to(results) and not source.is_relative_to(grant)
                     and not results.is_relative_to(grant), "grant store overlaps configured roots")
        if self.destination is not None:
            base = self.destination.expanduser().absolute()
            config = base / ("config.toml" if self.host == "codex" else "config.json")
            skills = base / "skills"
            receipt = base / "receipts" / f"{self.name}.json"
        elif self.host == "codex":
            base = (self.codex_home or Path(os.environ.get("CODEX_HOME", str(home / ".codex")))).expanduser().absolute()
            config = (base if self.scope == "user" else source / ".codex") / "config.toml"
            skills = (home if self.scope == "user" else source) / ".agents" / "skills"
            receipt = (base if self.scope == "user" else source / ".codex") / "agent-braid-receipts" / f"{self.name}.json"
        else:
            config = home / ".claude.json" if self.scope == "user" else source / ".mcp.json"
            skills = (home if self.scope == "user" else source) / ".claude" / "skills"
            receipt = (home if self.scope == "user" else source) / ".claude" / "agent-braid-receipts" / f"{self.name}.json"
        receipt = self.receipt.expanduser().absolute() if self.receipt else receipt
        _require(receipt != config and not receipt.is_relative_to(skills), "receipt collides with an asset")
        return config, skills, receipt

    def server(self) -> dict:
        self.paths()
        executable = (self.executable or Path(sys.executable)).absolute()
        _require(executable.is_file() and os.access(executable, os.X_OK), "selected executable is unavailable")
        args = ["-m", "agent_braid", "tooling", "serve", "--source-root", str(_canonical(self.source_root)),
                "--result-root", str(_canonical(self.result_root))]
        if self.enable_runtime:
            args += ["--enable-runtime", "--grant-store", str(self.grant_store)]
        return {"command": str(executable), "args": args}


def _members(text: str, start: int = 0):
    """Validated JSON object member spans; preserve every untouched byte."""
    decoder = json.JSONDecoder()
    i = start
    while text[i].isspace():
        i += 1
    _require(text[i] == "{", "configuration member must be an object")
    opening = i
    i += 1
    members = []
    while True:
        while text[i].isspace():
            i += 1
        if text[i] == "}":
            return opening, i, members
        key_start = i
        key, key_end = decoder.raw_decode(text, i)
        i = key_end
        while text[i].isspace():
            i += 1
        _require(text[i] == ":", "invalid JSON member")
        i += 1
        while text[i].isspace():
            i += 1
        value_start = i
        _, value_end = decoder.raw_decode(text, i)
        members.append((key, key_start, value_start, value_end))
        i = value_end
        while text[i].isspace():
            i += 1
        if text[i] == ",":
            i += 1
        else:
            _require(text[i] == "}", "invalid JSON object")
            return opening, i, members


def _json_entry(raw: bytes, name: str) -> bytes | None:
    parsed = _parse_json(raw)
    _require(isinstance(parsed, dict), "host JSON configuration must be an object")
    text = raw.decode("utf-8")
    _, _, members = _members(text)
    servers = next((m for m in members if m[0] == "mcpServers"), None)
    if servers is None:
        return None
    _require(isinstance(parsed["mcpServers"], dict), "mcpServers must be an object")
    _, _, entries = _members(text, servers[2])
    member = next((m for m in entries if m[0] == name), None)
    return text[member[2]:member[3]].encode("utf-8") if member else None


def _json_edit(raw: bytes, name: str, entry: bytes | None) -> bytes:
    _parse_json(raw)
    text = raw.decode("utf-8")
    _, end, members = _members(text)
    servers = next((m for m in members if m[0] == "mcpServers"), None)
    if servers is None:
        _require(entry is not None, "cannot remove missing server")
        addition = json.dumps("mcpServers") + ": {" + json.dumps(name) + ": " + entry.decode() + "}"
        return (text[:end] + ("," if members else "") + addition + text[end:]).encode()
    # Validate object type before scanning; scalars never enter _members.
    _json_entry(raw, name)
    _, end, entries = _members(text, servers[2])
    member = next((m for m in entries if m[0] == name), None)
    if member is None:
        _require(entry is not None, "cannot remove missing server")
        addition = json.dumps(name) + ": " + entry.decode()
        return (text[:end] + ("," if entries else "") + addition + text[end:]).encode()
    if entry is not None:
        return (text[:member[2]] + entry.decode() + text[member[3]:]).encode()
    index = entries.index(member)
    begin, finish = member[1], member[3]
    if index + 1 < len(entries):
        # Remove the following separator, preserving the next member's whitespace.
        comma = text.index(",", finish, entries[index + 1][1])
        finish = comma + 1
    elif index > 0:
        begin = text.index(",", entries[index - 1][3], begin)
    return (text[:begin] + text[finish:]).encode()


def _toml_entry(name: str, server: dict) -> bytes:
    return (f"# agent-braid owned {name} begin\n[mcp_servers.{name}]\n"
            + "command = " + json.dumps(server["command"], ensure_ascii=False) + "\n"
            + "args = " + json.dumps(server["args"], ensure_ascii=False) + "\n"
            + f"# agent-braid owned {name} end\n").encode()


def _toml_parse(raw: bytes):
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise InstallationRefused("invalid UTF-8 TOML configuration") from exc


def _config_entry(raw: bytes, host: str, name: str, owned: bytes | None = None, *, allow_modified=False):
    if host == "claude":
        return _json_entry(raw, name)
    parsed = _toml_parse(raw)
    servers = parsed.get("mcp_servers", {})
    _require(isinstance(servers, dict), "mcp_servers must be a table")
    if name not in servers:
        return None
    if allow_modified and (owned is None or raw.count(owned) != 1):
        return b""  # present, but never authorize deletion of modified bytes
    _require(owned is not None and raw.count(owned) == 1,
             "existing TOML server is unowned or modified")
    # Exact block alone is insufficient if another subtable extends this entry.
    block = _toml_parse(owned)["mcp_servers"][name]
    if allow_modified and servers[name] != block:
        return b""
    _require(servers[name] == block, "owned TOML server has additional shared keys")
    return owned


@dataclass(frozen=True)
class Change:
    path: Path
    before: bytes | None
    after: bytes | None

    def describe(self):
        return {"path": str(self.path), "beforeSha256": _digest(self.before) if self.before is not None else None,
                "afterSha256": _digest(self.after) if self.after is not None else None,
                "effect": "remove" if self.after is None else "create" if self.before is None else "replace"}


@dataclass
class Transaction:
    changes: list[Change]
    summary: dict

    def preview(self):
        result = dict(self.summary)
        result["changes"] = [change.describe() for change in self.changes]
        result["previewDigest"] = _digest(_json(result))
        return result


def _load_receipt(path: Path, selection: Selection, config: Path, skills: Path):
    raw = _read(path)
    if raw is None:
        return None
    value = _parse_json(raw)
    _require(isinstance(value, dict) and value.get("schema") == SCHEMA, "unknown installation receipt")
    _require((value.get("host"), value.get("scope"), value.get("serverName"), value.get("configPath"), value.get("skillsPath"))
             == (selection.host, selection.scope, selection.name, str(config), str(skills)), "receipt selection mismatch")
    _require(isinstance(value.get("files"), dict), "invalid receipt inventory")
    for relative, digest in value["files"].items():
        _require(re.fullmatch(r"agent-braid-(analyze|plan|execute|recover|evidence)/SKILL.md", relative), "receipt inventory escapes owned skill")
        _require(isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest), "invalid receipt digest")
    _require(isinstance(value.get("entry"), str), "invalid receipt server entry")
    directories = value.get("skillDirectories", [])
    _require(isinstance(directories, list) and len(directories) == len(set(directories))
             and all(isinstance(name, str) and re.fullmatch(r"agent-braid-(analyze|plan|execute|recover|evidence)", name)
                     for name in directories), "invalid receipt directory inventory")
    backups = value.get("backups", [])
    _require(isinstance(backups, list), "invalid receipt backup inventory")
    allowed_targets = {config, *(skills / name / "SKILL.md" for name in directories)}
    for record in backups:
        _require(isinstance(record, dict) and set(record) == {"path", "sha256"}
                 and isinstance(record["path"], str) and isinstance(record["sha256"], str)
                 and re.fullmatch(r"[a-f0-9]{64}", record["sha256"]), "invalid receipt backup record")
        allowed_names = {str(target.parent / f".{target.name}.braid-backup-{record['sha256']}") for target in allowed_targets}
        _require(record["path"] in allowed_names, "receipt backup is outside generated owned inventory")
    return value


def _planned_backups(changes, previous):
    records = list(previous)
    for change in changes:
        if change.before is not None:
            record = {"path": str(change.path.parent / f".{change.path.name}.braid-backup-{_digest(change.before)}"),
                      "sha256": _digest(change.before)}
            if record not in records:
                records.append(record)
    return records


def _unowned_skill_contents(directory: Path, receipt):
    backups = {record.get("path"): record.get("sha256") for record in receipt.get("backups", [])
               if isinstance(record, dict)} if receipt else {}
    foreign = []
    for item in directory.iterdir():
        if item.name == "SKILL.md":
            continue
        expected = backups.get(str(item))
        if expected is not None and item.is_file() and not item.is_symlink():
            raw = _read(item)
            if raw is not None and _digest(raw) == expected:
                continue
        foreign.append(item.name)
    return foreign


def plan(selection: Selection, *, operation: str = "install", source_checkout: bool = False) -> Transaction:
    """Prepare a local transaction; this function never writes or starts a host."""
    _require(operation in {"configure", "install", "update", "uninstall"}, "unknown lifecycle operation")
    config, skills, receipt_path = selection.paths()
    receipt = _load_receipt(receipt_path, selection, config, skills)
    config_before = _read(config)
    raw = config_before if config_before is not None else (b"" if selection.host == "codex" else b"{}\n")
    old_entry = receipt["entry"].encode() if receipt else None
    entry = _config_entry(raw, selection.host, selection.name, old_entry, allow_modified=operation == "uninstall")
    changes = []
    residuals = []
    if operation == "uninstall":
        if receipt is None:
            return Transaction([], {"operation": operation, "status": "unowned", "host": selection.host,
                                    "scope": selection.scope, "residuals": ["no receipt; no files removed"]})
        if entry == old_entry:
            after = _json_edit(raw, selection.name, None) if selection.host == "claude" else raw.replace(old_entry, b"", 1)
            # Retain surrounding bytes including empty shared containers.
            if config_before != after:
                changes.append(Change(config, config_before, after))
        elif entry is not None:
            residuals.append("modified server entry retained")
        retained = {}
        for name in receipt.get("skillDirectories", []):
            directory = skills / name
            _require(not directory.is_symlink(), "owned skill directory is unsafe")
            if directory.exists():
                _require(directory.is_dir(), "owned skill directory is unsafe")
                if _unowned_skill_contents(directory, receipt):
                    residuals.append(f"unowned skill contents retained: {name}")
        for relative, digest in receipt["files"].items():
            target = skills / relative
            before = _read(target)
            if before is None:
                continue
            if _digest(before) == digest:
                changes.append(Change(target, before, None))
            else:
                retained[relative] = digest
                residuals.append(f"modified skill retained: {relative}")
        # Keep ownership of residuals so a second uninstall never adopts user edits.
        receipt_after = dict(receipt, files=retained, state="residual" if residuals else "uninstalled", residuals=residuals,
                             backups=_planned_backups(changes, receipt.get("backups", [])))
        before = _read(receipt_path)
        after = _json(receipt_after)
        if before != after:
            changes.append(Change(receipt_path, before, after))
        return Transaction(changes, {"operation": operation, "status": "preview", "host": selection.host,
                                    "scope": selection.scope, "configPath": str(config), "receipt": str(receipt_path),
                                    "residuals": residuals})

    _require(entry is None or receipt is not None, "server name collision; no owned receipt")
    _require(receipt is None or entry == old_entry or (entry is None and receipt.get("state") == "uninstalled"),
             "owned server changed; refusing overwrite")
    _require(operation != "update" or receipt is not None, "update requires an owned receipt")
    _require(operation != "update" or receipt.get("state") == "installed", "update requires an active installation")
    server = selection.server()
    new_entry = _toml_entry(selection.name, server) if selection.host == "codex" else _json(server).rstrip(b"\n")
    if selection.host == "codex" and old_entry is not None and old_entry.startswith(b"\n"):
        new_entry = b"\n" + new_entry
    if selection.host == "codex":
        if entry is not None:
            config_after = raw.replace(old_entry, new_entry, 1)
        else:
            separator = b"" if not raw or raw.endswith(b"\n") else b"\n"
            new_entry = separator + new_entry  # receipt owns inserted separator too
            config_after = raw + new_entry
        _toml_parse(config_after)
    else:
        config_after = _json_edit(raw, selection.name, new_entry)
        _parse_json(config_after)
    if config_before != config_after:
        changes.append(Change(config, config_before, config_after))
    inventory = dict(receipt["files"]) if receipt else {}
    bundle_hash = receipt.get("bundleSha256") if receipt else None
    bundle_version = receipt.get("bundleVersion") if receipt else None
    if operation != "configure":
        from .tooling_assets import load_skill_bundle
        bundle = load_skill_bundle(source_checkout=source_checkout)
        bundle_hash, bundle_version = bundle.sha256, bundle.version
        for asset in bundle.skills:
            relative = f"{asset.name}/SKILL.md"
            target = skills / relative
            if target.parent.exists():
                _require(not target.parent.is_symlink() and target.parent.is_dir(), "skill directory is unsafe")
                _require(not _unowned_skill_contents(target.parent, receipt),
                         f"shared skill contents require manual review: {asset.name}")
            before = _read(target)
            owned = inventory.get(relative)
            _require(before is None or (owned is not None and _digest(before) == owned),
                     f"skill collision or user edit: {relative}")
            after = asset.content.encode("utf-8")
            if before != after:
                changes.append(Change(target, before, after))
            inventory[relative] = _digest(after)
    receipt_after = {"schema": SCHEMA, "host": selection.host, "hostBuild": "pending observation",
                     "scope": selection.scope, "serverName": selection.name,
                     "configPath": str(config), "skillsPath": str(skills), "entry": new_entry.decode(),
                     "bundleVersion": bundle_version, "bundleSha256": bundle_hash, "files": inventory,
                     "skillDirectories": sorted({relative.split("/")[0] for relative in inventory}),
                     "executable": server["command"], "args": server["args"],
                     "sourceRoot": str(selection.source_root), "resultRoot": str(selection.result_root),
                     "runtimeEnabled": selection.enable_runtime, "state": "installed", "residuals": []}
    receipt_before = _read(receipt_path)
    backups = _planned_backups(changes, receipt.get("backups", []) if receipt else [])
    receipt_after["backups"] = backups
    receipt_after["configurationAfterSha256"] = _digest(config_after)
    receipt_after["configurationBeforeSha256"] = (receipt.get("configurationBeforeSha256") if receipt and config_before == config_after
                                                  else _digest(config_before) if config_before is not None else None)
    encoded = _json(receipt_after)
    if receipt_before != encoded:
        changes.append(Change(receipt_path, receipt_before, encoded))
    _require(len({c.path for c in changes}) == len(changes), "transaction destination collision")
    return Transaction(changes, {"operation": operation, "status": "preview", "host": selection.host,
                                "scope": selection.scope, "serverName": selection.name,
                                "server": server, "configPath": str(config), "skillsPath": str(skills),
                                "receipt": str(receipt_path), "runtimeEnabled": selection.enable_runtime,
                                "bundleVersion": bundle_version, "bundleSha256": bundle_hash,
                                "enabledTools": ["analyze-work", "analyze", "prepare"] +
                                (["status", "verify", "execute", "recover"] if selection.enable_runtime else []),
                                "residuals": residuals})


def _atomic(path: Path, value: bytes | None):
    if value is None:
        path.unlink()
        _sync_directory(path.parent)
        return
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.braid-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _sync_directory(path: Path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def apply(transaction: Transaction, *, preview_digest: str,
          fault: Callable[[int, Path], None] | None = None) -> dict:
    """Apply exactly the reviewed preview with rollback and persistent backups."""
    preview = transaction.preview()
    _require(preview_digest == preview["previewDigest"], "selected preview digest does not match")
    for change in transaction.changes:
        _require(_read(change.path) == change.before, "concurrent destination edit; refusing transaction")
    if not transaction.changes:
        return dict(preview, status="unchanged", backups=[])
    # One lock per receipt/config scope; never start hosts, dependency installers or grants.
    lock_root = Path(transaction.summary["configPath"]).parent
    created_dirs = []
    for change in transaction.changes:
        pending = []
        parent = change.path.parent
        while not parent.exists():
            pending.append(parent)
            parent = parent.parent
        for directory in reversed(pending):
            _require(not directory.is_symlink(), "symlink destination parent")
            directory.mkdir(mode=0o700)
            created_dirs.append(directory)
        _check_path(change.path)
    lock = lock_root / ".agent-braid-install.lock"
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError as exc:
        raise InstallationRefused("another transaction holds the scope lock") from exc
    backups = []
    applied = []
    try:
        os.close(descriptor)
        for index, change in enumerate(transaction.changes):
            _require(_read(change.path) == change.before, "destination changed after preview")
            if change.before is not None:
                backup = change.path.parent / f".{change.path.name}.braid-backup-{_digest(change.before)}"
                existing = _read(backup)
                _require(existing is None or existing == change.before, "backup collision")
                if existing is None:
                    descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(change.before)
                        stream.flush()
                        os.fsync(stream.fileno())
                backups.append({"path": str(backup), "sha256": _digest(change.before)})
            if fault:
                fault(index, change.path)
            _require(_read(change.path) == change.before, "destination changed at replacement")
            applied.append(change)
            _atomic(change.path, change.after)
    except BaseException:
        # A third party edit is never overwritten by rollback.
        rollback_errors = []
        for change in reversed(applied):
            try:
                current = _read(change.path)
                if current == change.before:
                    continue  # failing write had no effect
                _require(current == change.after, "rollback destination changed")
                _atomic(change.path, change.before)
            except (InstallationRefused, OSError) as exc:
                rollback_errors.append(type(exc).__name__)
        if rollback_errors:
            raise InstallationRefused("transaction interrupted; rollback has residual changes; inspect backups")
        raise
    finally:
        lock.unlink(missing_ok=True)
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass  # only remove empty directories created by this transaction
    return dict(preview, status="applied", backups=backups)


def doctor(selection: Selection, *, source_checkout: bool = False) -> dict:
    """Separate static readiness from actual host discovery/authentication."""
    checks = {}
    executable = (selection.executable or Path(sys.executable)).absolute()
    checks["executable"] = {"status": "ok" if executable.is_file() and os.access(executable, os.X_OK) else "unavailable",
                            "path": str(executable)}
    checks["python"] = {"status": "ok" if sys.version_info >= (3, 12) else "unavailable", "version": sys.version.split()[0],
                         "domain": "doctor interpreter; selected executable not launched"}
    for distribution in ("agent-braid", "mcp"):
        try:
            version = metadata.version(distribution)
            checks[distribution] = {"status": "ok" if distribution != "mcp" or version == "2.3.0" else "incompatible", "version": version}
        except metadata.PackageNotFoundError:
            checks[distribution] = {"status": "unavailable", "version": None}
    try:
        from .tooling_assets import load_skill_bundle
        bundle = load_skill_bundle(source_checkout=source_checkout)
        asset_record = asset_provenance(source_checkout=source_checkout)
        checks["assets"] = {"status": "ok", "bundleSha256": bundle.sha256, "version": bundle.version,
                            "hostMetadataSha256": asset_record["hostMetadataSha256"],
                            "licenseFiles": asset_record["licenseFiles"]}
    except (ValueError, OSError) as exc:
        checks["assets"] = {"status": "unavailable", "reason": type(exc).__name__}
    try:
        config, _, receipt = selection.paths()
        existing = _read(config)
        if existing is not None:
            _toml_parse(existing) if selection.host == "codex" else _parse_json(existing)
        readable = os.access(selection.source_root, os.R_OK)
        writable = os.access(selection.result_root, os.W_OK)
        checks["roots"] = {"status": "ok" if readable and writable else "unavailable",
                           "sourceReadable": readable, "resultWritable": writable}
        checks["configuration"] = {"status": "pending" if existing is None else "present", "scope": selection.scope,
                                   "path": str(config), "receiptPresent": _read(receipt) is not None}
    except (InstallationRefused, OSError):
        checks["roots"] = {"status": "refused"}
        checks["configuration"] = {"status": "unknown"}
    host_executable = shutil.which("codex" if selection.host == "codex" else "claude")
    checks["host"] = {"status": "present" if host_executable else "unavailable", "executable": host_executable,
                      "version": None, "domain": "PATH resolution only; build observation pending"}
    checks["protocol"] = {"status": "pending", "domain": "stdio discovery requires a separate local probe receipt"}
    checks["schemas"] = {"status": "pending", "domain": "negotiated SDK discovery receipt required"}
    checks["analysis"] = {"status": "pending", "domain": "positive and negative fixture calls required"}
    checks["runtime"] = {"status": "enabled" if selection.enable_runtime else "disabled", "authority": "existing operator grant required"}
    checks["authentication"] = {"status": "pending", "domain": "actual selected host observation required"}
    checks["hostApproval"] = {"status": "pending", "domain": "interactive selected host approval not observed"}
    return {"schema": "agent-braid-doctor/v0.1", "checks": checks,
            "paidSessionStarted": False, "runtimeDispatched": False, "grantIssued": False}


def asset_provenance(*, source_checkout=False) -> dict:
    """Hash versioned installed assets and actual license texts without a host call."""
    from .tooling_assets import load_skill_bundle
    bundle = load_skill_bundle(source_checkout=source_checkout)
    if source_checkout:
        root = Path(__file__).resolve().parents[1]
        base = root / "integrations" / "agent-braid"
        licenses = root / "LICENSES"
    else:
        base = resources.files("agent_braid").joinpath("tooling_assets")
        licenses = base.joinpath("licenses")
    raw = base.joinpath("hosts.json").read_bytes()
    value = _parse_json(raw)
    _require(isinstance(value, dict) and value.get("schema") == "agent-braid-host-assets/v0.1"
             and value.get("hosts") == ["codex", "claude"] and value.get("scopes") == ["user", "project"]
             and value.get("transport") == "stdio" and value.get("sdk") == {"distribution": "mcp", "version": "2.3.0"},
             "host asset metadata is incompatible")
    license_records = {}
    for name in ("AGPL-3.0-only.txt", "CC-BY-SA-4.0.txt"):
        contents = licenses.joinpath(name).read_bytes()
        _require(0 < len(contents) <= MAX_CONFIG, "license text is absent or oversized")
        license_records[name] = {"sha256": _digest(contents), "sizeBytes": len(contents)}
    return dict(bundle.inventory(), hostMetadata=value, hostMetadataSha256=_digest(raw), licenseFiles=license_records)


def environment_inventory() -> dict:
    """Record the complete observed environment, including SDK transitives.

    This is an observation of installed distributions, not a lockfile or an
    assertion that unobserved platforms or different executables match it.
    """
    distributions = []
    for distribution in metadata.distributions():
        value = distribution.metadata
        distributions.append({"name": value.get("Name"), "version": distribution.version,
                              "requires": list(distribution.requires or []),
                              "licenseExpression": value.get("License-Expression"),
                              "licenseMetadata": value.get("License"),
                              "licenseClassifiers": [item for item in value.get_all("Classifier", []) if item.startswith("License ::")],
                              "licenseStatus": "declared" if value.get("License-Expression") or value.get("License") else "unavailable"})
    return {"schema": "agent-braid-environment-inventory/v0.1", "python": sys.version,
            "executable": sys.executable, "domain": "this interpreter's installed distributions, including development-only entries",
            "distributions": sorted(distributions, key=lambda value: (value["name"] or "").lower()),
            "limits": ["Declared license metadata is not a legal compatibility decision.",
                       "No provider session or dependency installation was performed."]}
