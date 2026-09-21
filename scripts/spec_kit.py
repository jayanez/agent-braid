#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Regenerate pinned official adapters in isolation; never invoke an AI agent."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.7"
COMMIT = "fe1d00e3ccaf495880aaf90fb0e17679e82f065b"
AGENTS = {"codex": ".agents", "claude": ".claude"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def render(root, installed, active):
    if importlib.metadata.version("specify-cli") != VERSION:
        raise ValueError("Use the pinned Spec Kit development environment")
    provenance = json.loads(importlib.metadata.distribution("specify-cli").read_text("direct_url.json") or "{}")
    if provenance.get("vcs_info", {}).get("commit_id") != COMMIT:
        raise ValueError("Spec Kit installation does not match the pinned upstream commit")
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.claude import ClaudeIntegration
    from specify_cli.integrations.manifest import IntegrationManifest

    if not installed or set(installed) - AGENTS.keys() or active not in installed:
        raise ValueError("Only Codex and Claude with an installed active integration are supported")
    cli = Path(sys.executable).parent / ("specify.exe" if os.name == "nt" else "specify")
    output = {}
    with tempfile.TemporaryDirectory(prefix="agent-braid-spec-kit-") as temporary:
        project = Path(temporary) / "project"
        project.mkdir()
        # Seed exact bytes before official init, so its constitution seeder is inert.
        memory = project / ".specify/memory/constitution.md"
        memory.parent.mkdir(parents=True)
        memory.write_bytes((root / "CONSTITUTION.md").read_bytes())

        def run(*args):
            result = subprocess.run([str(cli), *args], cwd=project, text=True,
                                    capture_output=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)

        run("init", "--here", "--force", "--non-interactive", "--integration",
            active, "--script", "py", "--ignore-agent-tools")
        for name in installed:
            if name != active:
                run("integration", "install", name, "--script", "py")
        # Exercise active-only refresh explicitly; restore before custom rendering.
        for name in installed:
            run("integration", "use", name)
        run("integration", "use", active)
        state = json.loads((project / ".specify/integration.json").read_text())
        if state["default_integration"] != active:
            raise ValueError("Official integration selection was not restored")
        if memory.read_bytes() != (root / "CONSTITUTION.md").read_bytes():
            raise ValueError("Upstream initialization altered the seeded Constitution")

        overrides = root / ".specify/templates/overrides"
        commands = Path(temporary) / "commands"
        commands.mkdir()
        shared = (overrides / "guardrails.md").read_text()
        for source in sorted(overrides.glob("speckit.*.md")):
            raw = source.read_text()
            closing = raw.index("\n---", 3) + 4
            # Shared gates precede command actions in both official adapters.
            rendered = raw[:closing] + "\n\n" + shared + raw[closing:]
            (commands / source.name.removeprefix("speckit.")).write_text(rendered)
        for name in installed:
            base = {"codex": CodexIntegration, "claude": ClaudeIntegration}[name]

            class ProjectIntegration(base):
                def list_command_templates(self):
                    return sorted(commands.glob("*.md"))

            manifest = IntegrationManifest(name, project, VERSION)
            ProjectIntegration().setup(project, manifest, script_type="py")
            for file in (project / AGENTS[name] / "skills").glob("speckit-*/SKILL.md"):
                output[file.relative_to(project).as_posix()] = file.read_bytes()
            # Stable manifest: timestamp is intentionally not a generated input.
            output[f".specify/integrations/{name}.manifest.json"] = encoded({
                "integration": name, "version": VERSION, "files": manifest.files,
            })
        for folder in ("scripts", "templates"):
            for file in (project / ".specify" / folder).rglob("*"):
                if file.is_file() and "__pycache__" not in file.parts:
                    output[file.relative_to(project).as_posix()] = file.read_bytes()
        for source in overrides.glob("*-template.md"):
            output[f".specify/templates/{source.name}"] = source.read_bytes()
        state["installed_integrations"] = sorted(installed)
        output[".specify/integration.json"] = encoded(state)
        options = json.loads((project / ".specify/init-options.json").read_text())
        output[".specify/init-options.json"] = encoded(options)
        output[".specify/.gitignore"] = (project / ".specify/.gitignore").read_bytes()
        # The bundled delivery workflow is deliberately NOT copied or enabled.
    return output


def generate(root=ROOT, check=False, installed=None, active=None):
    state_path = root / ".specify/integration.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    installed = installed or state.get("installed_integrations", ["codex", "claude"])
    active = active or state.get("default_integration", "codex")
    output = render(root, installed, active)
    overrides = root / ".specify/templates/overrides"
    sources = {p.relative_to(root).as_posix(): sha(p.read_bytes())
               for p in sorted(overrides.rglob("*")) if p.is_file()}
    for relative in ("scripts/spec_kit.py", "requirements-speckit.txt"):
        sources[relative] = sha((root / relative).read_bytes())
    lock = {"version": VERSION, "commit": COMMIT, "sources": sources,
            "outputs": {name: sha(data) for name, data in sorted(output.items())}}
    output[".specify/generation.json"] = encoded(lock)
    changed = []
    for relative, data in sorted(output.items()):
        target = root / relative
        if not target.is_file() or target.read_bytes() != data:
            changed.append(relative)
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    if check and changed:
        raise ValueError("Generated integration drift: " + ", ".join(changed))
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "check"))
    args = parser.parse_args()
    changed = generate(check=args.mode == "check")
    print(f"Spec Kit {args.mode}: {len(changed)} files changed; no agents executed.")
