# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 REQ-006 / SC-006: the surface capability matrix checker.

The checker must pass the seed matrix and reject each mutated copy with the
named finding. The matrix is read, never edited.
"""

from __future__ import annotations

from copy import deepcopy
import unittest

from tests.orchestration_matrix_checker import check_matrix, load_matrix


def cell(matrix: dict, surface: str, lifecycle: str) -> dict:
    return next(c for c in matrix["cells"] if c["surface"] == surface and c["lifecycle"] == lifecycle)


def mutated(mutation) -> dict:
    matrix = deepcopy(load_matrix())
    mutation(matrix)
    return matrix


def host_observed_without_receipt(m):
    c = cell(m, "workflow-tracks", "pre-flight")
    c["evidence"]["status"] = "host-observed"


def class_removed(m):
    del cell(m, "batch", "recovery")["compatibilityClass"]


def preview_removed(m):
    cell(m, "agent-teams", "pre-flight")["preview"] = False


def agent_view_preview_removed(m):
    cell(m, "linked-sessions", "recovery")["preview"] = False


def enforced_wording(m):
    cell(m, "batch", "continuous")["notes"] += " The surface is enforced by this receipt."


def enforcement_in_capability(m):
    cell(m, "workflow-tracks", "pre-flight")["capability"] += ", with enforcement of file ownership"


def surface_deleted(m):
    m["cells"] = [c for c in m["cells"] if c["surface"] != "batch"]
    m["surfaceIds"].remove("batch")


def cell_deleted(m):
    m["cells"].remove(cell(m, "agent-teams", "recovery"))


def cell_duplicated(m):
    m["cells"].append(deepcopy(cell(m, "agent-teams", "recovery")))


def version_basis_removed(m):
    del m["hostVersionsRead"]["versionBasis"]


def cell_version_removed(m):
    del cell(m, "batch", "pre-flight")["minHostVersion"]


def singular_surface(m):
    cell(m, "batch", "pre-flight")["surface"] = "batch-unit"


def plural_surface_ids(m):
    m["surfaceIds"][3] = "batches"


def integration_contradicts_table(m):
    c = cell(m, "agent-teams", "integration")
    c["status"], c["ownerSpec"] = "reuse-of-SPEC-052-unverified", "SPEC-052"


def integration_marked_covered(m):
    cell(m, "workflow-tracks", "integration")["status"] = "covered"


def integration_covered_wording(m):
    cell(m, "workflow-tracks", "integration")["notes"] += " SPEC-052 covers this surface."


def batch_integration_served(m):
    c = cell(m, "batch", "integration")
    c["status"], c["ownerSpec"] = "reuse-of-SPEC-052-unverified", "SPEC-052"
    c["capability"] = "SPEC-052 serves /batch"


def not_covered_item_removed(m):
    m["notCovered"] = [item for item in m["notCovered"] if item != "Codex"]


def unknown_evidence_status(m):
    cell(m, "batch", "pre-flight")["evidence"]["status"] = "verified"


def receipt_on_unobserved_cell(m):
    cell(m, "batch", "pre-flight")["evidence"]["receipt"] = "evidence/hv-11.json"


MUTATIONS = {
    host_observed_without_receipt: "host-observed-without-receipt:workflow-tracks/pre-flight",
    class_removed: "class-missing:batch/recovery",
    preview_removed: "preview-label-missing:agent-teams/pre-flight",
    agent_view_preview_removed: "preview-label-missing:linked-sessions/recovery",
    enforced_wording: "enforcement-wording:batch/continuous",
    enforcement_in_capability: "enforcement-wording:workflow-tracks/pre-flight",
    surface_deleted: "cell-missing:batch/pre-flight",
    cell_deleted: "cell-missing:agent-teams/recovery",
    cell_duplicated: "cell-duplicated:agent-teams/recovery",
    version_basis_removed: "version-basis-missing",
    cell_version_removed: "version-missing:batch/pre-flight",
    singular_surface: "surface-id-outside-set:batch-unit",
    plural_surface_ids: "surface-ids-not-closed-set",
    integration_contradicts_table: "integration-contradicts-specification:agent-teams/integration",
    integration_marked_covered: "status-invalid:workflow-tracks/integration",
    integration_covered_wording: "integration-coverage-wording:workflow-tracks/integration",
    batch_integration_served: "integration-contradicts-specification:batch/integration",
    not_covered_item_removed: "not-covered-list-incomplete",
    unknown_evidence_status: "evidence-status-invalid:batch/pre-flight",
    receipt_on_unobserved_cell: "receipt-without-host-observation:batch/pre-flight",
}


class OrchestrationMatrixTests(unittest.TestCase):
    def test_seed_matrix_passes(self):
        self.assertEqual(check_matrix(load_matrix()), [])

    def test_every_mutation_is_rejected_with_its_finding(self):
        for mutation, finding in MUTATIONS.items():
            with self.subTest(mutation=mutation.__name__):
                self.assertIn(finding, check_matrix(mutated(mutation)))

    def test_host_observed_with_receipt_passes(self):
        def observed(m):
            c = cell(m, "workflow-tracks", "pre-flight")
            c["evidence"].update(status="host-observed", receipt="evidence/hv-1.json")

        self.assertEqual(check_matrix(mutated(observed)), [])

    def test_deferral_sentences_may_name_enforcement(self):
        def deferred(m):
            cell(m, "batch", "continuous")["notes"] += " Enforcement is not provided here."

        self.assertEqual(check_matrix(mutated(deferred)), [])

    def test_non_object_inputs_fail_closed(self):
        for value in (None, [], "matrix", 3):
            with self.subTest(value=value):
                self.assertEqual(check_matrix(value), ["matrix-not-object"])
        self.assertIn("cells-missing", check_matrix({}))


if __name__ == "__main__":
    unittest.main()
