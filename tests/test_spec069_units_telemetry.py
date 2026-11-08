# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T014 (REQ-014 / SC-014, procedure_014): telemetry, shadow and platform controls for ``units``."""

from __future__ import annotations

import json
import ntpath
import os
import posixpath
import tempfile
import threading
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_braid import system_one_shadow as shadow
from agent_braid import tooling_mcp, tooling_telemetry, units
from agent_braid.analysis import InvalidAnalysis
from agent_braid.tooling_mcp import ToolingConfig, ToolingService
from scripts import spec069_generate_corpus as generator
from tests.test_system_one_shadow import counter_uuid

SENTINEL = "SENTINEL-9c1d77e0"
unit = generator.unit
request = generator.units_request


def conflicting_request() -> dict:
    return request(unit(f"{SENTINEL}-a", ("write", "README.md")), unit(f"{SENTINEL}-b", ("write", "./README.md")))


class ServiceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source, self.results, self.store = self.base / "source", self.base / "results", self.base / "store"
        self.source.mkdir()
        self.results.mkdir()
        for target, name in ((shadow, "default_directory"), (tooling_telemetry, "default_directory")):
            patcher = patch.object(target, name, return_value=self.store if target is shadow else self.base / "metrics")
            patcher.start()
            self.addCleanup(patcher.stop)
        with shadow._refusal_lock:
            shadow._refusals.clear()
        self.addCleanup(shadow.flush)

    def service(self, **kwargs) -> ToolingService:
        return ToolingService(ToolingConfig(self.source, self.results, **kwargs))

    def call(self, service, payload, kind="units"):
        envelope = service.invoke("analyze-work", {"kind": kind, "request": payload}, threading.Event())
        self.assertTrue(shadow.flush(), "shadow worker did not finish")
        return envelope

    def episodes(self) -> list[dict]:
        lines = []
        for path in sorted(self.store.glob("episodes-*.jsonl")):
            lines.extend(json.loads(line) for line in path.read_bytes().splitlines())
        return lines


class ShadowTests(ServiceCase):
    def test_units_call_records_one_valid_episode_with_its_own_kind(self):
        envelope = self.call(self.service(system_one="shadow"), conflicting_request())
        self.assertEqual(envelope["status"], "ok")
        episodes = self.episodes()
        self.assertEqual(len(episodes), 1, shadow.refusal_counts())
        shadow.validate_episode(episodes[0])
        self.assertEqual((episodes[0]["operation"], episodes[0]["analysisKind"]), ("analyze-work", "units"))
        self.assertEqual(episodes[0]["classificationCounts"]["conflicting"], 1)
        self.assertEqual(shadow.refusal_counts(), {})

    def test_episode_takes_effect_kinds_from_the_constructed_records(self):
        self.call(self.service(system_one="shadow"), request(unit("a", ("read", "x.txt")), unit("b", ("write", "x.txt"))))
        pair = self.episodes()[0]["pairs"][0]
        self.assertEqual(pair["effectKinds"], {"left": ["read"], "right": ["write"]})

    def test_episode_holds_no_request_string(self):
        self.call(self.service(system_one="shadow"), conflicting_request())
        stored = b"".join(p.read_bytes() for p in self.store.glob("episodes-*.jsonl"))
        for text in (SENTINEL, "README", "./README"):
            self.assertNotIn(text.encode(), stored)

    def test_envelope_is_identical_with_shadow_off_and_on(self):
        def run(mode):
            with patch.object(tooling_mcp, "uuid", counter_uuid()):
                envelope = self.call(self.service(system_one=mode), conflicting_request())
            return json.dumps(envelope, sort_keys=True)

        off = run("off")
        self.assertEqual(self.episodes(), [])
        self.assertEqual(off, run("shadow"))
        self.assertEqual(len(self.episodes()), 1)

    def test_refused_units_call_records_nothing(self):
        envelope = self.call(self.service(system_one="shadow"), request(unit("a", ("write", "../x"))))
        self.assertEqual(envelope["status"], "refused")
        self.assertEqual(self.episodes(), [])
        self.assertEqual(shadow.refusal_counts(), {})

    def test_shadow_guard_failure_is_counted_and_the_envelope_is_unchanged(self):
        expected = json.dumps(self.call(self.service(system_one="off"), conflicting_request()), sort_keys=True,
                              default=str)
        with patch.object(shadow, "submit", side_effect=RuntimeError("boom")):
            actual = self.call(self.service(system_one="shadow"), conflicting_request())
        self.assertEqual(actual["status"], "ok")
        self.assertEqual(json.loads(expected)["status"], "ok")
        self.assertEqual(shadow.refusal_counts(), {"internal-error": 1})
        self.assertEqual(self.episodes(), [])

    def test_oversized_artifact_result_still_records_an_episode(self):
        with patch.object(tooling_mcp, "INLINE_RESULT_BYTES", 100):
            envelope = self.call(self.service(system_one="shadow"), conflicting_request())
        self.assertEqual(envelope["result"]["type"], "evidence-artifact-reference")
        episodes = self.episodes()
        self.assertEqual(len(episodes), 1, shadow.refusal_counts())
        self.assertEqual(episodes[0]["analysisKind"], "units")


class TelemetryTests(ServiceCase):
    def rows(self):
        return {(r["operation"], r["outcome"], r["metric"], r["bucket"]): r["count"]
                for r in tooling_telemetry.Store().report()["rows"]}

    def test_accepted_units_call_has_a_defined_outcome_and_classification(self):
        self.call(self.service(telemetry="local"), conflicting_request())
        rows = self.rows()
        self.assertEqual(rows[("analyze-work", "ok", "calls", "all")], 1)
        self.assertEqual(rows[("analyze-work", "ok", "classification", "conflicting")], 1)

    def test_refused_units_call_has_the_refused_outcome_and_a_reason(self):
        self.call(self.service(telemetry="local"), request(unit("a", ("write", "/etc/x"))))
        rows = self.rows()
        self.assertEqual(rows[("analyze-work", "refused", "calls", "all")], 1)
        self.assertEqual(sum(v for k, v in rows.items() if k[2] == "refusal-reason"), 1)
        self.assertFalse([k for k in rows if k[1] == "error"])


class PlatformTests(unittest.TestCase):
    """Normalization is pure string logic: the same bytes on macOS, Linux and Windows path semantics."""

    def build(self, payload):
        return json.dumps(units.construct(payload, "0" * 32), sort_keys=True)

    def test_construction_ignores_the_host_path_flavour(self):
        payload = request(unit("a", ("write", "./docs//a.md")), unit("b", ("read", "docs/a.md/")))
        expected = self.build(payload)
        for flavour, sep in ((ntpath, "\\"), (posixpath, "/")):
            with patch.object(os, "path", flavour), patch.object(os, "sep", sep):
                self.assertEqual(self.build(payload), expected, flavour.__name__)

    def test_windows_style_paths_are_refused_on_every_platform(self):
        for value in ("docs\\a.md", "C:/a.md", "C:\\a.md", "\\\\server\\share\\a", "/a", "//server/share"):
            with self.subTest(value=value), self.assertRaises(InvalidAnalysis):
                units.normalize_resource(value, "/units/0/effects/0/resource")

    def test_decomposed_unicode_from_macos_equals_composed_unicode(self):
        composed = "caf\u00e9/\u00c5.md"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(units.normalize_resource(decomposed, "/p"), units.normalize_resource(composed, "/p"))
        self.assertEqual(units.normalize_resource(composed, "/p"), composed)

    def test_case_insensitive_file_systems_cannot_hide_a_collision(self):
        payload = request(unit("a", ("write", "Readme.md")), unit("b", ("write", "README.md")))
        with self.assertRaises(InvalidAnalysis) as caught:
            units.validate(payload)
        self.assertEqual(caught.exception.code, "case-only-duplicate-resource")


if __name__ == "__main__":
    unittest.main()
