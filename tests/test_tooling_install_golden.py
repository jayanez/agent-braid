# SPDX-License-Identifier: AGPL-3.0-only
"""Golden controls: Codex and Claude lifecycle bytes must not change (SPEC-068 T007).

The golden file was captured from the implementation before the OpenCode profile
was added. Paths are normalized to ``<ROOT>`` and content digests are masked
because they depend on the temporary root; lengths and byte ranges are kept by
using a root of constant length.
"""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import tooling_assets
from agent_braid.cli import main
from agent_braid.tooling_install import InstallationRefused, Selection, apply, doctor, plan

GOLDEN = Path(__file__).parent / "fixtures" / "tooling_install_golden.json"
ROOT_LENGTH = 96
HEX = re.compile(r"[a-f0-9]{64}")


def _bundle():
    skills = []
    for name in tooling_assets.SKILL_NAMES:
        content = f"---\nname: {name}\n---\nGolden fixture skill {name}.\n"
        skills.append(tooling_assets.SkillAsset(name, "d", "CC-BY-SA-4.0", content,
                                                hashlib.sha256(content.encode()).hexdigest(), len(content)))
    return tooling_assets.SkillBundle("0.0.0-golden", tuple(skills), "0" * 64)


class Fixture:
    def __init__(self, host):
        self.host = host
        base = Path(tempfile.mkdtemp()).resolve()
        self.base = base
        pad = "r" * (ROOT_LENGTH - len(str(base)) - 1)
        self.root = base / pad
        self.root.mkdir()
        self.source = self.root / "src"
        self.results = self.root / "res"
        self.source.mkdir()
        self.results.mkdir()
        self.destination = self.root / "dest"
        self.python = self.root / "python"
        self.python.write_text("#!/bin/sh\n")
        self.python.chmod(0o755)
        self.selection = Selection(host=host, scope="user", source_root=self.source, result_root=self.results,
                                   executable=self.python, destination=self.destination)

    def norm(self, value):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False) if not isinstance(value, str) else value
        return HEX.sub("<sha>", text.replace(str(self.root), "<ROOT>"))

    def plan(self, operation="install", selection=None):
        return plan(selection or self.selection, operation=operation, source_checkout=False)

    def apply(self, transaction):
        return apply(transaction, preview_digest=transaction.preview()["previewDigest"])

    def read(self, path):
        return self.norm(path.read_bytes().decode()) if path.exists() else None


def _scenario(host):
    fx = Fixture(host)
    out = {}
    with patch("agent_braid.tooling_assets.load_skill_bundle", lambda **_: _bundle()), \
            patch("agent_braid.tooling_install.shutil.which", lambda _: None):
        config, skills, receipt = fx.selection.paths()
        t = fx.plan()
        out["preview"] = fx.norm(t.preview())
        out["applied"] = fx.norm({k: v for k, v in fx.apply(t).items() if k != "backups"})
        out["config"] = fx.read(config)
        out["receipt"] = fx.read(receipt)
        out["skills"] = sorted(str(p.relative_to(skills)) for p in skills.rglob("*") if p.is_file())
        out["repeat"] = [fx.plan(op).changes == [] for op in ("install", "update")]
        d = doctor(fx.selection)
        out["doctor"] = fx.norm({k: d["checks"][k] for k in ("configuration", "telemetry", "host", "protocol")})
        up = fx.plan("update")
        out["update"] = fx.norm(up.preview())
        # modified owned entry
        original = config.read_bytes()
        marker = b'"command"' if host == "claude" else b"command = "
        config.write_bytes(original.replace(marker, b'"x": 1,\n' + marker if host == "claude" else b"x = 1\n" + marker, 1))
        try:
            fx.plan("update")
        except InstallationRefused as exc:
            out["modified"] = fx.norm({"message": str(exc), "diagnostic": exc.diagnostic})
        config.write_bytes(original)
        # concurrent drift after preview
        t = fx.plan("uninstall")
        config.write_bytes(original + (b"\n" if host == "claude" else b"# drift\n"))
        try:
            fx.apply(t)
        except InstallationRefused as exc:
            out["drift"] = fx.norm({"message": str(exc), "diagnostic": exc.diagnostic})
        config.write_bytes(original)
        # modified skill
        target = skills / "agent-braid-plan" / "SKILL.md"
        saved = target.read_bytes()
        target.write_bytes(b"user edit")
        try:
            fx.plan("update")
        except InstallationRefused as exc:
            out["skillEdit"] = fx.norm({"message": str(exc), "diagnostic": exc.diagnostic})
        target.write_bytes(saved)
        t = fx.plan("uninstall")
        out["uninstallPreview"] = fx.norm(t.preview())
        fx.apply(t)
        out["configAfterUninstall"] = fx.read(config)
        out["receiptAfterUninstall"] = fx.read(receipt)
        out["skillsAfterUninstall"] = sorted(str(p.relative_to(skills)) for p in skills.rglob("*") if p.is_file())
        # unowned collision through the CLI refusal record
        other = Fixture(host)
        oc, _, _ = other.selection.paths()
        oc.parent.mkdir(parents=True)
        oc.write_text('{"mcpServers": {"agent-braid": {"command": "x"}}}\n' if host == "claude"
                      else '[mcp_servers.agent-braid]\ncommand = "x"\n')
        argv = ["tooling", "install", "--host", host, "--scope", "user", "--source-root", str(other.source),
                "--result-root", str(other.results), "--executable", str(other.python),
                "--destination", str(other.destination)]
        stderr, stdout = io.StringIO(), io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(stdout):
            code = main(argv)
        out["cliCollision"] = [code, other.norm(stderr.getvalue()), other.norm(stdout.getvalue())]
    return out


class GoldenTests(unittest.TestCase):
    maxDiff = None

    def test_codex_and_claude_bytes_are_unchanged(self):
        actual = {host: _scenario(host) for host in ("codex", "claude")}
        if os.environ.get("AGENT_BRAID_UPDATE_GOLDEN") == "1":
            GOLDEN.write_text(json.dumps(actual, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        expected = json.loads(GOLDEN.read_text())
        self.assertEqual(json.loads(json.dumps(actual)), expected)


if __name__ == "__main__":
    unittest.main()
