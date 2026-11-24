"""SPEC-073 T010: the owner drill in drill.md runs as written on a fixture (procedure_009)."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import spec073_owner_promotion as drill

ROOT = Path(__file__).resolve().parents[1]


class OwnerDrillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.env = {**os.environ, 'PY': sys.executable, 'D': str(base / 'spec073-drill'),
                    'AGENT_BRAID_HOME': str(base / 'not-the-real-home'),
                    drill.EVIDENCE_ENV: str(base / 'procedure_009.json')}
        self.workdir, self.evidence = base / 'spec073-drill', base / 'procedure_009.json'
        self.skill = (ROOT / drill.lp.SCOPES[drill.SCOPE].target).read_bytes()

    def tearDown(self):
        self.tmp.cleanup()

    def run_step(self, command):
        # One shell per step, like the owner's: drill.env is sourced once it exists.
        script = f'[ -f "$D/drill.env" ] && . "$D/drill.env"; {command}'
        return subprocess.run(['bash', '-c', script], cwd=ROOT, env=self.env, capture_output=True,
                              text=True, timeout=120)

    def test_the_rendered_page_is_committed(self):
        self.assertEqual((ROOT / 'specs/073-lightning-promotion/drill.md').read_text(), drill.render_doc())

    def test_every_drill_step_runs_as_written_and_touches_only_the_work_directory(self):
        committed_evidence = drill.EVIDENCE.read_bytes() if drill.EVIDENCE.exists() else None
        for number, (title, _, command, code, expect) in enumerate(drill.STEPS, 1):
            if title == 'Clean up':
                record = json.loads(self.evidence.read_text())
            result = self.run_step(command)
            self.assertEqual(result.returncode, code, f'step {number} {title}: {result.stderr}')
            self.assertIn(expect, result.stdout, f'step {number} {title}')
        self.assertEqual(record['result'], 'OK')
        self.assertEqual(record['observed']['journal'],
                         ['recorded', 'begun', 'committed', 'recorded', 'begun', 'committed', 'rolled-back'])
        self.assertEqual(record['observed']['activeSha256'], record['observed']['candidateA'])
        self.assertEqual(record['observed']['releaseCheckMismatches'], [])
        self.assertFalse(self.workdir.exists())  # cleaned up
        self.assertFalse(Path(self.env['AGENT_BRAID_HOME']).exists())  # no plugin home was used
        self.assertEqual((ROOT / drill.lp.SCOPES[drill.SCOPE].target).read_bytes(), self.skill)
        self.assertEqual(drill.EVIDENCE.read_bytes() if drill.EVIDENCE.exists() else None,
                         committed_evidence)

    def test_an_edited_skill_fails_the_check_and_the_evidence(self):
        for _, _, command, _, _ in drill.STEPS[:4]:
            self.assertEqual(self.run_step(command).returncode, 0)
        target = self.workdir / 'root' / drill.lp.SCOPES[drill.SCOPE].target
        target.write_text(target.read_text() + 'hand edit\n')
        result = self.run_step('$PY -m scripts.spec073_owner_promotion check --workdir "$D"')
        self.assertEqual(result.returncode, 1)
        self.assertIn('lightning-promotion-mismatch: lightning.skill.analyze expected', result.stdout)
        result = self.run_step('$PY -m scripts.spec073_owner_promotion evidence --workdir "$D"')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(self.evidence.read_text())['result'], 'FAILED')

    def test_setup_refuses_the_real_home_an_existing_directory_and_cleanup_an_unmarked_one(self):
        home = Path(self.env['AGENT_BRAID_HOME'])
        for workdir in (home, home / 'drill'):
            result = self.run_step(f'$PY -m scripts.spec073_owner_promotion setup --workdir "{workdir}"')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('overlaps the real plugin home', result.stderr)
        self.workdir.mkdir()
        result = self.run_step('$PY -m scripts.spec073_owner_promotion setup --workdir "$D"')
        self.assertIn('already exists', result.stderr)
        result = self.run_step('$PY -m scripts.spec073_owner_promotion cleanup --workdir "$D"')
        self.assertIn('has no spec073-drill.json', result.stderr)
        self.assertTrue(self.workdir.exists())


if __name__ == '__main__':
    unittest.main()
