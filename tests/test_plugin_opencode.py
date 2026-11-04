# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-068 T005: read-only OpenCode collision diagnosis in `plugin doctor --host opencode`."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from agent_braid import plugin_opencode
from agent_braid.plugin_mcp import PluginRouter

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = '/cache/plugins/agent-braid'
OWN_SERVER = {'type': 'local', 'command': [f'{PLUGIN_ROOT}/launch', 'plugin', 'serve', '--plugin-root', PLUGIN_ROOT],
              'codemode': False, 'protocol': 'legacy'}


def skill(directory, skill_id):
    path = Path(directory) / skill_id / 'SKILL.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'---\nname: {skill_id}\n---\nbody\n')
    return path


class OpenCodeDoctorTests(unittest.TestCase):
    def setUp(self):
        # Skill discovery walks to the filesystem root: real ancestors of the temp dir are unguarded.
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.home = self.base / 'home'
        self.project = self.base / 'proj'
        (self.project / '.git').mkdir(parents=True)
        self.home.mkdir()
        self.state = self.base / 'state'
        self.env = {'HOME': str(self.home), 'XDG_CONFIG_HOME': ''}
        patch = mock.patch.dict(os.environ, self.env)
        patch.start()
        self.addCleanup(patch.stop)
        self.xdg = self.home / '.config' / 'opencode'

    def diagnose(self, **kwargs):
        return plugin_opencode.diagnose(self.project, **kwargs)

    def codes(self, report):
        return [finding['code'] for finding in report['findings']]

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if isinstance(text, str) else json.dumps(text))
        return path

    def test_clean_tree_has_no_findings(self):
        report = self.diagnose()
        self.assertEqual(report['findings'], [])
        self.assertTrue(report['readOnly'])

    def test_project_opencode_skill_shadowing_analyze_names_the_winner(self):
        low = skill(self.home / '.claude' / 'skills', 'analyze')
        high = skill(self.project / '.opencode' / 'skills', 'analyze')
        finding, = self.diagnose()['findings']
        self.assertEqual(finding['code'], 'collision')
        self.assertEqual(finding['skillId'], 'analyze')
        self.assertEqual(finding['winner'], {'source': 'project-opencode', 'path': str(high)})
        self.assertEqual([d['path'] for d in finding['definitions']], [str(low), str(high)])

    def test_documented_order_between_home_locations_and_ancestors(self):
        skill(self.home / '.claude' / 'skills', 'execute')
        agents = skill(self.home / '.agents' / 'skills', 'execute')
        self.assertEqual(self.diagnose()['findings'][0]['winner']['path'], str(agents))
        nested = self.project / 'sub'
        near = skill(nested / '.claude' / 'skills', 'plan')
        skill(self.project / '.claude' / 'skills', 'plan')
        finding, = (f for f in plugin_opencode.diagnose(nested)['findings'] if f['skillId'] == 'plan')
        self.assertEqual((finding['skillId'], finding['winner']['path']), ('plan', str(near)))

    def test_xdg_config_home_is_honoured(self):
        custom = self.base / 'xdg'
        with mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': str(custom)}):
            path = skill(custom / 'opencode' / 'skills', 'recover')
            skill(self.xdg / 'skills', 'setup')
            finding, = self.diagnose()['findings']
        self.assertEqual((finding['skillId'], finding['winner']['path']), ('recover', str(path)))

    def test_explicit_skills_entry_beats_every_discovered_skill(self):
        skill(self.project / '.opencode' / 'skills', 'analyze')
        explicit = skill(self.base / 'shared', 'analyze')
        self.write(self.xdg / 'opencode.json', {'skills': {'paths': [str(self.base / 'shared')]}})
        finding, = self.diagnose()['findings']
        self.assertEqual(finding['winner'], {'source': 'config-skills', 'path': str(explicit)})

    def test_explicit_skills_as_list_in_jsonc_with_comments_and_trailing_commas(self):
        explicit = skill(self.base / 'shared', 'evidence')
        self.write(self.project / 'opencode.jsonc',
                   '// comment\n{"skills": [\n"%s", /* more */\n],}\n' % (self.base / 'shared'))
        finding, = self.diagnose()['findings']
        self.assertEqual(finding['winner']['path'], str(explicit))

    def test_prefixed_legacy_skills_are_duplicate_guidance_not_collision(self):
        legacy = skill(self.home / '.claude' / 'skills', 'agent-braid-analyze')
        skill(self.home / '.agents' / 'skills', 'agent-braid-plan')
        skill(self.home / '.agents' / 'skills', 'unrelated')
        finding, = self.diagnose()['findings']
        self.assertEqual(finding['code'], 'duplicate-guidance')
        self.assertIn(str(legacy), [d['path'] for d in finding['definitions']])
        self.assertEqual(sorted(d['skillId'] for d in finding['definitions']), ['agent-braid-analyze', 'agent-braid-plan'])

    def test_foreign_server_entry_is_a_server_collision(self):
        config = self.write(self.xdg / 'opencode.json', {'mcp': {'agent-braid': {
            'type': 'local', 'command': ['agent-braid', 'plugin', 'serve'], 'codemode': False, 'protocol': 'legacy'}}})
        finding, = self.diagnose()['findings']
        self.assertEqual((finding['code'], finding['configFile']), ('server-collision', str(config)))
        self.assertEqual(finding['differingFields'], ['command'])

    def test_plugin_own_value_is_not_a_collision_and_other_servers_are_ignored(self):
        self.write(self.xdg / 'opencode.json', {'mcp': {'agent-braid': OWN_SERVER, 'other': {'type': 'remote'}}})
        self.assertEqual(self.diagnose()['findings'], [])
        self.assertEqual(self.diagnose(plugin_root=Path(PLUGIN_ROOT))['findings'], [])
        other = self.diagnose(plugin_root=Path('/elsewhere'))['findings']
        self.assertEqual(self.codes({'findings': other}), ['server-collision'])

    def test_last_config_file_wins_for_the_server_entry(self):
        foreign = {'type': 'remote', 'url': 'https://example.invalid'}
        self.write(self.xdg / 'opencode.json', {'mcp': {'agent-braid': foreign}})
        self.write(self.project / '.opencode' / 'opencode.jsonc', {'mcp': {'agent-braid': OWN_SERVER}})
        self.assertEqual(self.diagnose()['findings'], [])

    def test_json_and_jsonc_together_are_read_and_flagged_ambiguous(self):
        skill(self.base / 'a', 'plan')
        skill(self.base / 'b', 'plan')
        self.write(self.xdg / 'opencode.json', {'skills': [str(self.base / 'a')]})
        self.write(self.xdg / 'opencode.jsonc', '{"skills": ["%s"]}' % (self.base / 'b'))
        report = self.diagnose()
        self.assertEqual([w['code'] for w in report['warnings']], ['ambiguous-configuration'])
        self.assertEqual(report['findings'][0]['winner']['path'], str(self.base / 'b' / 'plan' / 'SKILL.md'))

    def test_invalid_config_is_reported_and_does_not_crash(self):
        for name, content in (('opencode.json', '{"mcp": '), ('opencode.jsonc', '[1]')):
            self.write(self.xdg / name, content)
        (self.project / 'opencode.json').write_bytes(b'\xff')
        report = self.diagnose()
        self.assertEqual([c['status'] for c in report['configFiles']], ['invalid'] * 3)
        self.assertEqual(report['findings'], [])

    def test_no_project_scans_only_global_locations(self):
        skill(self.project / '.opencode' / 'skills', 'analyze')
        skill(self.home / '.agents' / 'skills', 'setup')
        report = plugin_opencode.diagnose(None)
        self.assertEqual([f['skillId'] for f in report['findings']], ['setup'])
        self.assertIsNone(report['project'])

    def test_scan_writes_nothing(self):
        skill(self.project / '.opencode' / 'skills', 'analyze')
        self.write(self.xdg / 'opencode.json', {'mcp': {'agent-braid': {}}})
        before = sorted((str(p), p.read_bytes()) for p in self.base.rglob('*') if p.is_file())
        self.diagnose()
        self.assertEqual(sorted((str(p), p.read_bytes()) for p in self.base.rglob('*') if p.is_file()), before)

    def test_scan_cannot_write_spawn_or_connect(self):
        import builtins, socket
        skill(self.project / '.opencode' / 'skills', 'analyze')
        self.write(self.xdg / 'opencode.json', {'mcp': {'agent-braid': {}}})
        real_open = builtins.open
        def guarded(file, mode='r', *a, **k):
            self.assertFalse(set(mode) & set('wax+'), mode)
            return real_open(file, mode, *a, **k)
        boom = mock.Mock(side_effect=AssertionError('forbidden'))
        with mock.patch('builtins.open', guarded), mock.patch.object(socket, 'socket', boom), \
                mock.patch.object(subprocess, 'Popen', boom), mock.patch.object(Path, 'write_text', boom), \
                mock.patch.object(Path, 'write_bytes', boom), mock.patch.object(Path, 'mkdir', boom), \
                mock.patch.object(os, 'remove', boom), mock.patch.object(os, 'rename', boom):
            report = self.diagnose()
        self.assertEqual(self.codes(report), ['collision', 'server-collision'])
        self.assertNotIn('grant', json.dumps(report).lower())

    def test_explicit_entry_equal_to_a_discovered_directory_counts_once(self):
        directory = self.project / '.opencode' / 'skills'
        skill(directory, 'analyze')
        self.write(self.xdg / 'opencode.json', {'skills': [str(directory)]})
        self.assertEqual(len(self.diagnose()['findings'][0]['definitions']), 1)

    def test_bad_skills_entries_and_missing_project_do_not_crash(self):
        self.write(self.xdg / 'opencode.json', {'skills': [1, None, '', '~nosuchuser_x/y', 'a\x00b', {}]})
        self.assertEqual(self.diagnose()['findings'], [])
        self.write(self.xdg / 'opencode.jsonc', {'skills': 'text'})
        self.assertEqual(plugin_opencode.diagnose(self.base / 'missing')['findings'], [])

    def test_without_git_root_ancestor_configuration_is_read(self):
        outer = self.base / 'nogit'
        (outer / 'sub').mkdir(parents=True)
        self.write(outer / 'opencode.json', {'mcp': {'agent-braid': {'type': 'remote'}}})
        finding, = plugin_opencode.diagnose(outer / 'sub')['findings']
        self.assertEqual(finding['code'], 'server-collision')

    def test_skill_above_the_git_root_is_a_collision_and_nearer_wins(self):
        # T010 row 14: the host loads skills from directories above the project's Git root.
        far = skill(self.base / '.agents' / 'skills', 'plan')
        mid = skill(self.base / '.claude' / 'skills', 'plan')
        finding, = self.diagnose()['findings']
        self.assertEqual(finding['code'], 'collision')
        self.assertEqual(finding['winner'], {'source': 'project-agents', 'path': str(far)})
        self.assertEqual([d['path'] for d in finding['definitions']], [str(mid), str(far)])
        near = skill(self.project / '.agents' / 'skills', 'plan')
        finding, = self.diagnose()['findings']
        self.assertEqual(finding['winner']['path'], str(near))
        self.assertEqual([d['path'] for d in finding['definitions']], [str(mid), str(far), str(near)])

    def test_home_skills_are_not_counted_again_as_ancestors(self):
        skill(self.home / '.agents' / 'skills', 'plan')
        home_project = self.home / 'work'
        (home_project / '.git').mkdir(parents=True)
        finding, = plugin_opencode.diagnose(home_project)['findings']
        self.assertEqual([d['source'] for d in finding['definitions']], ['home-agents'])

    def test_configuration_above_the_git_root_is_still_not_read(self):
        self.write(self.base / 'opencode.json', {'mcp': {'agent-braid': {'type': 'remote'}}})
        self.assertEqual(self.diagnose()['findings'], [])

    def test_relative_xdg_config_home_is_used_as_given(self):
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.base)
        skill(self.base / 'rel' / 'opencode' / 'skills', 'plan')
        with mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': 'rel'}):
            finding, = self.diagnose()['findings']
        self.assertEqual(finding['skillId'], 'plan')


class OpenCodeDoctorCliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.home = self.base / 'home'
        self.state = self.base / 'state'
        self.project = self.base / 'proj'
        for path in (self.home, self.state, self.project / '.git'):
            path.mkdir(parents=True)
        self.state.chmod(0o700)

    def cli(self, *argv):
        env = dict(os.environ, PYTHONPATH=str(ROOT), HOME=str(self.home), XDG_CONFIG_HOME='')
        return subprocess.run([sys.executable, '-m', 'agent_braid', 'plugin', 'doctor', '--home', str(self.state), *argv],
                              capture_output=True, text=True, env=env, cwd=ROOT, timeout=60)

    def test_without_host_output_is_unchanged_even_with_collisions_present(self):
        skill(self.project / '.opencode' / 'skills', 'analyze')
        skill(self.home / '.claude' / 'skills', 'setup')
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        with mock.patch.dict(os.environ, {'HOME': str(self.home), 'XDG_CONFIG_HOME': ''}):
            expected = json.dumps(PluginRouter(self.state, None).status(), ensure_ascii=False, sort_keys=True, indent=2) + '\n'
        self.assertEqual(result.stdout, expected)
        self.assertNotIn('opencode', json.loads(result.stdout))

    def test_with_host_the_report_extends_the_existing_fields(self):
        skill(self.project / '.opencode' / 'skills', 'analyze')
        base = json.loads(self.cli().stdout)
        result = self.cli('--host', 'opencode', '--project', str(self.project))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        opencode = report.pop('opencode')
        self.assertEqual(report, base)
        self.assertEqual([f['code'] for f in opencode['findings']], ['collision'])
        self.assertIn('pluginVersion', report)

    def test_project_without_host_is_refused(self):
        result = self.cli('--project', str(self.project))
        self.assertEqual(result.returncode, 2)
        self.assertIn('--host opencode', result.stderr)


if __name__ == '__main__':
    unittest.main()
