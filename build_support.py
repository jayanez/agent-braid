# SPDX-License-Identifier: AGPL-3.0-only
"""Copy canonical product assets into installed package resources at build time."""
from pathlib import Path
from shutil import copyfile

from setuptools.command.build_py import build_py

# The first-party activity-viewer web bundle (SPEC-061 T043) with its vendored files, manifest and licence.
VIEW_WEB_SOURCE = Path(__file__).resolve().parent / "integrations" / "agent-braid-view" / "web"


def _view_web_files(source):
    if not (source / "index.html").is_file():
        raise FileNotFoundError(f"the activity viewer web bundle is missing: {source}")
    return sorted(path for path in source.rglob("*") if path.is_file() and not path.is_symlink())


class ToolingBuildPy(build_py):
    def _asset_mapping(self):
        root = Path(__file__).resolve().parent
        source = root / "integrations" / "agent-braid"
        destination = Path(self.build_lib) / "agent_braid" / "tooling_assets"
        mapping = {}
        names = ["analyze", "plan", "execute", "recover", "evidence"]
        for name in names:
            relative = Path("skills") / f"agent-braid-{name}" / "SKILL.md"
            mapping[str(destination / relative)] = str(source / relative)
        mapping[str(destination / "hosts.json")] = str(source / "hosts.json")
        for name in ("fixture-inventory.json", "prompts.json"):
            mapping[str(destination / "fixtures" / name)] = str(root / "examples" / "tooling" / name)
        for name in ("AGPL-3.0-only.txt", "CC-BY-SA-4.0.txt"):
            mapping[str(destination / "licenses" / name)] = str(root / "LICENSES" / name)
        for name in ("NOTICE", "TRADEMARKS.md"):
            mapping[str(destination / name)] = str(root / name)
        view = Path(self.build_lib) / "agent_braid" / "view_assets" / "web"
        for path in _view_web_files(VIEW_WEB_SOURCE):
            mapping[str(view / path.relative_to(VIEW_WEB_SOURCE))] = str(path)
        return mapping

    def run(self):
        super().run()
        for output, source in self._asset_mapping().items():
            target = Path(output)
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(source, target)

    def get_outputs(self, include_bytecode=1):
        return sorted(set(super().get_outputs(include_bytecode)) | set(self._asset_mapping()))

    def get_output_mapping(self):
        return {**super().get_output_mapping(), **self._asset_mapping()}
