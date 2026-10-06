"""Behavior and independent arithmetic for the synthetic evidence program."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "research/adoption/evidence-program"
SPEC = importlib.util.spec_from_file_location("adoption_evidence_program", BASE / "program.py")
program = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(program)
CANDIDATE = "a" * 64


class AdoptionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.register = program.load(BASE / "fixtures/register.json")
        self.frozen = program.load(BASE / "fixtures/frozen.json")

    def output(self):
        return program.report(self.register, self.frozen, CANDIDATE)

    def test_sc001_canonical_units_and_aliases(self):
        metrics = {r["id"]: r for r in self.output()["metrics"]}
        self.assertEqual(metrics["organizations"]["value"], 2)
        self.assertEqual(metrics["workloads"]["value"], 2)
        self.assertEqual(metrics["organizations"]["excluded"], 1)
        self.assertEqual(len(self.output()["episodes"]), 5)
        self.register["organizations"][1]["aliases"] = ["alias-a"]
        with self.assertRaisesRegex(program.InvalidEvidence, "alias"):
            self.output()

    def test_sc001_real_and_unresolved_intake_refused(self):
        for field, value in [("population", "real"), ("version", "unknown")]:
            with self.subTest(field=field):
                r = copy.deepcopy(self.register); r[field] = value
                with self.assertRaises(program.InvalidEvidence):
                    program.freeze(r)
        self.register["sources"][0]["kind"] = "real"
        with self.assertRaises(program.InvalidEvidence):
            self.output()

    def test_duplicate_episode_identity_rejects_new_ids_aliases_and_outcomes(self):
        for alter in ({"id": "episode-copy"},
                      {"id": "episode-copy", "organization": "alias-a"},
                      {"id": "episode-copy", "outcome": "failed"}):
            r = copy.deepcopy(self.register)
            r["episodes"].append({**copy.deepcopy(r["episodes"][0]), **alter})
            with self.subTest(alter=alter), self.assertRaisesRegex(
                    program.InvalidEvidence, "duplicate bound episode"):
                program.freeze(r)
        r = copy.deepcopy(self.register)
        another = copy.deepcopy(r["episodes"][0])
        another["id"] = "episode-distinct"
        another["binding"]["input"] = "b" * 64
        r["episodes"].append(another)
        result = program.report(r, program.freeze(r), CANDIDATE)
        self.assertEqual(len(result["episodes"]), 6)

    def test_huge_json_integer_refuses_without_float_overflow_or_traceback(self):
        for value in (10**400, -(10**400)):
            r = copy.deepcopy(self.register)
            r["episodes"][0]["times"]["setup"] = value
            with self.subTest(sign=value > 0), self.assertRaisesRegex(
                    program.InvalidEvidence, "numeric bound"):
                program.freeze(r)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "huge.json"
            path.write_text('{"PRIVATE-SENTINEL":' + '9' * 400 + '}')
            with self.assertRaisesRegex(program.InvalidEvidence, "numeric bound"):
                program.load(path)
            result = subprocess.run([
                sys.executable, str(BASE / "program.py"), str(path),
                str(BASE / "fixtures/frozen.json"), "--candidate", CANDIDATE],
                capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
            self.assertEqual(result.stderr, b"adoption-evidence: input refused\n")
            self.assertNotIn(b"PRIVATE-SENTINEL", result.stderr)
            self.assertNotIn(b"Traceback", result.stderr)

    def test_sc002_independently_fixed_arithmetic(self):
        expected = json.loads((BASE / "fixtures/expected.json").read_text())
        for metric in self.output()["metrics"]:
            with self.subTest(metric=metric["id"]):
                self.assertEqual({key: metric[key] for key in ("value", "denominator", "missing", "excluded")}, expected[metric["id"]])
                self.assertEqual(metric["inputHash"], program.digest(self.register))
                self.assertEqual(metric["manifestHash"], program.digest(self.register["metrics"]))
        self.assertEqual(sum(r["totalSeconds"] for r in self.output()["episodes"] if r["eligible"] and r["totalSeconds"] is not None), 45)

    def test_sc002_reject_wrong_unit_proxy_and_popularity(self):
        for field, value in [("unit", "organization"), ("evidenceClass", "proxy"), ("formula", "sum(stars)")]:
            r = copy.deepcopy(self.register); r["metrics"][2][field] = value
            with self.subTest(field=field), self.assertRaises(program.InvalidEvidence):
                program.freeze(r)
        self.register["metrics"].append({**self.register["metrics"][0], "id": "stars"})
        with self.assertRaises(program.InvalidEvidence):
            self.output()

    def test_sc003_complete_costs_and_missingness(self):
        episodes = self.output()["episodes"]
        self.assertEqual([r["outcome"] for r in episodes], ["completed", "failed", "abandoned", "unknown", "completed"])
        self.assertEqual([r["totalSeconds"] for r in episodes], [20, 10, 15, None, 4])
        self.assertEqual(episodes[3]["seconds"], {"setup": 2, "run": None, "review": 3, "debug": 4})
        self.assertEqual(episodes[1]["judgment"], "useful")
        self.assertEqual(episodes[1]["outcome"], "failed")
        self.assertEqual(episodes[1]["judgmentClass"], "proxy")

    def test_sc003_invalid_durations_refused(self):
        for value in (-1, True, float("nan"), float("inf"), "2"):
            r = copy.deepcopy(self.register); r["episodes"][0]["times"]["setup"] = value
            with self.subTest(value=value), self.assertRaises(program.InvalidEvidence):
                program.freeze(r)
        self.register["episodes"][0]["times"].pop("debug")
        with self.assertRaises(program.InvalidEvidence):
            self.output()

    def test_sc004_rights_duplicates_and_unreplayable_controls(self):
        rows = self.output()["contributions"]
        self.assertEqual([r["disposition"] for r in rows], ["admitted", "duplicate", "rejected", "pending", "rejected"])
        self.assertEqual(rows[0]["outcome"], "negative")
        self.assertTrue(rows[0]["replayExecuted"])
        self.assertEqual(rows[0]["replay"]["left"], 1)
        self.assertEqual(rows[0]["replay"]["right"], 2)
        self.assertTrue(rows[0]["replay"]["diverges"])
        self.assertTrue(all(not r["replayExecuted"] for r in rows[1:]))

    def test_sc004_contradictory_replay_not_admitted(self):
        self.register["contributions"][0]["observed"] = "1"
        self.frozen = program.freeze(self.register)
        row = self.output()["contributions"][0]
        self.assertEqual(row["disposition"], "changes-requested")
        self.assertEqual(row["reason"], "contradictory-replay-outcome")

    def test_sc004_replay_is_closed_and_bounded(self):
        for replay in ({"initial": 0, "left": [], "right": [1]}, {"initial": 0, "left": [True], "right": [1]}, {"initial": 0, "left": [1], "right": [2], "command": "execute"}):
            with self.subTest(replay=replay), self.assertRaises(program.InvalidEvidence):
                program.replay_counterexample(replay)
        self.assertFalse(program.replay_counterexample({"initial": 0, "left": [1], "right": [1]})["diverges"])

    def test_sc005_externality_and_candidate_controls(self):
        rows = self.output()["reproductions"]
        self.assertEqual([r["status"] for r in rows], ["internal", "pending", "synthetic-external-proposal", "changes-requested", "pending"])
        self.assertTrue(all(not r["releaseUpdateApplied"] for r in rows))
        self.assertEqual(self.output()["independentValidation"], "pending")
        for key in ("identity", "affiliation", "conflicts"):
            r = copy.deepcopy(self.register); r["reproductions"][2]["reviewer"][key] = None
            output = program.report(r, program.freeze(r), CANDIDATE)
            self.assertEqual(output["reproductions"][2]["status"], "pending")

    def test_sc005_commands_environment_and_rights_required(self):
        for key, value in [("commands", []), ("environment", None), ("rights", "withdrawn")]:
            r = copy.deepcopy(self.register); r["reproductions"][2][key] = value
            output = program.report(r, program.freeze(r), CANDIDATE)
            self.assertEqual(output["reproductions"][2]["status"], "pending")
        self.register["reproductions"][0]["binding"]["candidate"] = "b" * 64
        self.frozen = program.freeze(self.register)
        self.assertEqual(self.output()["reproductions"][0]["status"], "changes-requested")

    def test_sc007_hash_window_and_manifest_drift_invalidate(self):
        for alter in (lambda r: r["window"].update(end="2026-11-30"),
                      lambda r: r["episodes"][0]["times"].update(run=6),
                      lambda r: r["metrics"][0].update(baseline="changed baseline")):
            r = copy.deepcopy(self.register); alter(r)
            out = program.report(r, self.frozen, CANDIDATE)
            self.assertTrue(out["auditReasons"])
            self.assertTrue(all(not m["valid"] and m["value"] is None for m in out["metrics"]))
            self.assertEqual(out["metrics"][0]["denominator"], 3)

    def test_sc007_withdrawn_permission_and_stale_episode(self):
        self.register["sources"][0]["permission"] = "withdrawn"
        self.assertTrue(all(not row["eligible"] for row in self.output()["episodes"]))
        self.assertTrue(all(not row["valid"] for row in self.output()["metrics"]))
        self.register = program.load(BASE / "fixtures/register.json")
        self.register["episodes"][0]["binding"]["candidate"] = "b" * 64
        self.frozen = program.freeze(self.register)
        out = self.output()
        self.assertIn("stale-episode:episode-1", out["auditReasons"])
        self.assertTrue(all(m["value"] is None for m in out["metrics"]))

    def test_sc007_all_missing_is_unknown_not_zero(self):
        for row in self.register["episodes"]:
            row["outcome"] = None; row["times"] = dict.fromkeys(program.PHASES)
            row["judgment"] = "abstain"
        self.frozen = program.freeze(self.register)
        for row in self.output()["metrics"]:
            if row["id"] in ("cost", "completion", "judgment"):
                self.assertIsNone(row["value"])
                self.assertEqual(row["missing"], 4)
                self.assertEqual(row["denominator"], 0)

    def test_sc007_determinism_privacy_no_authority(self):
        first = program.canonical(self.output())
        self.assertEqual(first, program.canonical(self.output()))
        for sentinel in (b"private-synthetic-author", b"private-synthetic-reviewer", b"project affiliated", b"synthetic replay:"):
            self.assertNotIn(sentinel, first)
        self.assertEqual(self.output()["realYield"], 0)
        self.assertFalse(self.output()["publicationAuthorized"])
        self.assertFalse(self.output()["executionAuthorized"])
        self.register["metrics"][0]["limit"] = "PRIVATE-MANIFEST-SENTINEL"
        self.frozen = program.freeze(self.register)
        self.assertNotIn(b"PRIVATE-MANIFEST-SENTINEL", program.canonical(self.output()))

    def test_parser_duplicate_nonfinite_bounds_and_sanitized_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            for raw in ('{"id":1,"id":2}', '{"private":NaN}', '{"x":' + '[' * 18 + '0' + ']' * 18 + '}'):
                path.write_text(raw)
                with self.assertRaises(program.InvalidEvidence):
                    program.load(path)
            path.write_text('{"PRIVATE-SENTINEL": NaN}')
            result = subprocess.run([sys.executable, str(BASE / "program.py"), str(path), str(BASE / "fixtures/frozen.json"), "--candidate", CANDIDATE], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
            self.assertNotIn(b"PRIVATE-SENTINEL", result.stderr)

    def test_cli_repeatable_and_metadata_commands_not_executed(self):
        args = [sys.executable, str(BASE / "program.py"), str(BASE / "fixtures/register.json"), str(BASE / "fixtures/frozen.json"), "--candidate", CANDIDATE]
        first = subprocess.run(args, capture_output=True, check=True)
        second = subprocess.run(args, capture_output=True, check=True)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout), self.output())
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "never-created"
            self.register["contributions"][0]["commands"] = [f"touch {marker}"]
            self.frozen = program.freeze(self.register)
            self.output()
            self.assertFalse(marker.exists())

    def test_sc006_historical_source_bindings_and_pending_decisions(self):
        import hashlib
        packet = json.loads((ROOT / "specs/026-adoption-evidence-program/legacy-status-reconciliation.json").read_text())
        self.assertEqual(len(packet["obligations"]), 9)
        for path, expected in packet["sources"].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)
        self.assertTrue(all(row["proposedDisposition"] == "pending-founder-reconciliation" for row in packet["obligations"]))
        self.assertFalse(packet["currentRemoteVerified"])
        self.assertEqual(packet["observationDate"], "2026-09-25")


if __name__ == "__main__":
    unittest.main()
