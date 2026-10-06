# SPDX-License-Identifier: AGPL-3.0-only
"""Regenerate finite provider-inspired lifecycle controls without SDK execution."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "specs/023-recorded-trace-adapters"
spec = importlib.util.spec_from_file_location("trace_lifecycle_spike", FEATURE / "spikes/run_lifecycle.py")
spike = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spike)


class TraceLifecycleSpikeTests(unittest.TestCase):
    def test_predeclared_cases_regenerate_exact_results_without_dispatch(self):
        corpus = json.loads((FEATURE / "spikes/corpus.json").read_text())
        expected = json.loads((FEATURE / "spikes/results.json").read_text())
        with patch("subprocess.Popen") as process, patch("subprocess.run") as run, \
                patch("socket.socket") as socket, patch("urllib.request.urlopen") as network:
            result = spike.run()
        self.assertEqual(result, expected)
        self.assertEqual(len(result["results"]), 10)
        self.assertEqual(result["casesExcluded"], 0)
        self.assertFalse(result["executionAuthorization"])
        for case, record in zip(corpus["cases"], result["results"]):
            with self.subTest(case=case["caseId"]):
                self.assertEqual(record["caseId"], case["caseId"])
                self.assertEqual(record["outcome"], case["expected"]["outcome"])
                self.assertEqual(record["classification"], case["expected"]["classification"])
                self.assertEqual(record["timeline"], case["timeline"])
                self.assertFalse(record["falseSafe"])
                self.assertFalse(record["executionAuthorization"])
                if record["outcome"] == "mapped":
                    self.assertTrue(record["analyzerRecomputeConsistency"])
                    self.assertEqual(record["classification"], "unknown")
        process.assert_not_called()
        run.assert_not_called()
        socket.assert_not_called()
        network.assert_not_called()

    def test_provider_counts_keep_unsupported_and_unknown_denominators(self):
        providers = {p["provider"]: p for p in spike.run()["providers"]}
        self.assertEqual(providers["openai"]["caseCount"], 5)
        self.assertEqual(providers["openai"]["mappedCount"], 4)
        self.assertEqual(providers["openai"]["unsupportedCount"], 1)
        self.assertEqual(providers["mcp"]["caseCount"], 5)
        self.assertEqual(providers["mcp"]["mappedCount"], 3)
        self.assertEqual(providers["mcp"]["unsupportedCount"], 2)
        for provider in providers.values():
            self.assertEqual(provider["unknownCount"], provider["mappedCount"])
            self.assertEqual(provider["falseSafeCount"], 0)
            self.assertEqual(provider["outcome"], "negative-for-complete-provider-projection")
            self.assertEqual(provider["nextDecision"], "research-only")

    def test_pins_screening_and_privacy_status_do_not_promote_adoption(self):
        pins = json.loads((FEATURE / "source-pins.json").read_text())
        sources = {source["id"]: source for source in pins["sources"]}
        for source in sources.values():
            self.assertRegex(source["commit"], "^[0-9a-f]{40}$")
            retrieved = [d for d in source["documents"] if d["status"] == "retrieved"]
            self.assertTrue(retrieved)
            for document in retrieved:
                self.assertRegex(document["sha256"], "^[0-9a-f]{64}$")
                self.assertIn(source["commit"], document["url"])
                self.assertGreater(document["bytes"], 0)
        self.assertEqual(sources["openai"]["selectedVersion"], "v0.23.1")
        self.assertEqual(sources["mcp"]["selectedVersion"], "2025-11-25")
        screening = json.loads((FEATURE / "ecosystem-screening.json").read_text())
        self.assertEqual([record["candidate"] for record in screening["records"]],
                         ["A2A", "NeMo Agent Toolkit", "OpenTelemetry"])
        for record in screening["records"]:
            self.assertIn(record["sourcePin"], sources)
            self.assertIn(record["nextDecision"], {"watch", "research-only"})
            self.assertFalse(record["conformance"]["executed"])
            self.assertTrue(record["privacyRisks"])
            self.assertTrue(record["aimLoss"])
        self.assertFalse(screening["historicalRegistryModified"])
        self.assertFalse(screening["historicalRadarModified"])
        self.assertEqual(screening["providerAdoption"], "pending")
        self.assertFalse(screening["executionAuthorization"])
