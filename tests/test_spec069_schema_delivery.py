# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T005 (procedure_005, offline part): per-kind schemas inside the analyze-work tool definition."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import types as pytypes
import unittest
from pathlib import Path
from unittest import mock

import jsonschema

from agent_braid import analyze_work_schema, plugin_mcp
from agent_braid import tooling_mcp as core
from scripts import spec069_tool_schemas as generator

# The analyze-work definition served before T005 (alpha.7 plus PR #1099): the description-only arm.
INTERIM_INPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"kind": {"enum": ["aim", "git"]},
                   "request": {"oneOf": [{"type": "object"}, {"type": "array"}],
                               "description": core._ANALYZE_WORK_REQUEST_HELP}},
    "required": ["kind", "request"]}
PLAIN_TOP_LEVEL = {"type", "additionalProperties", "properties", "required", "$defs"}


class Tool:
    """Stand-in for mcp.types.Tool exposing the attribute names the plugin listing writes into."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.input_schema = kwargs["inputSchema"]
        self.output_schema = kwargs.get("outputSchema")


FAKE_TYPES = pytypes.SimpleNamespace(Tool=Tool, ToolAnnotations=lambda **kw: kw)


def top_level_violations(schema: dict, *, delegated: bool = True) -> list[str]:
    """Why a tool inputSchema is not a plain object with properties (and required, A1); empty when it is.

    The plugin's two bootstrap tools take no arguments and receive no `workspaceId`, so they declare no
    `required` list (`delegated=False`).
    """
    found = [f"top-level keyword {key}" for key in sorted(set(schema) - PLAIN_TOP_LEVEL)]
    if schema.get("type") != "object":
        found.append("type is not object")
    if not isinstance(schema.get("properties"), dict):
        found.append("properties missing")
    if delegated and not isinstance(schema.get("required"), list):
        found.append("required missing")
    return found


def cap_violation(definition: dict) -> str | None:
    """The D12 refusal for a model-facing definition over the cap, naming the fallback; None under it."""
    tokens = generator.approximate_tokens(definition)
    if tokens <= generator.TOKEN_CAP:
        return None
    return (f"{definition['name']} needs ~{tokens} tokens ({generator.TOKEN_APPROXIMATION}) over the D12 cap "
            f"of {generator.TOKEN_CAP}: serve the description-only fallback "
            "(python -m scripts.spec069_tool_schemas --delivery description-only) or raise the cap by a reviewed change")


class _Router:
    def __init__(self, services):
        self.services = services


class SchemaDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        for name in ("s", "r"):
            (base / name).mkdir()
        self.service = plugin_mcp.WorkspaceService("ws", core.ToolingConfig(base / "s", base / "r"))
        self.runtime = plugin_mcp.WorkspaceService("ws-runtime", core.ToolingConfig(
            base / "s", base / "r", grant_store=base / "grants", runtime_enabled=True))

    def tearDown(self):
        self.temp.cleanup()

    def analyze_work(self, delivery=None):
        return {item.name: item for item in core._tool_definitions(self.service, FAKE_TYPES, delivery)}["analyze-work"]

    def listed(self, *services):
        return {item.name: item for item in plugin_mcp.tool_listing(_Router(
            {service.identifier: service for service in services or (self.service,)}), FAKE_TYPES)}

    @staticmethod
    def model_facing(tool):
        return {"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}

    # --- build-time generation ------------------------------------------------
    def test_generated_schemas_equal_a_fresh_regeneration_byte_for_byte(self):
        self.assertEqual(generator.render("per-kind"), generator.OUTPUT.read_text(encoding="utf-8"))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(generator.main(["--check"]), 0)

    def test_the_committed_build_serves_the_per_kind_arm_with_its_sources_hashed(self):
        self.assertEqual(analyze_work_schema.DELIVERY, "per-kind")
        self.assertEqual(analyze_work_schema.KINDS, tuple(generator.KIND_SOURCES))
        built = generator.build()
        self.assertEqual(analyze_work_schema.SOURCES, built["sources"])
        self.assertEqual(set(built["sources"]), set(generator.KIND_SOURCES.values())
                         | {"schemas/0.2.0-draft/agent-interaction-metadata.schema.json"})

    def test_negative_control_drift_from_a_published_schema_is_detected(self):
        published = generator._published()
        identifier = "https://agent-braid.dev/schemas/0.2.0-draft/agent-interaction-metadata.schema.json"
        where, document = published[identifier]
        relaxed = copy.deepcopy(document)
        del relaxed["properties"]["instanceId"]["pattern"]
        with mock.patch.object(generator, "_published", return_value=dict(published, **{identifier: (where, relaxed)})):
            self.assertNotEqual(generator.render("per-kind"), generator.OUTPUT.read_text(encoding="utf-8"))

    def test_annotations_are_stripped_but_property_names_are_kept(self):
        schemas = json.loads(analyze_work_schema.SCHEMAS)
        text = json.dumps(schemas)
        for keyword in ('"$id"', '"$schema"', '"$comment"', '"title"'):
            self.assertNotIn(keyword, text)
        envelope = schemas["request"]["oneOf"][0]
        # `description` is a property of the envelope's source object, not an annotation.
        self.assertEqual(envelope["properties"]["source"]["required"], ["kind", "description"])
        self.assertIn("description", envelope["properties"]["source"]["properties"])
        self.assertNotIn('"$defs":', json.dumps(schemas["request"]))  # shared definitions live at the top level only

    def test_the_generator_refuses_constructs_it_does_not_translate(self):
        compactor = generator._Compactor()
        for node in ({"if": {"type": "string"}}, {"$ref": "#/$defs/x", "type": "object"},
                     {"$ref": "https://example.invalid/other.schema.json"}):
            with self.assertRaises(generator.GeneratorError, msg=node):
                compactor.schema(node, {"$defs": {"x": {}}})
        with self.assertRaises(generator.GeneratorError):
            generator.render("anything")

    # --- tool definition (A1) -------------------------------------------------
    def test_both_arms_keep_a_plain_object_top_level(self):
        for delivery in generator.DELIVERIES:
            schema = self.analyze_work(delivery).inputSchema
            self.assertEqual(top_level_violations(schema), [], delivery)
            self.assertEqual(schema["required"], ["kind", "request"])
            jsonschema.Draft202012Validator.check_schema(schema)

    def test_negative_control_a_top_level_one_of_is_flagged(self):
        schema = self.analyze_work().inputSchema
        self.assertIn("top-level keyword oneOf", top_level_violations(dict(schema, oneOf=[{"type": "object"}])))
        self.assertTrue(top_level_violations({"oneOf": [schema]}))

    def test_per_kind_arm_declares_one_labelled_branch_per_request_form(self):
        schema = self.analyze_work("per-kind").inputSchema
        self.assertEqual(schema["properties"]["kind"], {"enum": list(analyze_work_schema.KINDS)})
        request = schema["properties"]["request"]
        self.assertEqual(request["type"], ["object", "array"])
        labels = [branch["description"] for branch in request["oneOf"]]
        self.assertEqual(labels, ["kind=aim envelope", "kind=aim agent-interaction-metadata",
                                  "kind=aim records", "kind=git"])
        self.assertEqual(sorted(schema["$defs"]), ["agentInteractionMetadata", "effect"])
        self.assertNotIn("description", request)

    def test_description_only_arm_is_the_interim_definition_byte_for_byte(self):
        work = self.analyze_work("description-only")
        self.assertEqual(core._json_bytes(work.inputSchema), core._json_bytes(INTERIM_INPUT_SCHEMA))
        self.assertEqual(work.description, self.analyze_work("per-kind").description)

    def test_the_ablation_switch_changes_only_the_delivery_line(self):
        committed = generator.OUTPUT.read_text(encoding="utf-8").splitlines()
        ablation = generator.render("description-only").splitlines()
        self.assertEqual([(a, b) for a, b in zip(committed, ablation) if a != b],
                         [("DELIVERY = 'per-kind'", "DELIVERY = 'description-only'")])
        with mock.patch.object(analyze_work_schema, "DELIVERY", "description-only"):
            self.assertEqual(self.analyze_work().inputSchema, INTERIM_INPUT_SCHEMA)
        with self.assertRaises(ValueError):
            self.analyze_work("unknown")

    def test_each_listing_returns_fresh_schemas(self):
        first = self.analyze_work().inputSchema
        first["$defs"].clear()
        first["properties"]["request"]["oneOf"].clear()
        self.assertTrue(self.analyze_work().inputSchema["$defs"])

    # --- plugin list_tools (A1) -----------------------------------------------
    def test_plugin_listing_injects_workspace_id_into_every_tool_of_both_arms(self):
        for delivery in generator.DELIVERIES:
            with self.subTest(delivery=delivery), mock.patch.object(analyze_work_schema, "DELIVERY", delivery):
                tools = self.listed(self.service, self.runtime)
                self.assertEqual(set(tools), {"plugin-status", "workspaces", "analyze-work", "analyze", "prepare",
                                              "status", "execute", "recover", "verify"})
                for name, tool in tools.items():
                    schema = tool.input_schema
                    delegated = name not in {"plugin-status", "workspaces"}
                    self.assertEqual(top_level_violations(schema, delegated=delegated), [], name)
                    jsonschema.Draft202012Validator.check_schema(schema)
                    if delegated:
                        self.assertEqual(schema["properties"]["workspaceId"], {"type": "string"}, name)
                        self.assertEqual(schema["required"].count("workspaceId"), 1, name)
                work = tools["analyze-work"].input_schema
                self.assertEqual(work["required"], ["kind", "request", "workspaceId"])
                self.assertEqual("$defs" in work, delivery == "per-kind")

    def test_plugin_listing_accepts_a_valid_call_and_refuses_a_missing_workspace(self):
        sample = json.loads((generator.ROOT / "examples/analysis/file-edits.json").read_text())
        validator = jsonschema.Draft202012Validator(self.listed()["analyze-work"].input_schema)
        self.assertTrue(validator.is_valid({"workspaceId": "ws", "kind": "aim", "request": sample}))
        self.assertFalse(validator.is_valid({"kind": "aim", "request": sample}))
        self.assertFalse(validator.is_valid({"workspaceId": "ws", "kind": "units", "request": sample}))

    def test_negative_control_a_top_level_one_of_breaks_the_plugin_listing(self):
        def nested(service, types, delivery=None):
            return [types.Tool(name="analyze-work", description="d", inputSchema={"oneOf": [{"type": "object"}]},
                               outputSchema={"properties": {}})]
        with mock.patch.object(core, "_tool_definitions", nested):
            with self.assertRaises(KeyError):
                self.listed()

    # --- size cap (D12) -------------------------------------------------------
    def test_model_facing_definitions_are_under_the_d12_cap(self):
        for delivery in generator.DELIVERIES:
            with mock.patch.object(analyze_work_schema, "DELIVERY", delivery):
                for name, tool in self.listed(self.runtime).items():
                    self.assertIsNone(cap_violation(self.model_facing(tool)), f"{delivery}/{name}")

    def test_negative_control_an_oversized_definition_fails_and_names_the_fallback(self):
        tool = self.model_facing(self.listed()["analyze-work"])
        padded = dict(tool, description=tool["description"] + " x" * 2000)
        message = cap_violation(padded)
        self.assertIsNotNone(message)
        self.assertIn("--delivery description-only", message)
        self.assertGreater(generator.approximate_tokens(padded), generator.TOKEN_CAP)

    def test_the_approximation_counts_only_the_model_facing_fields_in_compact_utf8(self):
        definition = {"name": "n", "description": "é", "inputSchema": {"type": "object"}, "outputSchema": {"x": 1}}
        raw = generator.model_facing_bytes(definition)
        self.assertEqual(raw, '{"name":"n","description":"é","inputSchema":{"type":"object"}}'.encode())
        self.assertEqual(generator.approximate_tokens(definition), -(-len(raw) * 10 // 37))


if __name__ == "__main__":
    unittest.main()
