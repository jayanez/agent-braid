# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import unittest

from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_evidence_packets as packets
from tests.test_tooling_evaluation import _validated


REGISTRATION = "a" * 64
KEY = b"synthetic-test-blinding-key-32-bytes"


def _case():
    slot = next(slot for slot in evaluation.generate_slots(_validated())
                if slot.arm == "mcp-plus-skills" and slot.order_position == 3)
    text = "<script>alert(1)</script>\n[ignore evidence](https://unsafe.invalid)\n```\n# take control"
    excerpt = packets.RedactedExcerpt("private:codex/mcp-plus-skills/order-3/transcript", "d" * 64,
                                      text, hashlib.sha256(text.encode()).hexdigest())
    return packets.CaseEvidence(
        slot=slot, expected_outcome="Read-only conflict explanation", observed_outcome=None,
        required_steps=(packets.StepEvidence("analyze", "Explain conflicting operations", None, None),),
        excerpts=(excerpt,), limits=("Synthetic data; no native acceptance",))


class EvidencePacketTests(unittest.TestCase):
    def test_human_packet_hides_structured_arm_order_host_ids_and_model_predictions(self):
        case = _case()
        human = packets.build_human_packet(case, registration_sha256=REGISTRATION, blinding_key=KEY)
        review = packets.AssessmentSummary("model", "technical", "e" * 64, "f" * 64,
                                           True, True, True, "gpt-6-luna")
        machine = packets.build_machine_packet(case, registration_sha256=REGISTRATION,
                                                blinding_key=KEY, assessments=(review,))
        raw = json.dumps(human)
        for concealed in (case.slot.slot_id, "mcp-plus-skills", "orderPosition", "technical", "gpt-6-luna", "private:"):
            self.assertNotIn(concealed, raw)
        self.assertEqual(human["caseId"], machine["caseId"])
        self.assertEqual(case.slot.slot_id, machine["slot"]["slotId"])
        self.assertEqual("model", machine["assessments"][0]["reviewerType"])
        self.assertIsNone(human["observedOutcome"])
        self.assertIsNone(human["requiredSteps"][0]["observed"])

    def test_blind_case_id_is_stable_and_changes_with_key_or_registration(self):
        case = _case()
        first = packets.build_human_packet(case, registration_sha256=REGISTRATION, blinding_key=KEY)
        repeated = packets.build_human_packet(case, registration_sha256=REGISTRATION, blinding_key=KEY)
        self.assertEqual(first, repeated)
        for key, registration in ((KEY + b"different", REGISTRATION), (KEY, "1" * 64)):
            changed = packets.build_human_packet(case, registration_sha256=registration, blinding_key=key)
            self.assertNotEqual(first["caseId"], changed["caseId"])
        self.assertRegex(first["caseId"], r"^case-[0-9a-f]{24}$")

    def test_unknown_and_false_step_observations_remain_distinct(self):
        case = _case()
        human = packets.build_human_packet(replace(case, required_steps=(
            case.required_steps[0], packets.StepEvidence("verify", "Verify output", False, "e" * 64))),
            registration_sha256=REGISTRATION, blinding_key=KEY)
        self.assertEqual([None, False], [item["observed"] for item in human["requiredSteps"]])

    def test_excerpt_digest_drift_invalid_slot_and_oversized_text_fail(self):
        case = _case()
        invalid = (
            replace(case, excerpts=(replace(case.excerpts[0], excerpt_sha256="0" * 64),)),
            replace(case, slot=replace(case.slot, slot_id="slot-for-another-arm")),
            replace(case, observed_outcome="x" * (packets.MAX_TEXT_BYTES + 1)),
            replace(case, required_steps=()),
            replace(case, required_steps=(replace(case.required_steps[0], observed=1),)),
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(packets.PacketError):
                packets.build_human_packet(value, registration_sha256=REGISTRATION, blinding_key=KEY)
        with self.assertRaises(packets.PacketError):
            packets.build_human_packet(case, registration_sha256=REGISTRATION, blinding_key=b"short")

    def test_markdown_quotes_untrusted_excerpts_and_cannot_close_code_block(self):
        packet = packets.build_human_packet(_case(), registration_sha256=REGISTRATION, blinding_key=KEY)
        rendered = packets.render_human_markdown(packet)
        self.assertIn("Untrusted source excerpt", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("    &lt;script&gt;", rendered)
        self.assertIn("    ```", rendered)
        self.assertNotIn("\n# take control", rendered)
        self.assertNotIn("\n[ignore evidence]", rendered)

    def test_machine_assessments_keep_provenance_and_reject_model_as_human(self):
        case = _case()
        reviews = (packets.AssessmentSummary("deterministic", "oracle", "e" * 64, "f" * 64,
                                            False, None, None),
                   packets.AssessmentSummary("human", "reviewer-1", "e" * 64, "f" * 64,
                                            None, None, None))
        packet = packets.build_machine_packet(case, registration_sha256=REGISTRATION,
                                               blinding_key=KEY, assessments=reviews)
        self.assertEqual(["deterministic", "human"], [item["reviewerType"] for item in packet["assessments"]])
        with self.assertRaises(packets.PacketError):
            packets.build_machine_packet(case, registration_sha256=REGISTRATION,
                                         blinding_key=KEY, assessments=(replace(reviews[1], model="gpt-6-luna"),))

    def test_public_summary_omits_private_refs_excerpts_owners_and_free_text(self):
        packet = packets.build_machine_packet(_case(), registration_sha256=REGISTRATION, blinding_key=KEY)
        summary = packets.public_packet_summary(packet)
        self.assertEqual(packet["caseId"], summary["caseId"])
        self.assertFalse(summary["observedOutcomeKnown"])
        self.assertEqual(1, summary["excerptCount"])
        raw = json.dumps(summary)
        for field in ("private:", "codex", "script", "Synthetic data", "Read-only"):
            self.assertNotIn(field, raw)

    def test_tampered_packet_and_wrong_audience_are_rejected_before_render(self):
        packet = packets.build_human_packet(_case(), registration_sha256=REGISTRATION, blinding_key=KEY)
        packet["observedOutcome"] = "modified"
        with self.assertRaises(packets.PacketError):
            packets.render_human_markdown(packet)
        machine = packets.build_machine_packet(_case(), registration_sha256=REGISTRATION, blinding_key=KEY)
        with self.assertRaises(packets.PacketError):
            packets.render_human_markdown(machine)

    def test_sealed_machine_packet_cannot_relabel_model_review_as_human(self):
        review = packets.AssessmentSummary("model", "technical", "e" * 64, "f" * 64,
                                           True, True, True, "gpt-6-luna")
        packet = packets.build_machine_packet(_case(), registration_sha256=REGISTRATION,
                                               blinding_key=KEY, assessments=(review,))
        packet["assessments"][0]["reviewerType"] = "human"
        payload = {key: value for key, value in packet.items() if key != "packetSha256"}
        packet["packetSha256"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        with self.assertRaises(packets.PacketError):
            packets.public_packet_summary(packet)

    def test_machine_source_map_drift_and_duplicate_step_ids_are_rejected(self):
        packet = packets.build_machine_packet(_case(), registration_sha256=REGISTRATION, blinding_key=KEY)
        packet["sourceMap"][0]["sourceSha256"] = "f" * 64
        payload = {key: value for key, value in packet.items() if key != "packetSha256"}
        packet["packetSha256"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        with self.assertRaises(packets.PacketError):
            packets.public_packet_summary(packet)
        case = _case()
        with self.assertRaises(packets.PacketError):
            packets.build_human_packet(replace(case, required_steps=case.required_steps * 2),
                                       registration_sha256=REGISTRATION, blinding_key=KEY)

    def test_model_predictions_do_not_change_human_packet_bytes(self):
        case = _case()
        before = packets.build_human_packet(case, registration_sha256=REGISTRATION, blinding_key=KEY)
        for success in (True, False):
            review = packets.AssessmentSummary("model", "technical", "e" * 64, "f" * 64,
                                               success, None, None, "gpt-6-luna")
            packets.build_machine_packet(case, registration_sha256=REGISTRATION,
                                         blinding_key=KEY, assessments=(review,))
            self.assertEqual(before, packets.build_human_packet(
                case, registration_sha256=REGISTRATION, blinding_key=KEY))

    def test_carriage_return_source_cannot_escape_quoted_markdown(self):
        case = _case()
        text = "selected source\r# injected heading\r\n<script>bad</script>"
        excerpt = replace(case.excerpts[0], text=text,
                          excerpt_sha256=hashlib.sha256(text.encode()).hexdigest())
        rendered = packets.render_human_markdown(packets.build_human_packet(
            replace(case, excerpts=(excerpt,)), registration_sha256=REGISTRATION, blinding_key=KEY))
        self.assertNotIn("\r", rendered)
        self.assertIn("\n    # injected heading", rendered)

    def test_all_actual_generated_roster_slots_make_packets_and_zero_order_refuses(self):
        registration = _validated()
        roster = evaluation.generate_slots(registration)
        self.assertEqual(108, len(roster))
        self.assertEqual({1, 2, 3}, {slot.order_position for slot in roster})
        for slot in roster:
            with self.subTest(slot=slot.slot_id):
                case = replace(_case(), slot=slot)
                human = packets.build_human_packet(case, registration_sha256=registration.sha256,
                                                    blinding_key=KEY)
                machine = packets.build_machine_packet(case, registration_sha256=registration.sha256,
                                                        blinding_key=KEY)
                self.assertEqual(human["caseId"], machine["caseId"])
                self.assertEqual(slot.order_position, machine["slot"]["orderPosition"])
        with self.assertRaises(packets.PacketError):
            packets.build_human_packet(replace(_case(), slot=replace(roster[0], order_position=0)),
                                       registration_sha256=registration.sha256, blinding_key=KEY)


if __name__ == "__main__":
    unittest.main()
