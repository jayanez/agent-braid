# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded structured exchange positive and negative controls."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from agent_braid.structured_exchange import (
    InvalidExchange, exhaustive_corpus, produce, replay, verify,
)
from scripts.run_m3_git_witness import witness


def fixture(count: int = 2) -> dict:
    return {
        "model": "anchored-sequence-v1",
        "base": [{"id": "b0", "value": "base"}],
        "operations": [
            {"id": f"o{i}", "kind": "insert", "anchorId": "b0",
             "newId": ["z", "a", "m"][i], "value": f"v{i}"}
            for i in range(count)
        ],
    }


class StructuredExchangeTests(unittest.TestCase):
    def test_experimental_schemas_accept_generated_record(self) -> None:
        schema_dir = Path(__file__).resolve().parents[1] / "schemas/0.3.0-experimental"
        request_schema = json.loads((schema_dir / "structured-exchange-request.schema.json").read_text())
        evidence_schema = json.loads((schema_dir / "structured-exchange-evidence.schema.json").read_text())
        Draft202012Validator.check_schema(request_schema)
        Draft202012Validator.check_schema(evidence_schema)
        registry = Registry().with_resource(request_schema["$id"],
                                            Resource.from_contents(request_schema))
        Draft202012Validator(request_schema).validate(fixture())
        Draft202012Validator(evidence_schema, registry=registry).validate(produce(fixture()))

    def test_same_anchor_residual_and_final_observation(self) -> None:
        evidence = produce(fixture())
        self.assertEqual(evidence["proposal"], "propose-swap")
        self.assertTrue(evidence["paths"]["equivalent"])
        self.assertTrue(evidence["paths"]["residualChanged"])
        self.assertEqual(verify(evidence)["status"], "verified-bounded")
        self.assertFalse(evidence["executionAuthorization"])

    def test_braid_paths_are_complete_and_agree(self) -> None:
        evidence = produce(fixture(3))
        self.assertEqual(len(evidence["paths"]["left"]), 4)
        self.assertEqual(len(evidence["paths"]["right"]), 4)
        self.assertEqual(evidence["paths"]["left"][-1]["order"], ["o2", "o1", "o0"])
        self.assertEqual(evidence["paths"]["left"][-1]["final"],
                         evidence["paths"]["right"][-1]["final"])
        self.assertEqual(verify(evidence)["status"], "verified-bounded")

    def test_unknown_anchor_delete_and_duplicate_id_fail_closed(self) -> None:
        for change in (
            {"anchorId": "unknown"},
            {"kind": "delete"},
            {"newId": "b0"},
        ):
            with self.subTest(change=change):
                request = fixture()
                request["operations"][0].update(change)
                with self.assertRaises(InvalidExchange):
                    produce(request)

    def test_tamper_and_missing_path_are_inconclusive(self) -> None:
        evidence = produce(fixture(3))
        for mutate in (
            lambda item: item["paths"]["left"][1]["steps"][0].update(residualIndex=99),
            lambda item: item["paths"]["right"].pop(),
            lambda item: item.update(executionAuthorization=True),
            lambda item: item.update(requestHash="0" * 64),
        ):
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(evidence)
                mutate(changed)
                self.assertEqual(verify(changed)["status"], "inconclusive")

    def test_distinct_anchors_are_conservatively_kept(self) -> None:
        request = fixture()
        request["operations"][1]["anchorId"] = "$root"
        evidence = produce(request)
        self.assertEqual(evidence["proposal"], "keep-order")
        self.assertEqual(verify(evidence)["status"], "verified-bounded")

    def test_order_must_be_complete_permutation(self) -> None:
        with self.assertRaises(InvalidExchange):
            replay(fixture(), ["o0", "o0"])

    def test_finite_corpus(self) -> None:
        report = exhaustive_corpus()
        self.assertEqual(report["cases"], 484)
        self.assertEqual(report["pairCases"], 30)
        self.assertGreater(report["overlappingPairCases"], 0)
        self.assertEqual(report["falseCertificates"], 0)

    def test_temporary_git_serialization_is_only_a_witness(self) -> None:
        report = witness(fixture())
        self.assertTrue(report["sameTree"])
        self.assertEqual(len(report["paths"]), 2)
        self.assertIn("not an M2 fixed-patch certificate", report["claim"])
        self.assertFalse(report["executionAuthorization"])


if __name__ == "__main__":
    unittest.main()
