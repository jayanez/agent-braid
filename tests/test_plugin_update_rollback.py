# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-054 T006: alpha.3 -> alpha.4 update and rollback leave user state untouched.

Owned fixtures only: the alpha.3 package is assembled-equivalent (prefixed skills) and the
alpha.4 package uses the real packaging transform; no runtime download, host or network.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from agent_braid.plugin_package import inventory, verify_package
from agent_braid.plugin_registry import apply, load, plan_setup
from agent_braid.tooling_assets import load_skill_bundle
from scripts.build_native_plugin import VERSION, check_package_names
from tests.test_plugin_skill_naming import NAME, make_staging, write


def state_digest(home):
    """SHA-256 of every registry and result file, keyed by relative path."""
    files = {}
    for path in sorted(Path(home).rglob('*')):
        if path.is_file():
            files[path.relative_to(home).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def seal(plugin, version):
    write(plugin / 'package-inventory.json', {
        'schema': 'agent-braid-plugin-package/v1', 'version': version, 'files': inventory(plugin)})
    verify_package(plugin)


def make_alpha3(root):
    """Prefixed-skill package as published in alpha.3 (canonical names, no substitution)."""
    plugin = root / 'plugins' / NAME
    write(plugin / 'plugin.json', {'name': NAME, 'version': '0.1.0-alpha.3'})
    for skill in load_skill_bundle(source_checkout=True).skills:
        target = plugin / 'skills' / skill.name / 'SKILL.md'
        target.parent.mkdir(parents=True)
        target.write_text(skill.content)
    seal(plugin, '0.1.0-alpha.3')
    return plugin


class UpdateRollbackTests(unittest.TestCase):
    def test_alpha4_update_and_alpha3_restore_keep_registry_and_results_byte_identical(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw).resolve()
            repo = base / 'project'
            repo.mkdir()
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            home = base / 'AgentBraid'
            preview = plan_setup(home, [repo])
            apply(home, preview, preview['previewDigest'])
            workspace = load(home)['workspaces'][0]
            result = Path(workspace['resultRoot']) / 'report.json'
            result.write_text('{"kept": true}\n')
            registry = home / 'registry.json'
            self.assertEqual(json.loads(registry.read_text())['schema'], 'agent-braid-plugin-registry/v0.2')
            before = state_digest(home)
            self.assertIn('registry.json', before)

            installed = base / 'cache' / NAME
            alpha3 = make_alpha3(base / 'alpha3')
            shutil.copytree(alpha3, installed)
            verify_package(installed)
            alpha3_inventory = inventory(installed)
            self.assertEqual(state_digest(home), before)

            # Update: replace the installed package files with the alpha.4 candidate.
            staging = base / 'alpha4'
            alpha4 = make_staging(staging)
            check_package_names(staging)
            seal(alpha4, VERSION)
            shutil.rmtree(installed)
            shutil.copytree(alpha4, installed)
            verify_package(installed)
            self.assertEqual(VERSION, '0.1.0-alpha.5')
            self.assertEqual({x.name for x in (installed / 'skills').iterdir()},
                             {'analyze', 'plan', 'evidence', 'execute', 'recover', 'setup'})
            self.assertEqual(state_digest(home), before)
            self.assertEqual(load(home)['workspaces'][0], workspace)

            # Rollback: restore the alpha.3 files; registry v0.2 is accepted unchanged.
            shutil.rmtree(installed)
            shutil.copytree(alpha3, installed)
            verify_package(installed)
            self.assertEqual(inventory(installed), alpha3_inventory)
            self.assertEqual(state_digest(home), before)
            self.assertEqual(result.read_text(), '{"kept": true}\n')


if __name__ == '__main__':
    unittest.main()
