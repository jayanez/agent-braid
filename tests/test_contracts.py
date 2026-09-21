# SPDX-License-Identifier: AGPL-3.0-only
"""Development-only Draft 2020-12 structural checks."""

from copy import deepcopy
import unittest
from jsonschema import Draft202012Validator
from scripts.validate_contracts import ROOT, check
from research.lab.model import loads


class StructuralTests(unittest.TestCase):
    def test_contract_corpus(self):
        check()

    def test_aim_invalid_fields(self):
        schema = loads((ROOT / "schemas/0.2.0-draft/agent-interaction-metadata.schema.json").read_text())
        validator = Draft202012Validator(schema)
        original = loads((ROOT / "examples/contracts/0.2.0-draft/aim.json").read_text())
        for mutate in [lambda a: a.pop("attemptId"),
                       lambda a: a.update(verified=True),
                       lambda a: a["effects"]["coverage"].update(status="guaranteed"),
                       lambda a: a["readVersions"].update(x=-1)]:
            value = deepcopy(original)
            mutate(value)
            self.assertTrue(list(validator.iter_errors(value)))

    def test_legacy_bytes(self):
        import hashlib
        # Byte digests from foundation commit 77ca4b5; works in shallow CI checkouts.
        expected = {
            "schemas/agent-interaction-metadata.schema.json": "44b60956817cbcd92e0802dfe99ca537b20768f53472f04afd1dcc502f53cd5c",
            "schemas/confluence-certificate.schema.json": "ea68bf94f6767d615881167d8f7dd28359e6c399edd66935ba17b88b2b1cf785",
            "examples/aim/file-edits.json": "6b5f35a09ec432b34f3b9fc20c64cdcb3e2455fe91262ef8e1e0d74abd498666",
        }
        for path, checksum in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), checksum)
