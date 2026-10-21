# SPDX-License-Identifier: AGPL-3.0-only
"""Software-only join of the three internal verified-plan components."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import system_one_verified_acquisition as acquisition
from agent_braid import system_one_verified_ir as ir
from agent_braid import system_one_verified_registry as registry
from agent_braid.system_one import canonical, digest, thaw
import test_system_one_verified_acquisition as acquisition_fixtures


class VerifiedComponentsTests(unittest.TestCase):
    def setUp(self):
        # Reuse only fresh software-fixture construction, never research labels.
        self.fixture_case = acquisition_fixtures.VerifiedAcquisitionTests()
        self.addCleanup(self.fixture_case.doCleanups)
        self.fixture_case.setUp()
        self.calls = Counter()
        self.budget = self.fixture_case.budget()

    def checkpoint(self, stage, units):
        self.assertIn(stage, {"acquisition", "interpretation", "verification", "selection"})
        self.assertIs(type(units), int)
        self.assertGreaterEqual(units, 0)
        self.calls[stage] += units
        if self.calls["verification"] > 128:
            raise ValueError("work-budget-exceeded")

    def acquire(self):
        return acquisition.acquire(
            self.fixture_case.source, self.fixture_case.owned,
            limits=acquisition._BOUNDS, git_budget=self.budget,
            remaining_ns=lambda stage: 30_000_000_000,
            checkpoint=self.checkpoint)

    def registry_identity(self):
        pin = registry._PINNED_VERIFIER_SHA256
        self.assertIsInstance(pin, str)
        self.assertNotEqual(pin, "0" * 64)
        self.assertEqual(pin, sha256(Path(ir.__file__).read_bytes()).hexdigest())
        entry = {"domainId": "t024-eof-context-v1",
                 "irVersion": "t024-literal-program-v1",
                 "observationContract": "t024-path-blob-projection-v1",
                 "implementationId": "t024-eof-verifier-extracted-v1",
                 "verifierDigest": pin}
        manifest = {"format": "s1-static-verifier-registry-v1",
                    "entries": [entry], "executionAuthorization": False}
        return {k: entry[k] for k in ("domainId", "irVersion", "observationContract",
                                       "verifierDigest")} | {"registryDigest": digest(manifest)}

    def test_acquisition_ir_grammar_selection_and_real_registry_pin_join(self):
        before = self.fixture_case.inventory()
        acquired = self.acquire()
        program = acquired["program"]
        self.assertEqual(ir.validate_program(program, checkpoint=self.checkpoint), program)
        for language in ("en", "es"):
            for representation in ("symbolic", "controlled"):
                with self.subTest(language=language, representation=representation):
                    payload = ir.render(program, language, representation,
                                        checkpoint=self.checkpoint)
                    parsed = ir.interpret(payload, checkpoint=self.checkpoint)
                    self.assertEqual(canonical(parsed), canonical(program))
        decision = ir.verify_program(program,
            tuple(self.fixture_case.source["task"]["optionOrder"]),
            max_hunks=128, checkpoint=self.checkpoint)
        self.assertEqual(set(decision), {"status", "eligible", "choice", "plans",
                                         "executionAuthorization"})
        self.assertEqual(decision["status"], "answered")
        self.assertEqual(decision["eligible"], ("k0", "k1"))
        self.assertEqual(decision["choice"], "k0")
        self.assertIs(decision["plans"]["k2"]["valid"], False)
        self.assertIs(decision["executionAuthorization"], False)
        entry = registry.resolve(self.registry_identity(), checkpoint=self.checkpoint)
        self.assertEqual(entry["implementationId"], "t024-eof-verifier-extracted-v1")
        self.assertEqual(acquired["binding"]["snapshotDigest"],
                         digest(acquired["binding"]["snapshot"]))
        self.assertGreater(self.calls["verification"], 0)
        self.assertEqual(self.fixture_case.inventory(), before)
        self.assertEqual(list(self.fixture_case.scratch.iterdir()), [])

    def test_reacquisition_and_verification_share_context_without_reset(self):
        first = self.acquire()
        commands, output, start = (self.budget.commands, self.budget.output_bytes,
                                   self.budget.started_at)
        order = tuple(self.fixture_case.source["task"]["optionOrder"])
        first_result = ir.verify_program(first["program"], order, max_hunks=128,
                                         checkpoint=self.checkpoint)
        hunks = self.calls["verification"]
        second = self.acquire()
        second_result = ir.verify_program(second["program"], order, max_hunks=128,
                                          checkpoint=self.checkpoint)
        self.assertEqual(first, second)
        self.assertEqual(first_result, second_result)
        self.assertEqual(self.budget.started_at, start)
        self.assertEqual(self.budget.commands, commands * 2)
        self.assertEqual(self.budget.output_bytes, output * 2)
        self.assertEqual(self.calls["verification"], hunks * 2)
        self.budget.cancel_event.set()
        with self.assertRaisesRegex(ValueError, "^cancelled$"):
            self.acquire()
        self.assertEqual(self.budget.commands, commands * 2)

    def test_changed_verifier_bytes_refuse_without_mutating_actual_source(self):
        identity = self.registry_identity()
        actual = Path(ir.__file__).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed.py"
            changed.write_bytes(actual + b"# changed verifier\n")
            with patch.object(registry, "_VERIFIER_SOURCE", changed):
                with self.assertRaisesRegex(ValueError, "^verifier-mismatch$"):
                    registry.resolve(identity, checkpoint=self.checkpoint)
        self.assertEqual(Path(ir.__file__).read_bytes(), actual)

    def test_core_component_imports_do_not_load_research_or_neural_packages(self):
        code = ("import sys,json; from agent_braid import system_one_verified_ir, "
                "system_one_verified_acquisition, system_one_verified_registry; "
                "print(json.dumps(sorted(n for n in sys.modules if "
                "n == 'torch' or n.startswith('torch.') or "
                "n == 'transformers' or n.startswith('transformers.') or "
                "n == 'agent_braid_system_one' or n.startswith('agent_braid_system_one.') or "
                "n == 'research' or n.startswith('research.'))))")
        result = subprocess.run([sys.executable, "-c", code], check=True,
                                capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), [])


if __name__ == "__main__":
    unittest.main()
