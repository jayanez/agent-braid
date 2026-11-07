# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T010: the fixed sandbox workspace that every REQ-010 prompt refers to.

``build(path)`` creates a small git repository whose default branch is ``main`` and
a handful of single-commit branches cut from ``main``. The content is deterministic
(fixed identity and dates), so the same call always produces the same commits.

    python -m scripts.spec069_fixture_workspace <empty-directory>
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BASE_BRANCH = "main"

BASE_FILES = {
    "README.md": "# Tidewater\n\nA small command-line tool that reports tide tables.\n\n## Install\n\nRun `npm install`.\n",
    "CHANGELOG.md": "# Changelog\n\n## 0.3.0\n\n- First public release.\n",
    "LICENSE": "MIT License\n",
    "package.json": '{\n  "name": "tidewater",\n  "version": "0.3.0",\n  "license": "MIT"\n}\n',
    "docs/guide.md": "# Guide\n\nStart with `tidewater today`.\n",
    "docs/faq.md": "# FAQ\n\nQ: Which time zone is used?\nA: Local time.\n",
    "docs/api.md": "# API\n\n`GET /tides` returns today's tide table.\n",
    "src/api.py": "def tides(day):\n    return []\n",
    "src/cli.py": "def main(argv):\n    return 0\n",
    "src/db.py": "def connect(url):\n    return None\n",
    "src/utils.py": "def clean(value):\n    return value.strip()\n",
    "src/legacy.py": "def old_format(row):\n    return str(row)\n",
    "config/staging.yaml": "timeout: 30\nregion: eu-west\n",
    "config/production.yaml": "timeout: 60\nregion: us-east\n",
    "scripts/build.sh": "#!/bin/sh\necho build\n",
    "scripts/old_build.sh": "#!/bin/sh\necho old build\n",
    "tests/test_api.py": "def test_tides():\n    assert True\n",
}

# branch -> files changed by its single commit (every branch is cut from ``main``).
BRANCHES = {
    "docs-guide": ["docs/guide.md"],
    "src-api": ["src/api.py"],
    "src-cli": ["src/cli.py"],
    "readme-badge": ["README.md"],
    "readme-intro": ["README.md"],
    "guide-and-api": ["docs/guide.md", "src/api.py"],
    "docs-faq": ["docs/faq.md"],
    "docs-api": ["docs/api.md"],
    "src-db": ["src/db.py"],
    "tests-api": ["tests/test_api.py"],
    "remove-legacy": ["src/legacy.py"],  # deletes the file
}

_ENV = {
    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def _git(root: Path, *args: str) -> None:
    env = {**os.environ, **_ENV}
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


def _write(root: Path, name: str, text: str) -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def build(path: str | Path) -> Path:
    """Create the fixture repository in the empty directory ``path`` and return it."""
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError("fixture target must be an empty directory")
    _git(root, "init", "-q", "-b", BASE_BRANCH)
    for name, text in BASE_FILES.items():
        _write(root, name, text)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "Initial commit")
    for branch, files in BRANCHES.items():
        _git(root, "checkout", "-q", "-b", branch, BASE_BRANCH)
        for name in files:
            if branch == "remove-legacy":
                (root / name).unlink()
            else:
                _write(root, name, BASE_FILES[name] + f"\n<!-- {branch} -->\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", f"Change on {branch}")
    _git(root, "checkout", "-q", BASE_BRANCH)
    return root


if __name__ == "__main__":
    print(build(sys.argv[1]))
