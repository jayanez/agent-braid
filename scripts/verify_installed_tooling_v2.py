# SPDX-License-Identifier: AGPL-3.0-only
"""Installed-package verifier for portable surface ``agent-braid-tooling/v0.2``.

``verify_installed_tooling.py`` stays byte-identical because its SHA-256 is
pinned in frozen evidence; it verifies contract v0.1 (package 0.1.0a1, three
``agent-braid-*`` prompts). This module loads it unchanged and replaces only
the two points that differ in v0.2: the candidate distribution version
(``0.1.0a2``) and the prompt roster (``analyze``, ``plan``, ``evidence`` plus
the deprecated aliases ``agent-braid-analyze``, ``-plan`` and ``-evidence``).
Offline install, relay, bounds and receipt layout are inherited. As in v0.1,
nothing is installed unless --execute-installed is supplied.
"""
from __future__ import annotations

import importlib.util
from email.parser import Parser
from pathlib import Path
import re
import zipfile

_BASE_PATH = Path(__file__).resolve().with_name("verify_installed_tooling.py")
_SPEC = importlib.util.spec_from_file_location("_verify_installed_tooling_v01", _BASE_PATH)
base = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(base)

CANDIDATE_VERSION = "0.1.0a2"
ProbeError = base.ProbeError

_V01_PROMPT_BLOCK = '''        prompts=await client.list_prompts(); prompt_names=sorted(row.name for row in prompts.prompts)
        if prompt_names!=["agent-braid-analyze","agent-braid-evidence","agent-braid-plan"]: raise RuntimeError("prompt roster")
        prompt=await client.get_prompt("agent-braid-evidence")
        if "SHA-256" not in prompt.messages[0].content.text: raise RuntimeError("prompt content")
'''

_V02_PROMPT_BLOCK = '''        prompts=await client.list_prompts(); listed_prompts=list(prompts.prompts); prompt_names=[row.name for row in listed_prompts]
        if prompt_names!=["analyze","plan","evidence","agent-braid-analyze","agent-braid-plan","agent-braid-evidence"]: raise RuntimeError("prompt roster")
        for row in listed_prompts:
            marked=(row.description or "").startswith("[Deprecated alias of")
            if marked!=row.name.startswith("agent-braid-"): raise RuntimeError("deprecation marking")
        prompt=await client.get_prompt("evidence")
        if "SHA-256" not in prompt.messages[0].content.text: raise RuntimeError("prompt content")
        alias=await client.get_prompt("agent-braid-evidence")
        if alias.messages[0].content.text!=prompt.messages[0].content.text: raise RuntimeError("alias text")
        if not (alias.description or "").startswith("Deprecated alias of"): raise RuntimeError("alias description")
'''

_V01_SDK_PROBE_CODE = base._sdk_probe_code


def candidate_metadata(path: Path, expected_sha: str) -> dict[str, str]:
    """The v0.1 checks, with the distribution version pinned to 0.1.0a2."""
    if path.is_symlink() or not path.is_file() or path.suffix != ".whl":
        raise ProbeError("candidate must be a regular wheel file")
    digest = base.sha256_file(path)
    if digest != expected_sha:
        raise ProbeError("candidate wheel digest mismatch")
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise ProbeError("candidate metadata roster invalid")
            metadata = Parser().parsestr(archive.read(names[0]).decode("utf-8"))
    except (OSError, UnicodeError, KeyError, zipfile.BadZipFile) as exc:
        raise ProbeError("candidate metadata unreadable") from exc
    if (metadata.get("Name", "").lower().replace("_", "-") != "agent-braid"
            or metadata.get("Version") != CANDIDATE_VERSION):
        raise ProbeError("candidate distribution identity mismatch")
    extras = {item.lower() for item in metadata.get_all("Provides-Extra", [])}
    optional_sdk = any(re.match(r"\s*mcp\s*==\s*2\.3\.0\b", item, re.I)
                       and "extra" in item.lower() and "tooling" in item.lower()
                       for item in metadata.get_all("Requires-Dist", []))
    if "tooling" not in extras or not optional_sdk:
        raise ProbeError("candidate metadata does not declare the pinned optional tooling extra")
    return {"sha256": digest, "distribution": metadata["Name"], "version": metadata["Version"]}


def sdk_probe_code(*args, **kwargs) -> str:
    """The v0.1 child program with only the prompt roster block replaced."""
    code = _V01_SDK_PROBE_CODE(*args, **kwargs)
    if _V01_PROMPT_BLOCK not in code:
        raise ProbeError("v0.1 prompt probe layout changed; the v0.2 adapter refuses to guess")
    return code.replace(_V01_PROMPT_BLOCK, _V02_PROMPT_BLOCK, 1)


_sdk_probe_code = sdk_probe_code
base.candidate_metadata = candidate_metadata
base._sdk_probe_code = sdk_probe_code


def main(argv: list[str] | None = None) -> int:
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
