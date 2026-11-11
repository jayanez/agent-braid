# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T010 versioned, opt-in, read-only advisory CLI (``harness-advisory``).

Invocation: ``python -m agent_braid.harness_advisory <command>``. It is deliberately not a
top-level ``agent-braid`` subcommand yet: ``agent_braid/cli.py`` top-level help is pinned by the
laboratory CLI tests, so wiring it there is a separate reviewed change.
Contract: specs/050-braid-harness-adaptation/contracts/advisory.md
(``braid-harness-advisory/v0.1``). Every command is advice over records the caller already
holds: it reads bounded regular files inside one explicitly bound workspace, starts no process,
opens no network connection, writes nothing and issues no grant. Every output carries
``executionAuthorization: false`` and ``advisory: true``. Refusals are one JSON object with a
fixed reason code on stdout and exit 2; argument-usage errors also exit 2 with usage text on
stderr only. The existing ``harness`` laboratory command, the plugin and the MCP tool surface are
not modified; a new execution surface needs a separate explicit adoption.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from .harness_cli import CliRefusal, _evidence, _file_diff, _hash, _read, _registry_status
from .harness_components import (CLASSES, HOST_SUPPORT, ROOTS, ProfileError, derive_admission,
                                 parse_profile, verify_profile)
from .harness_promotion import PromotionError

CONTRACT = "braid-harness-advisory/v0.1"
VERSIONS = ("v0.1",)
HELP = "opt-in read-only advisory views of harness profiles (no execution authority)"
COMMANDS = ("capabilities", "profile-inventory", "profile-diff", "status", "evidence")
_ENVELOPE = {"contract": CONTRACT, "executionAuthorization": False, "advisory": True}
_REASON = re.compile(r"[a-z][a-z-]{0,47}\Z")
_DIFFERENCE_KEYS = ("version", "componentClass", "host", "effectClass", "admission", "settings",
                    "provenance", "parentSha256", "deleted")
_PROVIDER_LIMITATIONS = [
    "claude: build 2.1.292 observed, adapter and native wiring tested with doubles only; no "
    "class is qualified and no native unit has run",
    "codex: not installed; refused",
    "hook, plugin and delegated-role schemas per host build are not inventoried, so classes "
    "C6 to C8 stay blocked",
    "a matched --sha256 binds bytes, not authenticity, rights or containment",
    "advice is not product acceptance, qualification or activation",
]
_COMMAND_HELP = {
    "capabilities": "list contract versions, component classes, host support and limits",
    "profile-inventory": "show one component profile's files, admission and host rows",
    "profile-diff": "file-level and metadata diff between two component profiles",
    "status": "report a profile registry's active, pending and audit state",
    "evidence": "inventory a spec directory's evidence files against its tasks",
}


def bound_reason(value) -> str:
    """A fixed-shape reason code; anything else collapses to ``refused``."""
    return value if type(value) is str and _REASON.fullmatch(value) else "refused"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agent_braid.harness_advisory", description=HELP)
    commands = parser.add_subparsers(dest="advisory_command", required=True)
    for name in COMMANDS:
        child = commands.add_parser(name, help=_COMMAND_HELP[name])
        child.add_argument("--workspace", required=True, type=Path,
                           help="existing directory every input must resolve inside")
        child.add_argument("--contract-version", default=VERSIONS[-1],
                           help="advisory contract version the caller expects")
        if name == "profile-inventory":
            child.add_argument("--profile", required=True, type=Path)
            child.add_argument("--sha256", help="trusted full profile SHA-256")
        if name == "profile-diff":
            child.add_argument("--base", required=True, type=Path)
            child.add_argument("--candidate", required=True, type=Path)
        if name == "status":
            child.add_argument("--registry", required=True, type=Path)
        if name == "evidence":
            child.add_argument("--spec-dir", required=True, type=Path)
    return parser


def _workspace(path: Path) -> Path:
    try:
        resolved = Path(os.path.realpath(path, strict=True))
    except (OSError, ValueError):
        raise CliRefusal("workspace-invalid") from None
    if not resolved.is_dir():
        raise CliRefusal("workspace-invalid")
    return resolved


def _inside(workspace: Path, path: Path) -> Path:
    """Resolved ``path`` (links followed) if it lies inside ``workspace``; else refuse."""
    try:
        resolved = Path(os.path.realpath(path))
    except (OSError, ValueError):
        raise CliRefusal("input-unreadable") from None
    if resolved != workspace and workspace not in resolved.parents:
        raise CliRefusal("outside-workspace")
    return resolved


def _profile(workspace: Path, path: Path, trusted: str | None = None):
    raw = _read(_inside(workspace, path))
    if trusted is None:
        return parse_profile(raw), "unverified"
    return verify_profile(raw, expected_sha256=_hash(trusted)), "hash-matched"


def _files(profile) -> list[dict]:
    return [{"path": r["path"], "sha256": r["sha256"], "sizeBytes": r["sizeBytes"]}
            for r in profile.to_dict()["inventory"]]


def _capabilities() -> dict:
    classes = []
    for name in CLASSES:
        state, blocker = derive_admission(name, "E0")
        classes.append({"class": name, "root": ROOTS[name], "admission": state, "blocker": blocker})
    return {"supportedContractVersions": list(VERSIONS), "commands": list(COMMANDS),
            "componentClasses": classes,
            "hosts": {host: dict(row) for host, row in HOST_SUPPORT.items()},
            "effects": "none", "pluginOrMcpSurface": "unchanged",
            "providerLimitations": list(_PROVIDER_LIMITATIONS)}


def _inventory(workspace: Path, args) -> dict:
    profile, authenticity = _profile(workspace, args.profile, args.sha256)
    data = profile.to_dict()
    return {"sha256": profile.sha256, "authenticity": authenticity, "format": data["format"],
            "version": data["version"], "componentClass": data["componentClass"],
            "host": data["host"], "effectClass": data["effectClass"],
            "admission": data["admission"], "hostSupport": data["hostSupport"],
            "parentSha256": data["parentSha256"], "files": _files(profile),
            "deleted": data["deleted"], "limits": list(_PROVIDER_LIMITATIONS)}


def _diff(workspace: Path, args) -> dict:
    base, _ = _profile(workspace, args.base)
    candidate, _ = _profile(workspace, args.candidate)
    old, new = base.to_dict(), candidate.to_dict()
    return {"baseSha256": base.sha256, "candidateSha256": candidate.sha256,
            "identical": base.sha256 == candidate.sha256,
            "authenticity": "unverified", "files": _file_diff(old["inventory"], new["inventory"]),
            "changedFields": [k for k in _DIFFERENCE_KEYS if old[k] != new[k]]}


def _dispatch(args, workspace: Path) -> dict:
    command = args.advisory_command
    if command == "capabilities":
        return _capabilities()
    if command == "profile-inventory":
        return _inventory(workspace, args)
    if command == "profile-diff":
        return _diff(workspace, args)
    if command == "status":
        return _registry_status(_inside(workspace, args.registry))
    return _evidence(_inside(workspace, args.spec_dir))


def _emit(value: dict) -> None:
    print(json.dumps(value, sort_keys=True, allow_nan=False))


def run(args) -> int:
    envelope = _ENVELOPE
    try:
        if args.contract_version not in VERSIONS:
            raise CliRefusal("unsupported-version")
        workspace = _workspace(args.workspace)
        result = _dispatch(args, workspace)
    except (CliRefusal, ProfileError, PromotionError) as exc:
        _emit({**envelope, "status": "refused", "reason": bound_reason(exc.reason)})
        return 2
    _emit({**envelope, "status": "ok", "result": result,
           "workspace": {"bound": True, "id": sha256(str(workspace).encode()).hexdigest()}})
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
