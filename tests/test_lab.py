# SPDX-License-Identifier: AGPL-3.0-only

from copy import deepcopy
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import unittest

from research.lab import controls
from research.lab.certificates import produce, validate_aim_batch, verify
from research.lab.model import Invalid, canonical, digest, loads, run, schedules, validate_fixture

ROOT = Path(__file__).resolve().parents[1]


def fixture(name="independent"):
    return loads((ROOT / f"examples/lab/{name}.json").read_text())


class ModelTests(unittest.TestCase):
    def test_projection_and_raw_events(self):
        f = fixture()
        bundle = produce(f)
        self.assertEqual(bundle["certificate"]["result"], "equivalent-observed")
        self.assertNotEqual(run(f, ["A", "B"])["events"], run(f, ["B", "A"])["events"])
        f["observation"] = {"mode": "exact"}
        self.assertEqual(produce(f)["certificate"]["result"], "divergent")

    def test_context_counterexample(self):
        f = fixture("context-dependent")
        self.assertEqual(len(schedules(f)), 6)
        self.assertEqual(run(f, ["A", "B", "C"])["state"]["z"], 1)
        self.assertEqual(run(f, ["A", "C", "B"])["state"]["z"], 0)
        self.assertEqual(produce(f)["certificate"]["result"], "divergent")

    def test_all_controls(self):
        with contextlib.redirect_stdout(io.StringIO()):
            controls.check_counterexamples()
            controls.check_finite_braid()

    def test_dependencies_and_cycles(self):
        f = fixture()
        f["operations"][1]["dependencies"] = ["A"]
        self.assertEqual(schedules(f), [["A", "B"]])
        self.assertEqual(run(f, ["B", "A"])["status"], "blocked")
        self.assertEqual(verify(produce(f))["status"], "verified")
        f["operations"][0]["dependencies"] = ["B"]
        with self.assertRaises(Invalid):
            schedules(f)

    def test_guards_and_versions(self):
        f = fixture()
        f["operations"][0]["guard"] = {"op": "eq", "left": {"read": "y"}, "right": {"int": 99}}
        outcome = run(f, ["A", "B"])
        self.assertEqual(outcome["status"], "blocked")
        self.assertEqual(outcome["state"], f["state"])
        self.assertEqual(outcome["pending"], ["A", "B"])
        self.assertEqual(produce(f)["certificate"]["result"], "inconclusive")
        f = fixture()
        f["operations"][1]["readVersions"] = {"x": 0}
        self.assertEqual(run(f, ["A", "B"])["reason"], "stale read version")

    def test_read_arithmetic_and_results(self):
        f = fixture()
        f["operations"][0].update(kind="add", expression={"int": 3})
        f["operations"][1].update(kind="multiply", target="x", expression={"int": 2})
        outcome = run(f, ["A", "B"])
        self.assertEqual(outcome["results"], {"A": 3, "B": 6})
        self.assertEqual(outcome["versions"]["x"], 2)
        f["operations"][1]["kind"] = "read"
        del f["operations"][1]["expression"]
        self.assertEqual(run(f, ["A", "B"])["results"]["B"], 3)

    def test_missing_resource_and_overflow_are_atomic_errors(self):
        for expr in [{"read": "missing"}, {"op": "multiply", "left": {"int": 2**62}, "right": {"int": 4}}]:
            f = fixture()
            f["operations"][0]["expression"] = expr
            outcome = run(f, ["A", "B"])
            self.assertEqual(outcome["status"], "error")
            self.assertEqual(outcome["state"], f["state"])
            self.assertEqual(outcome["events"], [])

    def test_malformed_fixtures(self):
        mutations = [lambda f: f.update(extra=1),
                     lambda f: f["state"].update(x=True),
                     lambda f: f["operations"][0].update(kind="eval"),
                     lambda f: f["operations"][0].update(dependencies=["missing"]),
                     lambda f: f["operations"][1].update(id="A"),
                     lambda f: f["observation"].update(resources=["unknown"]),
                     lambda f: f.update(operations=f["operations"] * 4)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                f = fixture()
                mutate(f)
                with self.assertRaises(Invalid):
                    validate_fixture(f)

    def test_six_operation_bound(self):
        f = fixture()
        f["operations"] = [{**deepcopy(f["operations"][0]), "id": str(i)} for i in range(6)]
        self.assertEqual(len(schedules(f)), 720)
        f["operations"].append({**f["operations"][0], "id": "seventh"})
        with self.assertRaises(Invalid):
            schedules(f)

    def test_canonical_and_strict_json(self):
        self.assertEqual(digest({"x": 1, "y": 2}), digest({"y": 2, "x": 1}))
        for text in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1.0}']:
            with self.assertRaises(Invalid):
                loads(text)
        with self.assertRaises(Invalid):
            canonical({1: "bad key"})

    def test_reproducibility_and_no_mutation(self):
        f = fixture()
        before = deepcopy(f)
        self.assertEqual(canonical(produce(f)), canonical(produce(f)))
        self.assertEqual(f, before)


class CertificateTests(unittest.TestCase):
    def test_valid_and_invalid_corpus(self):
        for path in (ROOT / "examples/contracts/0.2.0-draft").glob("*.json"):
            if path.stem == "aim":
                continue
            expected = {"exhaustive": "verified", "replay": "verified",
                        "proof-unverified": "unverified"}.get(path.stem, "rejected")
            with self.subTest(path=path.name):
                self.assertEqual(verify(loads(path.read_text()))["status"], expected)

    def test_scope_and_contract_mutations(self):
        mutations = [lambda c: c.update(initialStateDigest="sha256:" + "0" * 64),
                     lambda c: c.update(executionContract="real-world-safe"),
                     lambda c: c.update(observation={"mode": "exact"}),
                     lambda c: c["claim"].update(domain="all agents"),
                     lambda c: c["claim"].update(assumptions=[]),
                     lambda c: c["claim"].update(property="confluence"),
                     lambda c: c["claim"].update(method="formal"),
                     lambda c: c["claim"].update(assuranceClass=True)]
        for mutate in mutations:
            bundle = produce(fixture())
            mutate(bundle["certificate"])
            self.assertEqual(verify(bundle)["status"], "rejected")

    def test_rehashed_fake_outcome_is_rejected(self):
        bundle = produce(fixture())
        trace = bundle["certificate"]["evidence"]["traces"][0]
        fake = deepcopy(bundle["artifacts"][trace["outcomeDigest"]])
        fake["state"]["x"] = 99
        bundle["artifacts"][digest(fake)] = fake
        trace["outcomeDigest"] = digest(fake)
        self.assertEqual(verify(bundle)["status"], "rejected")

    def test_arbitrary_malformed_input_rejected(self):
        for value in [None, [], {}, {"certificate": {}, "artifacts": []}]:
            self.assertEqual(verify(value)["status"], "rejected")

    def test_replay_selection(self):
        for chosen in [[['A', 'B']], [['A', 'B'], ['A', 'B']], [['A', 'X']]]:
            with self.assertRaises(Invalid):
                produce(fixture(), chosen)

    def test_proof_artifact_binding(self):
        bundle = loads((ROOT / "examples/contracts/0.2.0-draft/proof-unverified.json").read_text())
        key = bundle["certificate"]["evidence"]["proofDigest"]
        bundle["artifacts"].pop(key)
        self.assertEqual(verify(bundle)["status"], "rejected")

    def test_dependency_free_consumer(self):
        result = subprocess.run([sys.executable, "-S", "-m", "research.lab", "verify",
                                 str(ROOT / "examples/contracts/0.2.0-draft/exhaustive.json")],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_aim_identity_and_dependencies(self):
        a = loads((ROOT / "examples/contracts/0.2.0-draft/aim.json").read_text())
        validate_aim_batch([a])
        with self.assertRaises(Invalid):
            validate_aim_batch([a, a])
        a["dependencies"] = ["unknown"]
        with self.assertRaises(Invalid):
            validate_aim_batch([a])
        a["dependencies"] = ["A"]
        with self.assertRaises(Invalid):
            validate_aim_batch([a])

    def test_cli_exit_status(self):
        for filename, code in [("exhaustive", 0), ("proof-unverified", 1), ("false-verdict", 1)]:
            result = subprocess.run([sys.executable, "-m", "research.lab", "verify",
                                     str(ROOT / f"examples/contracts/0.2.0-draft/{filename}.json")],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
