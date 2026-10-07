# SPDX-License-Identifier: AGPL-3.0-only
"""Predeclared structural projection controls, independent of compiler outputs."""
from contextlib import ExitStack
import json
from pathlib import Path
import unittest
import threading
from unittest.mock import patch

from agent_braid import system_one_schema as schema
from agent_braid.system_one import CancellationToken, canonical, digest, thaw

_FIXTURES = Path(__file__).resolve().parents[1] / "specs/032-system-one-product/fixtures"


def object_schema(properties, definitions=None):
    value = dict(type="object", properties=properties, required=list(properties), additionalProperties=False)
    if definitions is not None:
        value["$defs"] = definitions
    return value


class SchemaTests(unittest.TestCase):
    def assert_packet(self, result):
        value = thaw(result)
        self.assertIs(value["executionAuthorization"], False)
        self.assertEqual(value["evidenceClass"], "heuristic")
        self.assertEqual(value["packetDigest"], digest({k: v for k, v in value.items() if k != "packetDigest"}))
        return value

    def refusal(self, document, reason):
        raw = document if type(document) is bytes else canonical(document)
        result = self.assert_packet(schema.compile_schema(raw))
        self.assertEqual(result["reasonCodes"], [reason])
        self.assertIsNone(result["schemaDigest"])
        self.assertEqual(result["questions"], [])
        self.assertEqual(result["bindings"], [])
        self.assertEqual(set(result), {"contractVersion", "schemaDigest", "questions", "bindings", "reasonCodes", "evidenceClass", "executionAuthorization", "packetDigest"})
        return result

    def test_frozen_corpus(self):
        corpus = json.loads((_FIXTURES / "schema-compiler.json").read_text())
        for case in corpus["cases"]:
            with self.subTest(case=case["caseId"]), ExitStack() as stack:
                token = CancellationToken()
                controls = case.get("controls", {})
                if controls.get("cancelBeforePublication"):
                    original = schema._packet
                    def cancelled_packet(fields):
                        result = original(fields)
                        if "reasonCodes" not in fields:
                            token.cancel()
                        return result
                    stack.enter_context(patch.object(schema, "_packet", side_effect=cancelled_packet))
                if "monotonicBeforePublicationMs" in controls:
                    # Only publication advances time; no sleeps or expected generation.
                    original = schema._packet
                    times = [0]
                    def late_packet(fields):
                        result = original(fields)
                        if "reasonCodes" not in fields:
                            times[0] = 5000000000
                        return result
                    stack.enter_context(patch.object(schema, "_packet", side_effect=late_packet))
                    stack.enter_context(patch.object(schema, "_monotonic_ns", side_effect=lambda: times[0]))
                result = self.assert_packet(schema.compile_schema(canonical(case["schema"]), cancellation=token))
                expected = case["expected"]
                if "packetDigest" in expected:
                    self.assertEqual(result, expected)
                else:
                    for key, value in expected.items():
                        self.assertEqual(result[key], value)
                    self.assertIsNone(result["schemaDigest"])

    def test_hand_declared_chained_object_reference(self):
        document = object_schema({"payload": {"$ref": "#/$defs/A"}}, {
            "A": {"$ref": "#/$defs/B"},
            "B": object_schema({"ready": {"type": "boolean"}, "mode": {"enum": ["off", "on"]}}),
        })
        result = self.assert_packet(schema.compile_schema(canonical(document)))
        self.assertEqual(result["schemaDigest"], "5d4d6872d34bcec549a142e4cc74efb434f7707b0bf467f52e56df467c5baee2")
        self.assertEqual(result["packetDigest"], "62b95ae3b0f460f3434b9309a0bb3aa0ff647081830f3eac9a8b0622787bf173")
        self.assertEqual([(b["instancePointer"], b["schemaPointer"], b["resolvedSchemaPointer"]) for b in result["bindings"]], [
            ("/payload/mode", "/properties/payload", "/$defs/B/properties/mode"),
            ("/payload/ready", "/properties/payload", "/$defs/B/properties/ready"),
        ])
        self.assertEqual([q["id"] for q in result["questions"]], [
            "0c69ab2b47f485e6f91cd602fbbdcef8fc0c5763bd322984f0e9a824ed1737c4",
            "5c9a8e7c2bd32ef332ab90f0a53d8cca443716d48cb84923c0df3714db91282e",
        ])

    def test_two_aliases_and_nested_reference_keep_original_identity(self):
        doc = object_schema({"a": {"$ref": "#/$defs/O"}, "b": {"$ref": "#/$defs/O"}}, {
            "O": object_schema({"leaf": {"$ref": "#/$defs/L"}}), "L": {"type": "boolean"},
        })
        result = self.assert_packet(schema.compile_schema(canonical(doc)))
        self.assertEqual([(b["instancePointer"], b["schemaPointer"], b["resolvedSchemaPointer"]) for b in result["bindings"]], [
            ("/a/leaf", "/properties/a", "/$defs/L"), ("/b/leaf", "/properties/b", "/$defs/L"),
        ])
        self.assertNotEqual(result["questions"][0]["id"], result["questions"][1]["id"])

    def test_parser_and_builtin_bytes(self):
        for raw in [bytearray(b'{"type":"boolean"}'), memoryview(b'{}'), '{}', b'{} trailing',
                    b'\xef\xbb\xbf{}', b'{"type":"boolean","type":"boolean"}',
                    b'{"enum":[NaN,0]}', b'{"enum":[1e999,0]}', b'{"enum":[9223372036854775808,0]}',
                    b'{"enum":["\\ud800","x"]}', b'x' * 1048577]:
            with self.subTest(raw=type(raw)):
                result = self.assert_packet(schema.compile_schema(raw))
                self.assertEqual(result["reasonCodes"], ["invalid-schema"])
        result = self.assert_packet(schema.compile_schema(b'{"type":"boolean"}' + b' ' * (1048576 - 18)))
        self.assertNotIn("reasonCodes", result)

    def test_unused_definitions_and_object_cycles(self):
        self.refusal(object_schema({"ok": {"type": "boolean"}}, {"unused": {"type": "string"}}), "unsupported-shape")
        self.refusal(object_schema({"ok": {"type": "boolean"}}, {"unused": {"$ref": "#/$defs/missing"}}), "invalid-local-reference")
        self.refusal(object_schema({"x": {"$ref": "#/$defs/O"}}, {"O": object_schema({"again": {"$ref": "#/$defs/O"}})}), "reference-cycle")
        self.refusal(object_schema({"ok": {"type": "boolean"}}, {"unused": {"$ref": "#/$defs/unused"}}), "reference-cycle")

    def test_pointer_resolution_never_decodes_percent(self):
        for ref in ["#/%24defs/L", "#/$defs/%4c", "#/$defs/~2L", "#", "file:///secret", "#/$defs/L/enum/0"]:
            self.refusal(object_schema({"x": {"$ref": ref}}, {"L": {"enum": [False, True]}}), "invalid-local-reference")
        document = object_schema({"x": {"$ref": "#/$defs/%4c"}}, {"%4c": {"type": "boolean"}})
        result = self.assert_packet(schema.compile_schema(canonical(document)))
        self.assertEqual(result["bindings"][0]["resolvedSchemaPointer"], "/$defs/%4c")

    def test_question_node_reference_and_depth_limits(self):
        self.refusal(object_schema({str(i): {"type": "boolean"} for i in range(33)}), "compiler-budget-exceeded")
        self.assertEqual(len(schema.compile_schema(canonical(object_schema({str(i): {"type": "boolean"} for i in range(32)})))["questions"]), 32)
        # 1 root + 1 property + 128 unused definitions + 127 other properties
        # exceeds combined syntax/expansion budget before any publication.
        self.refusal(object_schema({str(i): {"type": "boolean"} for i in range(127)}, {str(i): {"type": "boolean"} for i in range(128)}), "compiler-budget-exceeded")
        self.refusal(object_schema({"ok": {"type": "boolean"}}, {str(i): {"type": "boolean"} for i in range(129)}), "unsupported-shape")
        def chain(length):
            return object_schema({"x": {"$ref": "#/$defs/n0"}}, {f"n{i}": ({"$ref": f"#/$defs/n{i+1}"} if i < length - 1 else {"type": "boolean"}) for i in range(length)})
        self.assertNotIn("reasonCodes", schema.compile_schema(canonical(chain(16))))
        self.refusal(chain(17), "compiler-budget-exceeded")
        document = {"type": "boolean"}
        for _ in range(8):
            document = object_schema({"x": document})
        self.refusal(document, "invalid-schema")

    def test_combined_counter_exact_boundary(self):
        # Syntax159 + expansion97 =256; one unused definition adds one visit.
        doc = object_schema({f"p{i}": {"$ref": "#/$defs/B"} for i in range(32)}, {"B": {"$ref": "#/$defs/d0"}, **{f"d{i}": {"type": "boolean"} for i in range(125)}})
        self.assertNotIn("reasonCodes", schema.compile_schema(canonical(doc)))
        doc["$defs"]["last"] = {"type": "boolean"}
        self.refusal(doc, "compiler-budget-exceeded")

    def test_enums_types_and_sanitized_unknowns(self):
        for value in [{"enum": [1, 2], "type": ["integer", "null"]}, {"enum": [None, "x"], "type": ["null", "null"]},
                      {"enum": [None, "x"], "type": ["null", {}]}, {"enum": [False, 0], "type": "integer"},
                      {"enum": [1, 2], "type": "number", "x-agent-braid-ordinal": False},
                      {"enum": ["x" * 257, "y"]}, {"enum": [[], "y"]}, {"enum": [1, 2], "$defs": {}},
                      object_schema({"bad\x7f": {"type": "boolean"}})]:
            self.refusal(value, "unsupported-shape")
        result = self.refusal({"type": "boolean", "SYNTHETIC_PRIVATE_SENTINEL": "secret"}, "unsupported-keyword")
        self.assertNotIn("SYNTHETIC_PRIVATE_SENTINEL", canonical(result).decode())

    def test_immutable_and_id_collision(self):
        result = schema.compile_schema(canonical({"enum": ["a", "b"]}))
        with self.assertRaises(TypeError):
            result["bindings"][0]["options"][0]["value"] = "c"
        copied = thaw(result)
        copied["questions"][0]["options"][0]["description"] = "other"
        self.assertEqual(result["questions"][0]["options"][0]["description"], '"a"')
        original = schema.digest
        with patch.object(schema, "digest", side_effect=lambda value: "0" * 64 if type(value) is dict and set(value) == {"type", "value"} else original(value)):
            self.refusal({"enum": ["a", "b"]}, "id-collision")

    def test_token_reuse_invalid_token_and_publication_precedence(self):
        with self.assertRaisesRegex(TypeError, "invalid cancellation token"):
            schema.compile_schema(b'{}', cancellation=object())
        token = CancellationToken()
        token.claim()
        try:
            with self.assertRaises(ValueError):
                schema.compile_schema(b'{"type":"boolean"}', cancellation=token)
        finally:
            token.release()
        now = [0]
        original = schema._packet
        def boundary(fields):
            result = original(fields)
            if "reasonCodes" not in fields:
                token.cancel()
                now[0] = 5000000000
            return result
        with patch.object(schema, "_packet", side_effect=boundary), patch.object(schema, "_monotonic_ns", side_effect=lambda: now[0]):
            result = self.assert_packet(schema.compile_schema(b'{"type":"boolean"}', cancellation=token))
        self.assertEqual(result["reasonCodes"], ["cancelled"])
        token.claim()
        token.release()

    def test_real_token_cancellation_race_suppresses_publication(self):
        entered, release = threading.Event(), threading.Event()
        token = CancellationToken()
        outcomes, errors = [], []
        original = schema._packet
        def boundary(fields):
            result = original(fields)
            if "reasonCodes" not in fields:
                entered.set()
                if not release.wait(2):
                    raise AssertionError("barrier timeout")
            return result
        def worker():
            try:
                outcomes.append(schema.compile_schema(b'{"type":"boolean"}', cancellation=token))
            except Exception as exc:
                errors.append(exc)
        with patch.object(schema, "_packet", side_effect=boundary):
            thread = threading.Thread(target=worker)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaises(ValueError):
                    schema.compile_schema(b'{"type":"boolean"}', cancellation=token)
                token.cancel()
            finally:
                release.set()
                thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(outcomes), 1)
        result = self.assert_packet(outcomes[0])
        self.assertEqual(result["reasonCodes"], ["cancelled"])
        self.assertEqual(result["questions"], [])

    def test_zero_dispatch(self):
        import socket
        import subprocess
        from agent_braid import system_one, system_one_backends
        with patch.object(socket, "socket", side_effect=AssertionError("network")), patch.object(subprocess, "Popen", side_effect=AssertionError("process")), patch.object(system_one, "evaluate", side_effect=AssertionError("evaluation")), patch.object(system_one_backends, "DecisionRuntime", side_effect=AssertionError("admission")):
            self.assertNotIn("reasonCodes", schema.compile_schema(b'{"type":"boolean"}'))
