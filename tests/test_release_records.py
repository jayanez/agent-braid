# SPDX-License-Identifier: AGPL-3.0-only

import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from scripts.validate_release_records import validate_record


ROOT = Path(__file__).resolve().parents[1]


class ReleaseRecordTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "protocol.md").write_text("protocol\n")
        (self.root / "evidence.json").write_text("{}\n")
        self.pending = {
            "recordVersion": "0.2.0",
            "release": "example",
            "softwareMaturity": "research-preview",
            "independent_validation": {
                "status": "pending",
                "conflictOfInterest": "Founder-authored and founder-reviewed.",
                "reproductionProtocol": "protocol.md",
                "invitation": "External reviewers are invited to reproduce this evidence.",
            },
            "internalEvidence": ["evidence.json"],
            "scientificOrBenchmarkClaims": True,
            "limits": ["No production-safety claim."],
        }

    def tearDown(self):
        self.temporary.cleanup()

    def test_pending_record_is_explicit_and_complete(self):
        self.assertEqual(validate_record(self.pending, self.root), [])

    def test_provisional_record_version_is_rejected(self):
        record = dict(self.pending)
        record["recordVersion"] = "0.1.0"
        self.assertTrue(any("0.2.0" in item for item in validate_record(record, self.root)))

    def test_missing_status_and_pending_disclosure_fail(self):
        record = dict(self.pending)
        record["independent_validation"] = {"status": "pending"}
        failures = validate_record(record, self.root)
        self.assertTrue(any("conflictOfInterest" in item for item in failures))
        self.assertTrue(any("reproductionProtocol" in item for item in failures))

    def test_pending_record_cannot_claim_independent_validation(self):
        record = dict(self.pending)
        record["limits"] = ["This release is independently validated."]
        self.assertTrue(any("claims independently validated" in item
                            for item in validate_record(record, self.root)))

    def test_completed_requires_external_reviewer_and_evidence(self):
        record = dict(self.pending)
        record["independent_validation"] = {"status": "completed"}
        failures = validate_record(record, self.root)
        self.assertTrue(any("reviewer" in item for item in failures))
        self.assertTrue(any("evidence" in item for item in failures))
        record["independent_validation"] = {
            "status": "completed",
            "reviewer": {
                "name": "Project Founder", "affiliation": "Agent Braid",
                "external": False, "conflictOfInterest": "Project founder and author.",
            },
            "evidence": "evidence.json",
        }
        self.assertTrue(any("must be external" in item
                            for item in validate_record(record, self.root)))
        schema = json.loads(
            (ROOT / "schemas/governance/release-validation-record.schema.json").read_text()
        )
        validator = Draft202012Validator(schema)
        self.assertTrue(list(validator.iter_errors(record)))
        missing_reviewer = dict(record)
        missing_reviewer["independent_validation"] = {
            "status": "completed", "evidence": "evidence.json"
        }
        self.assertTrue(list(validator.iter_errors(missing_reviewer)))
        record["independent_validation"]["reviewer"] = {
            "name": "Independent Reviewer", "affiliation": "External Laboratory",
            "external": True, "conflictOfInterest": "None declared.",
        }
        self.assertEqual(validate_record(record, self.root), [])
        validator.validate(record)

    def test_not_applicable_rejects_scientific_claims(self):
        record = dict(self.pending)
        record["independent_validation"] = {
            "status": "not_applicable", "rationale": "Editorial metadata only."
        }
        self.assertTrue(any("scientificOrBenchmarkClaims false" in item
                            for item in validate_record(record, self.root)))
