# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T010: agent-braid-loom/v0.1 contract, strict parsing and parity with the schema."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from agent_braid import view_loom
from agent_braid.view_loom import LoomError, canonical_bytes, parse_event, parse_stream, validate_event

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "specs/061-activity-viewer/contracts"
FIXTURES = Path(__file__).resolve().parent / "fixtures/view/loom"
SCHEMA = json.loads((CONTRACTS / "loom-event.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
CTL = "\x01"  # no trailing newline: Python's `$` would let jsonschema accept it


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


EXAMPLE = read_events(CONTRACTS / "loom-event.example.jsonl")
CORPUS = read_events(FIXTURES / "valid-corpus.jsonl")


def by_kind(events, kind):
    return deepcopy(next(event for event in events if event["kind"] == kind))


def schema_ok(event):
    return not list(VALIDATOR.iter_errors(event))


def spec_schema(spec):
    """Translate a view_loom field spec into its JSON Schema fragment."""
    tag = spec[0]
    if tag == "ident":
        return {"type": "string", "pattern": view_loom.IDENTIFIER_PATTERN}
    if tag == "text":
        return {"type": "string", "maxLength": view_loom.TEXT_MAX_LENGTH, "pattern": view_loom.TEXT_PATTERN}
    if tag == "enum":
        return {"enum": list(spec[1])}
    if tag == "const":
        return {"const": spec[1]}
    if tag == "bool":
        return {"type": "boolean"}
    if tag == "int":
        bounds = {"minimum": spec[1]} if spec[2] is None else {"minimum": spec[1], "maximum": spec[2]}
        return {"type": "integer", **bounds}
    if tag == "number":
        return {"type": "number", "minimum": spec[1], "maximum": spec[2]}
    if tag == "null":
        return {"anyOf": [spec_schema(spec[1]), {"type": "null"}]}
    if tag == "list":
        return {"type": "array", "maxItems": spec[2], "items": spec_schema(spec[1])}
    if tag == "object":
        return {"type": "object", "additionalProperties": False, "required": list(spec[1]),
                "properties": {name: spec_schema(child) for name, child in spec[1].items()}}
    raise AssertionError(tag)


class ParityTests(unittest.TestCase):
    def test_constants_match_schema(self):
        props = SCHEMA["properties"]
        self.assertEqual(view_loom.SCHEMA_VERSION, props["schemaVersion"]["const"])
        self.assertEqual(list(view_loom.KINDS), props["kind"]["enum"])
        self.assertEqual(list(view_loom.AT_BASES), props["at"]["properties"]["basis"]["enum"])
        self.assertEqual(list(view_loom.ADAPTERS), props["source"]["properties"]["adapter"]["enum"])
        self.assertEqual(list(view_loom.HOSTS), props["source"]["properties"]["host"]["enum"])
        self.assertEqual(list(view_loom.VERIFICATIONS), props["source"]["properties"]["verification"]["enum"])
        self.assertEqual(view_loom.MAX_SEQ, props["seq"]["maximum"])
        self.assertEqual(sorted(SCHEMA["required"]), sorted(view_loom.EVENT_FIELDS))
        ref = props["source"]["properties"]["evidenceRef"]["anyOf"][1]["properties"]
        self.assertEqual(view_loom.EVIDENCE_PATH_PATTERN, ref["path"]["pattern"])
        self.assertEqual(view_loom.EVIDENCE_PATH_MAX_LENGTH, ref["path"]["maxLength"])
        self.assertEqual(view_loom.SHA256_PATTERN, ref["sha256"]["pattern"])
        self.assertEqual(16 * 1024, view_loom.MAX_LINE_BYTES)
        self.assertEqual(50_000, view_loom.MAX_EVENTS)

    def test_gap_reasons_match_schema_and_are_closed(self):
        gap = next(c for c in SCHEMA["allOf"] if c["if"]["properties"]["kind"].get("const") == "observation.gap")
        schema_reasons = gap["then"]["properties"]["data"]["properties"]["reason"]["enum"]
        self.assertEqual(list(view_loom.GAP_REASONS), schema_reasons)
        self.assertEqual(7, len(view_loom.GAP_REASONS))

    def test_data_specs_match_schema_for_every_kind(self):
        branches = {c["if"]["properties"]["kind"]["const"]: c["then"]["properties"]["data"]
                    for c in SCHEMA["allOf"] if "data" in c["then"]["properties"]}
        self.assertEqual(set(view_loom.KINDS), set(branches))
        self.assertEqual(set(view_loom.KINDS), set(view_loom.DATA_SPECS))
        for kind in view_loom.KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(branches[kind], spec_schema(("object", view_loom.DATA_SPECS[kind])))

    def test_class_rules_match_schema(self):
        rules = {c["if"]["properties"]["kind"].get("const"): c["then"]["properties"]["assurance"]
                 for c in SCHEMA["allOf"] if "assurance" in c["then"]["properties"]}
        self.assertEqual({"type": "integer"}, rules["crossing.classified"]["properties"]["compatibilityClass"])
        self.assertEqual({"const": 0}, rules["gate.result"]["properties"]["compatibilityClass"])
        self.assertEqual(("crossing.classified",), view_loom.CLASS_REQUIRED_KINDS)
        self.assertEqual({"gate.result": 0}, dict(view_loom.CLASS_FIXED_KINDS))
        schema_null = SCHEMA["allOf"][-1]["if"]["properties"]["kind"]["enum"]
        expected_null = set(view_loom.KINDS) - set(view_loom.CLASS_REQUIRED_KINDS) - set(dict(view_loom.CLASS_FIXED_KINDS))
        self.assertEqual(sorted(schema_null), sorted(expected_null))

    def test_example_and_corpus_validate_in_both(self):
        for name, events in (("example", EXAMPLE), ("corpus", CORPUS)):
            for event in events:
                with self.subTest(name=name, seq=event["seq"], kind=event["kind"]):
                    self.assertTrue(schema_ok(event))
                    self.assertIs(event, validate_event(event))

    def test_example_lines_are_canonical(self):
        raw = (CONTRACTS / "loom-event.example.jsonl").read_bytes()
        self.assertEqual(raw, b"".join(canonical_bytes(event) for event in EXAMPLE))
        self.assertEqual(EXAMPLE, parse_stream(raw))

    def test_corpus_covers_every_kind_and_reason(self):
        self.assertEqual(set(view_loom.KINDS), {event["kind"] for event in CORPUS})
        gap_reasons = {e["data"]["reason"] for e in CORPUS if e["kind"] == "observation.gap"}
        self.assertEqual(set(view_loom.GAP_REASONS), gap_reasons)
        raw = (FIXTURES / "valid-corpus.jsonl").read_bytes()
        self.assertEqual(CORPUS, parse_stream(raw))


def _drop(*path):
    def go(event):
        node = event
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]
    return go


def _set(*path_and_value):
    *path, value = path_and_value

    def go(event):
        node = event
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return go


def _top(field, value):
    return lambda event: event.__setitem__(field, value)


# (label, event kind to start from, mutation). Every one must be refused by validate_event and by the schema.
VIOLATIONS = [
    ("unknown kind", "strand.open", _top("kind", "strand.explode")),
    ("executionAuthorization true", "strand.open", _top("executionAuthorization", True)),
    ("executionAuthorization missing", "strand.open", _drop("executionAuthorization")),
    ("executionAuthorization 0", "strand.open", _top("executionAuthorization", 0)),
    ("crossing class null", "crossing.classified", _set("assurance", "compatibilityClass", None)),
    ("crossing class out of range", "crossing.classified", _set("assurance", "compatibilityClass", 6)),
    ("crossing class text", "crossing.classified", _set("assurance", "compatibilityClass", "1")),
    ("effort with class", "effort.sample", _set("assurance", "compatibilityClass", 1)),
    ("analysis report with class", "analysis.report", _set("assurance", "compatibilityClass", 0)),
    ("gate result class 1", "gate.result", _set("assurance", "compatibilityClass", 1)),
    ("gate result class null", "gate.result", _set("assurance", "compatibilityClass", None)),
    ("gate status outside enum", "gate.result", _set("data", "status", "ok")),
    ("gate phase outside enum", "gate.phase", _set("data", "phase", "deploy")),
    ("gate phase status outside enum", "gate.phase", _set("data", "status", "passed")),
    ("runtime phase outside enum", "runtime.phase", _set("data", "phase", "running")),
    ("grant action outside enum", "grant.issued", _set("data", "action", "apply")),
    ("C0 in free text", "strand.open", _set("data", "label", "a" + CTL + "b")),
    ("C1 in free text", "strand.open", _set("data", "label", "a\x85b")),
    ("DEL in free text", "strand.open", _set("data", "label", "a\x7fb")),
    ("bidi override in free text", "strand.open", _set("data", "label", "a\u202eb")),
    ("bidi isolate in free text", "strand.open", _set("data", "label", "a\u2067b")),
    ("free text too long", "strand.open", _set("data", "label", "x" * 257)),
    ("missing verification", "strand.open", _drop("source", "verification")),
    ("unknown verification", "strand.open", _set("source", "verification", "trusted")),
    ("coverage outside enum", "crossing.classified", _set("data", "evidence", "coverage", ["full"])),
    ("identifier with space", "strand.open", _set("data", "strandId", "not valid")),
    ("identifier uppercase digest", "strand.open", _set("data", "strandId", "sha256:" + "A" * 64)),
    ("identifier too long", "strand.open", _set("data", "strandId", "a" * 65)),
    ("evidence path absolute", "analysis.report", _set("source", "evidenceRef", "path", "/etc/passwd")),
    ("evidence path drive", "analysis.report", _set("source", "evidenceRef", "path", "C:/x")),
    ("evidence path dotdot", "analysis.report", _set("source", "evidenceRef", "path", "a/../b")),
    ("evidence path backslash", "analysis.report", _set("source", "evidenceRef", "path", "a\\b")),
    ("evidence path too long", "analysis.report", _set("source", "evidenceRef", "path", "a" * 513)),
    ("evidence hash uppercase", "analysis.report", _set("source", "evidenceRef", "sha256", "A" * 64)),
    ("notAGuarantee false", "strand.open", _set("assurance", "notAGuarantee", False)),
    ("extra top-level member", "strand.open", _top("extra", 1)),
    ("extra data member", "strand.open", _set("data", "extra", 1)),
    ("missing data member", "strand.open", _drop("data", "role")),
    ("wrong schema version", "strand.open", _top("schemaVersion", "agent-braid-loom/v0.2")),
    ("seq zero", "strand.open", _top("seq", 0)),
    ("seq above 2^53-1", "strand.open", _top("seq", 2 ** 53)),
    ("seq boolean", "strand.open", _top("seq", True)),
    ("at basis outside enum", "strand.open", _set("at", "basis", "wall-clock")),
    ("at relMs negative", "strand.open", _set("at", "relMs", -1)),
    ("gap reason outside enum", "observation.gap", _set("data", "reason", "because")),
    ("adapter outside enum", "strand.open", _set("source", "adapter", "mystery")),
    ("host outside enum", "strand.open", _set("source", "host", "gemini")),
    ("effort basis not host-estimate", "effort.sample", _set("data", "basis", "measured")),
    ("effort negative tokens", "effort.sample", _set("data", "inputTokens", -1)),
    ("effort cost above cap", "effort.sample", _set("data", "costUsd", 1_000_000.5)),
    ("too many crossing reasons", "crossing.classified", _set("data", "reasons", ["r"] * 9)),
    ("wave index above 63", "wave.started", _set("data", "wave", 64)),
    ("too many hazard units", "hazard.noticed", _set("data", "units", ["u"] * 129)),
    ("derived flag not boolean", "grant.issued", _set("data", "derived", "yes")),
]


class SeededViolationTests(unittest.TestCase):
    def test_every_violation_is_refused_with_a_stable_reason_and_by_the_schema(self):
        for label, kind, mutate in VIOLATIONS:
            with self.subTest(label):
                event = by_kind(CORPUS, kind)
                mutate(event)
                with self.assertRaises(LoomError) as raised:
                    validate_event(event)
                self.assertIn(raised.exception.reason, view_loom.REASONS)
                self.assertTrue(raised.exception.detail)
                self.assertFalse(schema_ok(event))

    def test_non_object_events_are_refused(self):
        for value in (["not", "an", "object"], None, "x", 1):
            with self.subTest(value=value):
                with self.assertRaises(LoomError) as raised:
                    validate_event(value)
                self.assertEqual("not-an-object", raised.exception.reason)

    def test_reasons_are_stable_for_the_named_controls(self):
        def reason(kind, mutate):
            event = by_kind(CORPUS, kind)
            mutate(event)
            with self.assertRaises(LoomError) as raised:
                validate_event(event)
            return raised.exception.reason

        self.assertEqual("unknown-kind", reason("strand.open", _top("kind", "nope")))
        self.assertEqual("execution-authorization", reason("strand.open", _top("executionAuthorization", True)))
        self.assertEqual("execution-authorization", reason("strand.open", _drop("executionAuthorization")))
        self.assertEqual("compatibility-class", reason("crossing.classified", _set("assurance", "compatibilityClass", None)))
        self.assertEqual("compatibility-class", reason("gate.result", _set("assurance", "compatibilityClass", 2)))
        self.assertEqual("compatibility-class", reason("effort.sample", _set("assurance", "compatibilityClass", 0)))
        self.assertEqual("free-text", reason("strand.open", _set("data", "label", "a\x00b")))
        self.assertEqual("identifier", reason("strand.open", _set("data", "strandId", "no way")))
        self.assertEqual("evidence-path", reason("analysis.report", _set("source", "evidenceRef", "path", "../x")))

    def test_integer_fields_refuse_floats_and_booleans(self):
        for value in (1.0, True, "1"):
            with self.subTest(value=value):
                event = by_kind(CORPUS, "wave.started")
                event["data"]["wave"] = value
                with self.assertRaises(LoomError):
                    validate_event(event)

    def test_cost_accepts_integer_and_float_but_not_non_finite(self):
        event = by_kind(CORPUS, "effort.sample")
        for value in (0, 1, 0.25, None):
            event["data"]["costUsd"] = value
            validate_event(event)
        for value in (float("nan"), float("inf")):
            event["data"]["costUsd"] = value
            with self.assertRaises(LoomError):
                validate_event(event)

    def test_validate_does_not_mutate_its_input(self):
        event = by_kind(CORPUS, "crossing.classified")
        before = deepcopy(event)
        validate_event(event)
        self.assertEqual(before, event)


class StrictJsonTests(unittest.TestCase):
    def line(self, kind="strand.open"):
        return canonical_bytes(by_kind(CORPUS, kind)).rstrip(b"\n")

    def test_canonical_bytes_are_sorted_compact_newline_terminated_utf8(self):
        event = by_kind(CORPUS, "strand.open")
        event["data"]["label"] = "caf\u00e9 \u2713"
        out = canonical_bytes(event)
        self.assertTrue(out.endswith(b"}\n"))
        self.assertEqual(1, out.count(b"\n"))
        self.assertIn('"label":"caf\u00e9 \u2713"'.encode("utf-8"), out)
        self.assertNotIn(b", ", out)
        self.assertNotIn(b": ", out)
        self.assertEqual(out, canonical_bytes(json.loads(out)))
        keys = json.loads(out, object_pairs_hook=lambda pairs: [key for key, _ in pairs])
        self.assertEqual(sorted(keys), keys)

    def test_canonical_bytes_refuse_invalid_events_and_oversize(self):
        event = by_kind(CORPUS, "strand.open")
        event["executionAuthorization"] = True
        with self.assertRaises(LoomError):
            canonical_bytes(event)
        event = by_kind(CORPUS, "analysis.report")
        event["data"]["uncertainty"] = ["\u20ac" * 256] * 16
        event["data"]["limits"] = ["\u20ac" * 256] * 16
        with self.assertRaises(LoomError) as raised:
            canonical_bytes(event)
        self.assertEqual("line-too-long", raised.exception.reason)

    def test_parse_event_round_trip(self):
        line = self.line()
        expected = by_kind(CORPUS, "strand.open")
        self.assertEqual(expected, parse_event(line))
        self.assertEqual(expected, parse_event(line.decode("utf-8")))
        self.assertEqual(expected, parse_event(line + b"\n"))

    def test_duplicate_members_are_refused_at_any_depth(self):
        nested = self.line().replace(b'"label":', b'"role":"agent","label":', 1)
        raws = (b'{"seq":1,"seq":2}', nested, (FIXTURES / "duplicate-key.jsonl").read_bytes())
        for raw in raws:
            with self.subTest(raw=raw[:40]):
                with self.assertRaises(LoomError) as raised:
                    parse_event(raw)
                self.assertEqual("duplicate-key", raised.exception.reason)

    def test_non_finite_numbers_are_refused(self):
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            with self.subTest(token=token):
                raw = self.line("effort.sample").replace(b'"costUsd":0.25', b'"costUsd":' + token)
                self.assertIn(token, raw)
                with self.assertRaises(LoomError) as raised:
                    parse_event(raw)
                self.assertEqual("non-finite-number", raised.exception.reason)
        with self.assertRaises(LoomError) as raised:
            parse_stream((FIXTURES / "nan.jsonl").read_bytes())
        self.assertEqual("non-finite-number", raised.exception.reason)

    def test_malformed_lines_are_refused(self):
        raws = (b"", b"\n", b"   ", b"{", b"[]", b"null", b'"x"', b"1", b'{"a":1}{"b":2}', b"\xff\xfe{}",
                b"[" * 5000 + b"]" * 5000)
        for raw in raws:
            with self.subTest(raw=raw[:20]):
                with self.assertRaises(LoomError) as raised:
                    parse_event(raw)
                self.assertIn(raised.exception.reason, view_loom.REASONS)

    def test_line_limit_is_16_kib_exclusive_of_the_terminator(self):
        event = by_kind(CORPUS, "strand.open")
        body = canonical_bytes(event).rstrip(b"\n")
        exact = body + b" " * (view_loom.MAX_LINE_BYTES - len(body))
        self.assertEqual(view_loom.MAX_LINE_BYTES, len(exact))
        self.assertEqual(event, parse_event(exact))
        self.assertEqual([event], parse_stream(exact + b"\n"))
        over = exact + b" "
        with self.assertRaises(LoomError) as raised:
            parse_event(over)
        self.assertEqual("line-too-long", raised.exception.reason)
        with self.assertRaises(LoomError) as raised:
            parse_stream(exact + b"\n" + over + b"\n")
        self.assertEqual("line-too-long", raised.exception.reason)

    def test_multibyte_characters_count_as_bytes_against_the_line_limit(self):
        event = by_kind(CORPUS, "strand.open")
        event["data"]["label"] = "\u20ac" * 256
        body = canonical_bytes(event).rstrip(b"\n")
        self.assertEqual(event, parse_event(body))
        with self.assertRaises(LoomError):
            parse_event(body + b" " * (view_loom.MAX_LINE_BYTES - len(body) + 1))


class StreamTests(unittest.TestCase):
    def stream(self, *seqs):
        out = b""
        for seq in seqs:
            event = by_kind(CORPUS, "strand.close")
            event["seq"] = seq
            out += canonical_bytes(event)
        return out

    def test_valid_stream_with_gaps_in_seq_is_accepted(self):
        events = parse_stream(self.stream(1, 2, 7, 900))
        self.assertEqual([1, 2, 7, 900], [e["seq"] for e in events])
        self.assertEqual([], parse_stream(b""))
        self.assertEqual(1, len(parse_stream(self.stream(5).rstrip(b"\n"))))

    def test_repeated_or_decreasing_seq_is_refused_and_no_prefix_is_returned(self):
        for seqs in ((1, 1), (2, 1), (1, 2, 2), (1, 3, 2), (5, 4, 6)):
            with self.subTest(seqs=seqs):
                with self.assertRaises(LoomError) as raised:
                    parse_stream(self.stream(*seqs))
                self.assertEqual("seq-order", raised.exception.reason)
        for name in ("duplicate-seq.jsonl", "decreasing-seq.jsonl"):
            with self.subTest(name=name):
                with self.assertRaises(LoomError) as raised:
                    parse_stream((FIXTURES / name).read_bytes())
                self.assertEqual("seq-order", raised.exception.reason)

    def test_a_bad_last_line_refuses_the_whole_stream(self):
        bad = self.stream(3).replace(b'"executionAuthorization":false', b'"executionAuthorization":true')
        with self.assertRaises(LoomError):
            parse_stream(self.stream(1, 2) + bad)

    def test_blank_lines_are_refused(self):
        with self.assertRaises(LoomError) as raised:
            parse_stream(self.stream(1) + b"\n" + self.stream(2))
        self.assertEqual("blank-line", raised.exception.reason)

    def test_error_names_the_line(self):
        with self.assertRaises(LoomError) as raised:
            parse_stream(self.stream(1, 2) + b"{\n")
        self.assertEqual(3, raised.exception.line)

    def test_event_count_limit(self):
        template = self.stream(1).replace(b'"seq":1,', b'"seq":%d,')
        self.assertIn(b"%d", template)

        def build(count):
            return b"".join(template % number for number in range(1, count + 1))

        self.assertEqual(view_loom.MAX_EVENTS, len(parse_stream(build(view_loom.MAX_EVENTS))))
        with self.assertRaises(LoomError) as raised:
            parse_stream(build(view_loom.MAX_EVENTS + 1))
        self.assertEqual("too-many-events", raised.exception.reason)


class ReadOnlyBoundaryTests(unittest.TestCase):
    def test_execution_authorization_is_constant_false(self):
        self.assertIs(False, view_loom.EXECUTION_AUTHORIZATION)
        for event in EXAMPLE + CORPUS:
            self.assertIs(False, event["executionAuthorization"])

    def test_module_has_no_ownership_import_or_command_names(self):
        source = (ROOT / "agent_braid/view_loom.py").read_text(encoding="utf-8")
        for command in ("expand-ownership", "check-ownership", "audit-isolation", "report-recovery"):
            self.assertNotIn(command, source)
        self.assertNotIn("import ownership", source)
        self.assertNotIn("from agent_braid import ownership", source)
        self.assertNotIn("agent_braid.ownership", source)


if __name__ == "__main__":
    unittest.main()
