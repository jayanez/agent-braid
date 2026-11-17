# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T406: the owner GO packet reports the evidence, records nothing and works with no data."""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from agent_braid import system_one_dp1_rule as rule, system_one_promotion as promotion, system_one_shadow as shadow
from research import s15b_outcome_observer as observer
from scripts import spec066_go_packet as packet_script

TODAY = date(2026, 11, 28)
INDEPENDENT = "likely-independent"


def joined(kind, answer=INDEPENDENT):
    return {"outcomeKind": kind, observer.RULE_ANSWER_FIELD: answer, "day": "2026-11-20"}


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.home = self.base / "state"
        self.home.mkdir(mode=0o700)
        self.store = self.base / "system-one"  # absent: the empty store
        patch = mock.patch.object(shadow, "default_directory", lambda: self.store)
        patch.start()
        self.addCleanup(patch.stop)

    def build(self, *, episodes=0, unknown=0, advised=0, outcomes=()):
        report = {"totals": {"episodes": episodes}, "unknownPairs": unknown}
        with mock.patch.object(shadow, "report", lambda: report), \
                mock.patch.object(observer, "read_episodes", lambda today, counts: counts.update({"advised-pairs": advised}) or []), \
                mock.patch.object(packet_script, "_stored_outcomes", lambda: list(outcomes)):
            return packet_script.build_packet(TODAY, home=self.home)

    def go(self):
        promotion.owner_go(self.home, "DP-1", backend_kind=promotion.RULE_BACKEND_KIND, evidence_digest="b" * 64,
                           manifest_digest=rule.manifest_digest(), decided_on="2026-11-30")


class TruthTable(Base):
    def test_no_data_reports_zeros_and_an_uninformative_bound_from_the_real_empty_state(self):
        value = packet_script.build_packet(TODAY, home=self.home)  # nothing patched but the empty store
        self.assertEqual((value["shadowEpisodes"], value["advisedPairs"], value["joinedOutcomes"],
                          value["falseIndependent"], value["wilson95Upper"], value["coverage"]),
                         (0, 0, 0, 0, None, None))
        self.assertEqual(value["verdict"], "no-evidence")
        self.assertIsNone(value["registry"]["latest"])
        text = packet_script.render(value)
        self.assertIn("uninformative", text)
        self.assertIn("empty, DP-1 stays shadow", text)
        self.assertFalse(promotion.path(self.home).exists())  # reading created nothing

    def test_zero_errors_gives_a_finite_bound_and_coverage(self):
        value = self.build(episodes=29, unknown=40, advised=10,
                           outcomes=[joined("merge-clean")] * 5 + [joined("merge-clean", "undetermined")])
        self.assertEqual((value["joinedOutcomes"], value["advisedTrials"], value["falseIndependent"]), (6, 5, 0))
        self.assertAlmostEqual(value["coverage"], 0.25)
        self.assertGreater(value["wilson95Upper"], 0)
        self.assertLess(value["wilson95Upper"], 1)
        self.assertEqual(value["verdict"], "ready-for-owner-decision")
        text = packet_script.render(value)
        self.assertIn("10 advised of 40 unknown (25.0%)", text)
        self.assertNotIn("uninformative", text)

    def test_false_independence_blocks_the_verdict(self):
        value = self.build(episodes=29, unknown=40, advised=10,
                           outcomes=[joined("merge-clean")] * 4 + [joined("merge-conflict")])
        self.assertEqual((value["advisedTrials"], value["falseIndependent"]), (5, 1))
        self.assertEqual(value["verdict"], "blocked-false-independence")
        self.assertIn("review it before any go", packet_script.render(value))

    def test_conflict_on_an_unanswered_pair_is_not_a_false_independence(self):
        value = self.build(outcomes=[joined("merge-conflict", None), joined("merge-conflict", "undetermined")])
        self.assertEqual(value["falseIndependent"], 0)

    def test_registry_already_holding_a_go_is_reported_and_not_repeated(self):
        self.go()
        before = promotion.path(self.home).read_bytes()
        value = self.build(episodes=3, unknown=4, advised=2, outcomes=[joined("merge-clean")])
        self.assertEqual(value["registry"]["latest"]["decision"], "go")
        self.assertEqual(value["registry"]["ifConfigured"]["advise"]["activeMode"], "advise")
        text = packet_script.render(value)
        self.assertIn("A go is already recorded", text)
        self.assertNotIn("--confirm <previewDigest>\n   Only this step", text)
        self.assertIn("--rollback", text)
        self.assertEqual(promotion.path(self.home).read_bytes(), before)  # never records

    def test_rolled_back_registry_names_the_reason_and_offers_a_new_go(self):
        self.go()
        promotion.auto_rollback_false_independence(self.home, "DP-1", false_independent_days=["2026-12-01"],
                                                   decided_on="2026-12-01")
        text = packet_script.render(self.build())
        self.assertIn(promotion.AUTO_ROLLBACK_REASON, text)
        self.assertIn("a new go supersedes it", text)


class Rendering(Base):
    def test_packet_holds_every_owner_command_and_date(self):
        text = packet_script.render(self.build())
        for needle in ("plugin setup --system-one advise", "system-one promote --decision-point DP-1 --go",
                       "--go --confirm <previewDigest>", "Reconnect", "--rollback",
                       "plugin setup --system-one shadow", "plugin setup --system-one off",
                       "2026-11-30", "2026-12-31", "records nothing", "merge conflict"):
            self.assertIn(needle, text)

    def test_main_prints_text_or_json_and_never_writes_the_registry(self):
        for argv in ([], ["--json"]):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(packet_script.main(argv, today=TODAY, home=self.home), 0)
            if argv:
                self.assertFalse(json.loads(out.getvalue())["executionAuthorization"])
            else:
                self.assertIn("GO decision packet", out.getvalue())
        self.assertFalse(promotion.path(self.home).exists())


if __name__ == "__main__":
    unittest.main()
