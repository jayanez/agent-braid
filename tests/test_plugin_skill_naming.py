# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-054 T002/T004: packaged plugin names and skill substitutions."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from agent_braid.plugin_package import inventory, verify_package
from agent_braid.tooling_assets import load_skill_bundle
from scripts.build_native_plugin import (PREFIXED_TOKEN, ROOT, SKILL_SUBSTITUTIONS, check_package_names,
                                         package_skill)

NAME = 'agent-braid'
POLICY_NAMES = {'analyze', 'plan', 'evidence', 'execute', 'recover', 'setup'}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def make_staging(root):
    """Minimal marketplace tree using the real packaging transform; no runtime downloads."""
    plugin = root / 'plugins' / NAME
    write(plugin / 'plugin.json', {'name': NAME})
    write(plugin / '.claude-plugin/plugin.json', {'name': NAME})
    write(plugin / 'mcp.json', {'mcpServers': {NAME: {}}})
    write(plugin / '.mcp.json', {'mcpServers': {NAME: {}}})
    write(root / '.agents/plugins/marketplace.json', {'name': NAME, 'plugins': [{'name': NAME}]})
    write(root / '.claude-plugin/marketplace.json', {'name': NAME, 'plugins': [{'name': NAME}]})
    for skill in load_skill_bundle(source_checkout=True).skills:
        target = plugin / 'skills' / SKILL_SUBSTITUTIONS[skill.name] / 'SKILL.md'
        target.parent.mkdir(parents=True)
        target.write_text(package_skill(skill.content))
    shutil.copytree(ROOT / 'integrations/agent-braid/plugin/setup', plugin / 'skills/setup')
    return plugin


class SkillNamingTests(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        self.root = Path(self._directory.name)
        self.plugin = make_staging(self.root)

    def test_packaged_names_directories_and_pattern(self):
        check_package_names(self.root)
        directories = {x.name for x in (self.plugin / 'skills').iterdir()}
        self.assertEqual(directories, POLICY_NAMES)
        for directory in directories:
            text = (self.plugin / 'skills' / directory / 'SKILL.md').read_text()
            name = re.search(r'^name: (\S+)$', text, re.M).group(1)
            self.assertEqual(name, directory)
            self.assertRegex(name, r'^[a-z0-9]+(-[a-z0-9]+)*$')
            self.assertLessEqual(len(name), 64)
            self.assertIsNone(PREFIXED_TOKEN.search(text))

    def test_bodies_equal_canonical_after_declared_substitutions_only(self):
        for skill in load_skill_bundle(source_checkout=True).skills:
            packaged = (self.plugin / 'skills' / SKILL_SUBSTITUTIONS[skill.name] / 'SKILL.md').read_text()
            expected = skill.content
            for old, new in SKILL_SUBSTITUTIONS.items():
                expected = expected.replace(old, new)
            self.assertEqual(packaged, expected)
            self.assertEqual(hashlib.sha256(skill.content.encode()).hexdigest(), skill.sha256)
        analyze = (self.plugin / 'skills/analyze/SKILL.md').read_text()
        self.assertIn('use `plan`', analyze)

    def test_inventory_verification_ignores_provenance_keys(self):
        write(self.plugin / 'provenance.json', {'skillNaming': {'substitutions': SKILL_SUBSTITUTIONS}})
        write(self.plugin / 'package-inventory.json', {
            'schema': 'agent-braid-plugin-package/v1', 'version': '0.0.0', 'files': inventory(self.plugin)})
        verify_package(self.plugin)

    def test_unmapped_prefixed_reference_fails(self):
        path = self.plugin / 'skills/plan/SKILL.md'
        path.write_text(path.read_text() + '\nSee agent-braid-analyze.\n')
        with self.assertRaisesRegex(ValueError, 'prefixed skill token'):
            check_package_names(self.root)

    def test_unsubstituted_canonical_skill_fails(self):
        skill = next(x for x in load_skill_bundle(source_checkout=True).skills if x.name == 'agent-braid-plan')
        (self.plugin / 'skills/plan/SKILL.md').write_text(skill.content)
        with self.assertRaisesRegex(ValueError, 'frontmatter name differs'):
            check_package_names(self.root)

    def test_tampered_server_key_fails(self):
        for filename in ('mcp.json', '.mcp.json'):
            with self.subTest(filename):
                path = self.plugin / filename
                original = path.read_text()
                write(path, {'mcpServers': {'agent_braid': {}}})
                with self.assertRaisesRegex(ValueError, 'server key'):
                    check_package_names(self.root)
                path.write_text(original)
        check_package_names(self.root)

    def test_tampered_plugin_and_marketplace_names_fail(self):
        for relative in ('plugins/agent-braid/plugin.json', 'plugins/agent-braid/.claude-plugin/plugin.json',
                         '.agents/plugins/marketplace.json', '.claude-plugin/marketplace.json'):
            with self.subTest(relative):
                path = self.root / relative
                original = path.read_text()
                write(path, {'name': 'agent-braid-plugin', 'plugins': [{'name': 'agent-braid'}]})
                with self.assertRaises(ValueError):
                    check_package_names(self.root)
                path.write_text(original)

    def test_renamed_directory_fails(self):
        (self.plugin / 'skills/plan').rename(self.plugin / 'skills/planning')
        with self.assertRaisesRegex(ValueError, 'skill directories'):
            check_package_names(self.root)

    def test_package_skill_rejects_unknown_canonical_name(self):
        with self.assertRaises(ValueError):
            package_skill('---\nname: agent-braid-other\n---\nbody\n')


if __name__ == '__main__':
    unittest.main()
