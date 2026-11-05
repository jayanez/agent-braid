# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T034 (REQ-015 / SC-015, procedure_015; the receipt part of procedure_014): the viewer documentation.

The guide must state the boundaries (loopback only, read-only, ephemeral effort, explicit recording, minimal
default export, `host-estimate`, no speedup claim, host-verification status per host), document exactly the
commands, options, artifact names, exit codes and retention bounds the code has, and every relative link must
resolve. Host-verification receipts must have their required fields and agree with the surfaces matrix.
"""
import argparse
import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from agent_braid import plugin_mcp, view_cli
from agent_braid.view_tail import KNOWN_ARTIFACTS, MAX_ROOTS

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "tooling" / "VIEWER.md"
BUNDLE_README = ROOT / "integrations" / "agent-braid-view" / "README.md"
TOOLING_INDEX = ROOT / "docs" / "tooling" / "README.md"
SPEC = ROOT / "specs" / "061-activity-viewer"
MATRIX = SPEC / "contracts" / "surfaces-matrix.json"
RECEIPTS = sorted((SPEC / "evidence").glob("hv-*.json"))
DOCUMENTS = (GUIDE, BUNDLE_README)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
OUTCOMES = {"verified", "not-matching", "unobserved"}
RECEIPT_FIELDS = {"task", "host", "os", "outcome", "limits", "matrixRows"}


def text(path):
    return path.read_text(encoding="utf-8")


def view_parsers():
    root = argparse.ArgumentParser()
    view_cli.add_parser(root.add_subparsers(dest="command", required=True))
    view = root._subparsers._group_actions[0].choices["view"]
    return view._subparsers._group_actions[0].choices


def run_view(*arguments):
    root = argparse.ArgumentParser()
    view_cli.add_parser(root.add_subparsers(dest="command", required=True))
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = view_cli.run(root.parse_args(["view", *arguments]))
        except SystemExit as exit_:
            code = exit_.code
    return code


class StatementTests(unittest.TestCase):
    GUIDE_TEXT = text(GUIDE)

    def test_the_guide_states_every_boundary(self):
        lowered = " ".join(self.GUIDE_TEXT.lower().split())
        for statement in ("loopback only", "read-only", "ephemeral", "explicit", "minimal", "host-estimate",
                          "no page or export claims a speedup", "not a guarantee", "executionauthorization: false",
                          "never uploaded", "never shows a path", "writes nothing", "vis.1b"):
            with self.subTest(statement):
                self.assertIn(statement, lowered)

    def test_vis1b_features_are_not_presented_as_available(self):
        section = self.GUIDE_TEXT.split("## What it is and is not", 1)[1].split("## Install", 1)[0]
        self.assertIn("are **VIS.1b** and are not available", section)
        self.assertIn("None of that exists in this release", section)
        self.assertIn("`--host codex` is accepted and reports that it is not available yet", self.GUIDE_TEXT)

    def test_the_guide_links_the_plugin_privacy_statement_and_the_tooling_index_links_the_guide(self):
        self.assertIn("(PLUGIN_PRIVACY.md)", self.GUIDE_TEXT)
        self.assertIn("(VIEWER.md)", text(TOOLING_INDEX))
        self.assertIn("(../../docs/tooling/VIEWER.md)", text(BUNDLE_README))

    def test_the_banner_example_matches_what_serve_prints(self):
        self.assertIn("root 1: ", self.GUIDE_TEXT)
        self.assertIn("the page shows only these labels", self.GUIDE_TEXT)
        self.assertIn("the page shows only these labels", text(ROOT / "agent_braid" / "view_cli.py"))


class CodeAgreementTests(unittest.TestCase):
    GUIDE_TEXT = text(GUIDE)

    def test_every_subcommand_and_option_of_the_cli_is_documented(self):
        parsers = view_parsers()
        self.assertEqual(set(parsers), {"serve", "open", "validate", "env"})
        for name, parser in parsers.items():
            self.assertIn(f"view {name}", self.GUIDE_TEXT)
            for action in parser._actions:
                for option in action.option_strings:
                    if option not in {"-h", "--help"}:
                        with self.subTest(command=name, option=option):
                            self.assertRegex(self.GUIDE_TEXT, rf"(?<![\w-]){re.escape(option)}(?![\w-])")

    def test_every_watched_artifact_name_is_documented_and_no_other_is(self):
        paragraph = self.GUIDE_TEXT.split("**Watched artifacts.**", 1)[1].split("\n\n", 1)[0]
        documented = set(re.findall(r"`([a-z-]+\.json)`", paragraph))
        self.assertEqual(documented, set(KNOWN_ARTIFACTS))

    def test_the_root_bound_and_the_retention_bounds_are_the_code_values(self):
        self.assertEqual(MAX_ROOTS, 8)
        self.assertIn("at most 8 roots", self.GUIDE_TEXT)
        self.assertEqual((plugin_mcp.REPORT_COPY_DAYS, plugin_mcp.REPORT_COPY_MAX_BYTES,
                          plugin_mcp.REPORT_COPY_MAX_COUNT), (30, 64 * 1024 * 1024, 1500))
        self.assertIn("removed after 30 days", self.GUIDE_TEXT)
        self.assertIn("64 MiB or 1,500", self.GUIDE_TEXT)

    def test_the_source_surfaces_are_the_documented_ones(self):
        self.assertEqual(view_cli.SURFACES, ("web", "mod", "tui", "mcp-app"))
        for surface in view_cli.SURFACES:
            self.assertIn(f"`{surface}`", self.GUIDE_TEXT)

    def test_the_documented_exit_codes_are_the_ones_the_commands_return(self):
        table = self.GUIDE_TEXT.split("### Exit codes", 1)[1].split("##", 1)[0]
        self.assertEqual(re.findall(r"^\| (\d) \|", table, re.MULTILINE), ["0", "1", "2"])
        with tempfile.TemporaryDirectory() as directory:
            fixtures = ROOT / "tests" / "fixtures" / "view" / "loom"
            valid = fixtures / "valid-corpus.jsonl"
            bad = Path(directory) / "bad.jsonl"
            bad.write_text("not json\n", encoding="utf-8")
            self.assertEqual(run_view("validate", str(valid)), 0)
            self.assertEqual(run_view("validate", str(bad)), 1)
            self.assertEqual(run_view("validate", str(Path(directory) / "missing.jsonl")), 2)
            self.assertEqual(run_view("serve", "--surface", "tui"), 2)
            self.assertEqual(run_view("env", "--host", "codex"), 2)


class LinkTests(unittest.TestCase):
    def test_every_relative_link_resolves(self):
        for document in DOCUMENTS:
            links = LINK.findall(text(document))
            self.assertTrue(links, document.name)
            for link in links:
                if re.match(r"[a-z][a-z0-9+.-]*:", link) or link.startswith("#"):
                    continue
                with self.subTest(document=document.name, link=link):
                    self.assertTrue((document.parent / link.split("#", 1)[0]).exists())

    def test_the_guide_has_the_spdx_header_of_documentation(self):
        for document in DOCUMENTS:
            self.assertTrue(text(document).startswith("<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->"))


class HostVerificationTests(unittest.TestCase):
    GUIDE_TEXT = text(GUIDE)
    MATRIX_ROWS = json.loads(text(MATRIX))["rows"]

    def test_the_guide_status_table_agrees_with_the_surfaces_matrix(self):
        listed = re.findall(r"^\| ([a-z-]+) \| ([a-z]+) \| ([a-z-]+) \| ([a-z-]+) \|$", self.GUIDE_TEXT, re.MULTILINE)
        listed = {row[:3]: row[3] for row in listed if row[0] != "Host"}
        self.assertTrue(listed)
        matrix = {(row["host"], row["client"], row["surface"]): row["status"] for row in self.MATRIX_ROWS}
        for key, status in listed.items():
            with self.subTest(row=key):
                self.assertEqual(matrix[key], status)
        observed = {key for key, status in matrix.items() if status in {"verified", "hv-pending", "not-matching",
                                                                         "unobserved"}}
        self.assertEqual(observed, set(listed))

    def test_each_receipt_has_its_required_fields_and_a_valid_outcome(self):
        self.assertGreaterEqual(len(RECEIPTS), 3)
        for path in RECEIPTS:
            receipt = json.loads(text(path))
            with self.subTest(path.name):
                self.assertLessEqual(RECEIPT_FIELDS, set(receipt))
                self.assertIn(receipt["outcome"], OUTCOMES)
                self.assertTrue(receipt["limits"])
                self.assertTrue("command" in receipt or "steps" in receipt)

    def test_a_verified_matrix_row_comes_from_a_verified_receipt(self):
        matrix = {(row["host"], row["client"], row["surface"]): row["status"] for row in self.MATRIX_ROWS}
        for path in RECEIPTS:
            for row in json.loads(text(path))["matrixRows"]:
                key = (row["host"], row["client"], row["surface"])
                with self.subTest(path.name, row=key):
                    self.assertEqual(matrix[key], row["status"])
                if row["status"] == "verified":
                    self.assertEqual(json.loads(text(path))["outcome"], "verified")


if __name__ == "__main__":
    unittest.main()
