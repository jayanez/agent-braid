# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.system_one import STRICT_POLICY, evaluate
from tests.test_system_one_core import encoded, fixture, repair_state


class SystemOnePolicyTests(unittest.TestCase):
    def test_default_strict_is_uncalibrated_abstention(self):
        response = evaluate(encoded(fixture(policy=STRICT_POLICY)))
        self.assertEqual(response["status"], "abstain")
        self.assertEqual(response["reasonCodes"], ["calibration-absent"])
        self.assertEqual(response["answers"], [])
        self.assertEqual(response["inputCoverage"], 0)
        self.assertEqual(response["calibrationStatus"], "absent")
        self.assertNotIn("calibratedProbability", response)
        self.assertFalse(response["executionAuthorization"])

    def test_missing_mapping_never_publishes_partial_batch(self):
        value = fixture()
        value["state"]["ruleAnswers"] = {}
        repair_state(value)
        response = evaluate(encoded(value))
        self.assertEqual(response["status"], "abstain")
        self.assertEqual(response["reasonCodes"], ["fixture-mapping-missing"])
        self.assertEqual(response["answers"], [])
        self.assertEqual(response["inputCoverage"], 0)

    def test_explicit_fixture_diagnostic_never_grants_authority(self):
        response = evaluate(encoded(fixture()))
        self.assertEqual(response["status"], "answered")
        self.assertEqual(response["answers"][0]["rawTopProbability"], 1)
        self.assertFalse(response["executionAuthorization"])
        self.assertEqual(response["evidenceClass"], "heuristic")
        self.assertIsNone(response["calibrationManifestDigest"])
        self.assertNotIn("certificate", response)
