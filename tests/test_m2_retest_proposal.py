# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed controls for the unapproved M2 real-corpus retest proposal."""

from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_m2_retest_proposal import (
    EXPECTED_LIMITS, INPUT_PATH, PROPOSAL_COMMIT, ROOT,
    RetestPreflightRejected, check_code_hashes, check_controls,
    check_dependency_hashes, check_footprints, check_image, check_prs,
    check_refs, check_workstreams,
    expected_refs, negative_controls,
)


class M2RetestProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.proposal = json.loads((ROOT / INPUT_PATH).read_text())
        feature = ROOT / "specs/013-m2-real-workload"
        self.manifest = json.loads((feature / "m2-corpus-manifest.json").read_text())
        self.selection = json.loads((feature / "m2-corpus-selection.json").read_text())
        self.refs = expected_refs(self.proposal)
        self.writes = {identifier: footprint["writes"][:]
                       for identifier, footprint in self.selection["footprints"].items()}
        self.code_hashes = {key: self.proposal["candidate"][key]
                            for key in ("prototypeSha256", "gitProcessSha256",
                                        "benchmarkScriptSha256")}

    def test_frozen_contract_rejects_relaxed_isolation_and_claims(self) -> None:
        check_controls(self.proposal)
        for field, value in (("cpusPerContainer", 3),
                             ("memoryBytesPerContainer", 4 * 1024**3),
                             ("network", "bridge"), ("hostWrites", True),
                             ("sourceRepositoryReadOnly", False),
                             ("repositoryRefPromotion", True)):
            changed = deepcopy(self.proposal)
            changed["resourceLimits"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                    RetestPreflightRejected, "resource limits"):
                check_controls(changed)
        self.assertEqual(self.proposal["resourceLimits"], EXPECTED_LIMITS)
        changed = deepcopy(self.proposal)
        changed["measurementProtocol"]["pairedSamplesPerBatch"] = 1
        with self.assertRaisesRegex(RetestPreflightRejected, "measurement protocol"):
            check_controls(changed)
        changed = deepcopy(self.proposal)
        changed["executionAuthorization"] = True
        with self.assertRaisesRegex(RetestPreflightRejected, "falsely claims"):
            check_controls(changed)

    def test_corpus_rejects_duplicate_pr_and_substituted_commit(self) -> None:
        check_workstreams(self.proposal, self.manifest, self.selection)
        duplicate = deepcopy(self.proposal)
        duplicate["workstreams"][1]["pullRequest"] = duplicate["workstreams"][0]["pullRequest"]
        with self.assertRaisesRegex(RetestPreflightRejected, "duplicate workstream PR"):
            check_workstreams(duplicate, self.manifest, self.selection)
        substituted = deepcopy(self.manifest)
        substituted["operations"][0]["sourceCommit"] = "f" * 40
        with self.assertRaisesRegex(RetestPreflightRejected, "source commit"):
            check_workstreams(self.proposal, substituted, self.selection)

    def test_live_ref_and_declared_write_controls(self) -> None:
        check_refs(self.proposal, self.refs)
        check_footprints(self.selection, self.writes)
        moved = dict(self.refs)
        moved["refs/heads/develop"] = "f" * 40
        with self.assertRaisesRegex(RetestPreflightRejected, "remote ref moved"):
            check_refs(self.proposal, moved)
        missing = dict(self.refs)
        del missing["refs/heads/work/m2-parallel-prep-performance-20260925"]
        with self.assertRaisesRegex(RetestPreflightRejected, "remote ref moved"):
            check_refs(self.proposal, missing)
        extra = deepcopy(self.writes)
        extra[next(iter(extra))].append("unregistered.py")
        with self.assertRaisesRegex(RetestPreflightRejected, "undeclared tracked write"):
            check_footprints(self.selection, extra)

    def test_candidate_hash_and_pr_identity_controls(self) -> None:
        check_code_hashes(self.proposal, self.code_hashes)
        changed = dict(self.code_hashes)
        changed["prototypeSha256"] = "f" * 64
        with self.assertRaisesRegex(RetestPreflightRejected, "candidate code hash"):
            check_code_hashes(self.proposal, changed)
        prs = {}
        for number, item, base in (
            (137, self.proposal["workstreams"][0], self.proposal["baseCommit"]),
            (138, self.proposal["workstreams"][1], self.proposal["baseCommit"]),
            (140, self.proposal["candidate"],
             "3b51fb6335400c5673f1ba40cf028a6ac6d525ca"),
            (141, {"pullRequest": "https://github.com/jayanez/agent-braid/pull/141",
                   "branch": "work/m2-performance-retest-decision-20260925",
                   "sourceCommit": PROPOSAL_COMMIT},
             self.proposal["candidate"]["codeCommit"]),
        ):
            prs[number] = {"number": number, "url": item["pullRequest"],
                           "headRefOid": item.get("sourceCommit", item.get("codeCommit")),
                           "headRefName": item["branch"], "baseRefOid": base,
                           "state": "OPEN"}
        check_prs(self.proposal, prs)
        prs[137]["headRefOid"] = "f" * 40
        with self.assertRaisesRegex(RetestPreflightRejected, "PR identity"):
            check_prs(self.proposal, prs)

    def test_image_and_dependency_bytes_must_match_exactly(self) -> None:
        image = {"Id": self.proposal["containerImage"]["id"],
                 "Os": "linux", "Architecture": "arm64"}
        check_image(image)
        changed_image = dict(image, Architecture="amd64")
        with self.assertRaisesRegex(RetestPreflightRejected, "pinned image"):
            check_image(changed_image)
        expected = self.proposal["dependencyFilesSha256"]
        check_dependency_hashes(self.proposal, expected, expected)
        current = dict(expected)
        current["requirements-dev.txt"] = "f" * 64
        with self.assertRaisesRegex(RetestPreflightRejected, "dependency bytes"):
            check_dependency_hashes(self.proposal, current, expected)
        base = dict(expected)
        base["requirements-speckit.txt"] = "f" * 64
        with self.assertRaisesRegex(RetestPreflightRejected, "dependency bytes"):
            check_dependency_hashes(self.proposal, expected, base)

    def test_six_negative_controls_are_actually_exercised(self) -> None:
        self.assertEqual(negative_controls(self.proposal, self.manifest,
                                           self.selection, self.refs, self.writes,
                                           self.code_hashes), [
            "moved-base", "substituted-commit", "duplicate-pr",
            "undeclared-write", "changed-code-hash", "breached-resource-limit",
        ])


if __name__ == "__main__":
    unittest.main()
