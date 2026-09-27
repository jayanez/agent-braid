# SPDX-License-Identifier: AGPL-3.0-only
"""Deferred SPEC-019 acceptance anchors; no M3.5 model exists yet."""

import unittest


class NativePredictorContractTests(unittest.TestCase):
    @unittest.skip("SPEC-019 M3.5 implementation is deferred")
    def test_versioned_local_inference_and_tamper(self) -> None:
        self.fail("deferred")

    @unittest.skip("SPEC-019 M3.5 implementation is deferred")
    def test_held_out_evaluation_and_negative_outcome(self) -> None:
        self.fail("deferred")

    @unittest.skip("SPEC-019 M3.5 implementation is deferred")
    def test_verifier_remains_sole_certificate_source(self) -> None:
        self.fail("deferred")
