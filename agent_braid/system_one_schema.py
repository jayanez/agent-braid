# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded structural schema projection; no evaluation or execution authority."""
from __future__ import annotations

from collections.abc import Mapping
import math
import re
from time import monotonic_ns as _monotonic_ns
from typing import Any

from agent_braid.system_one import CancellationToken, InvalidDecision, MAX_BYTES, canonical, digest, freeze, parse_json

from agent_braid.system_one_product_metadata import COMPILER_MANIFEST

VERSION = "s1-schema-synthetic-v1"
_INSTRUCTION = "Select the explicit schema value."


class _Refusal(Exception):
    def __init__(self, reason: str):
        self.reason = reason


def compiler_manifest() -> Mapping:
    """Return package metadata, without probing or importing a provider."""
    return freeze(COMPILER_MANIFEST)


def _packet(fields: dict) -> Mapping:
    fields.update(evidenceClass="heuristic", executionAuthorization=False)
    fields["packetDigest"] = digest(fields)
    return freeze(fields)


def _refused(reason: str) -> Mapping:
    return _packet(dict(contractVersion=VERSION, schemaDigest=None, questions=[], bindings=[], reasonCodes=[reason]))


def _escape(text: str) -> str:
    return text.replace("~", "~0").replace("/", "~1")


def _name(value: Any) -> bool:
    return (type(value) is str and bool(value) and len(value.encode("utf-8")) <= 256
            and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value))


def _kind(value: Any) -> str:
    return {str: "string", bool: "boolean", int: "integer", float: "number", type(None): "null"}.get(type(value), "invalid")


class _Compiler:
    def __init__(self, document: dict, deadline: int, token: CancellationToken | None):
        self.document = document
        self.deadline = deadline
        self.token = token
        self.visits = 0
        self.nodes: dict[str, dict] = {}
        self.children: dict[str, list[str]] = {}
        self.targets: dict[str, str] = {}
        self.questions: list[dict] = []
        self.bindings: list[dict] = []
        self.question_ids: set[str] = set()

    def check(self) -> None:
        if self.token is not None and self.token.cancelled:
            raise _Refusal("cancelled")
        if _monotonic_ns() >= self.deadline:
            raise _Refusal("deadline-exceeded")

    def visit(self) -> None:
        self.check()
        self.visits += 1
        if self.visits > 256:
            raise _Refusal("compiler-budget-exceeded")

    def validate(self, node: Any, pointer: str) -> None:
        self.visit()
        if type(node) is not dict:
            raise _Refusal("unsupported-shape")
        self.nodes[pointer] = node
        self.children[pointer] = []
        keys = set(node)
        if pointer == "" and "$schema" in keys:
            if node["$schema"] != "https://json-schema.org/draft/2020-12/schema":
                raise _Refusal("unsupported-shape")
            keys.remove("$schema")
        if "$ref" in keys:
            if keys != {"$ref"}:
                raise _Refusal("unsupported-shape")
            return
        allowed = {"type", "properties", "required", "additionalProperties", "$defs", "enum", "x-agent-braid-ordinal"}
        if keys - allowed:
            raise _Refusal("unsupported-keyword")
        if node.get("type") == "object":
            if keys not in ({"type", "properties", "required", "additionalProperties"}, {"type", "properties", "required", "additionalProperties", "$defs"}):
                raise _Refusal("unsupported-shape")
            props, required, defs = node["properties"], node["required"], node.get("$defs", {})
            if (type(props) is not dict or not props or type(required) is not list or node["additionalProperties"] is not False
                    or type(defs) is not dict or len(defs) > 128):
                raise _Refusal("unsupported-shape")
            if len(props) > 256:
                raise _Refusal("compiler-budget-exceeded")
            if (any(not _name(name) for name in props) or any(not _name(name) for name in defs)
                    or any(type(name) is not str for name in required) or len(required) != len(props)
                    or len(set(required)) != len(required) or set(required) != set(props)):
                raise _Refusal("unsupported-shape")
            for label, children in (("properties", props), ("$defs", defs)):
                for name in sorted(children):
                    child = pointer + "/" + label + "/" + _escape(name)
                    self.children[pointer].append(child)
                    self.validate(children[name], child)
        elif keys == {"type"} and node["type"] == "boolean":
            return
        elif "enum" in keys:
            ordinal = "x-agent-braid-ordinal" in keys
            expected = {"type", "enum", "x-agent-braid-ordinal"} if ordinal else keys & {"type", "enum"}
            if keys != expected:
                raise _Refusal("unsupported-shape")
            values = node["enum"]
            if type(values) is not list or not 2 <= len(values) <= 32:
                raise _Refusal("unsupported-shape")
            kinds = []
            for value in values:
                kind = _kind(value)
                if kind == "invalid" or (kind == "string" and len(value.encode("utf-8")) > 256):
                    raise _Refusal("unsupported-shape")
                if kind in ("integer", "number") and not math.isfinite(value):
                    raise _Refusal("unsupported-shape")
                kinds.append(kind)
            for index, value in enumerate(values):
                for prior, prior_kind in zip(values[:index], kinds[:index]):
                    if value == prior and (kinds[index] == prior_kind or {kinds[index], prior_kind} <= {"integer", "number"}):
                        raise _Refusal("unsupported-shape")
            if set(kinds) == {"null"}:
                raise _Refusal("unsupported-shape")
            if "type" in node:
                types = node["type"]
                if type(types) is list:
                    if (len(types) != 2 or any(type(t) is not str for t in types) or len(set(types)) != 2
                            or "null" not in types or "null" not in kinds or all(k == "null" for k in kinds)):
                        raise _Refusal("unsupported-shape")
                elif type(types) is str:
                    types = [types]
                else:
                    raise _Refusal("unsupported-shape")
                if any(t not in {"string", "boolean", "integer", "number", "null"} for t in types):
                    raise _Refusal("unsupported-shape")
                if any(k not in types and not (k == "integer" and "number" in types) for k in kinds):
                    raise _Refusal("unsupported-shape")
            if ordinal and (node["x-agent-braid-ordinal"] is not True or node.get("type") not in ("integer", "number")
                    or any(k not in ("integer", "number") or abs(v) > 1000000 for k, v in zip(kinds, values))
                    or any(a >= b for a, b in zip(values, values[1:]))):
                raise _Refusal("unsupported-shape")
        else:
            raise _Refusal("unsupported-shape")

    def resolve(self) -> None:
        for pointer, node in self.nodes.items():
            self.check()
            if "$ref" not in node:
                continue
            ref = node["$ref"]
            if type(ref) is not str or not ref.startswith("#/"):
                raise _Refusal("invalid-local-reference")
            parts = ref[2:].split("/")
            if any(re.search(r"~(?:[^01]|$)", part) for part in parts):
                raise _Refusal("invalid-local-reference")
            target = "".join("/" + _escape(part.replace("~1", "/").replace("~0", "~")) for part in parts)
            if target not in self.nodes:
                raise _Refusal("invalid-local-reference")
            self.targets[pointer] = target
        active, done = set(), set()
        def walk(pointer: str) -> None:
            self.check()
            if pointer in active:
                raise _Refusal("reference-cycle")
            if pointer in done:
                return
            active.add(pointer)
            for child in self.children[pointer]:
                walk(child)
            if pointer in self.targets:
                walk(self.targets[pointer])
            active.remove(pointer)
            done.add(pointer)
        for pointer in self.nodes:
            walk(pointer)

    def emit(self, pointer: str, instance: str, origin: str | None = None, edges: int = 0) -> None:
        self.visit()
        node = self.nodes[pointer]
        if "$ref" in node:
            if edges >= 16:
                raise _Refusal("compiler-budget-exceeded")
            self.emit(self.targets[pointer], instance, pointer if origin is None else origin, edges + 1)
            return
        if node.get("type") == "object":
            for name in sorted(node["properties"]):
                self.emit(pointer + "/properties/" + _escape(name), instance + "/" + _escape(name), origin, edges)
            return
        if len(self.questions) >= 32:
            raise _Refusal("compiler-budget-exceeded")
        schema_pointer = pointer if origin is None else origin
        question_id = digest(dict(instancePointer=instance, schemaPointer=schema_pointer))
        if question_id in self.question_ids:
            raise _Refusal("id-collision")
        self.question_ids.add(question_id)
        boolean = node.get("type") == "boolean" and "enum" not in node
        kind = "boolean" if boolean else "score" if "x-agent-braid-ordinal" in node else "choice"
        values = [False, True] if boolean else node["enum"]
        options, bindings, option_ids = [], [], set()
        for value in values:
            scalar = _kind(value)
            option_id = str(value).lower() if boolean else digest(dict(type=scalar, value=value))
            if option_id in option_ids:
                raise _Refusal("id-collision")
            option_ids.add(option_id)
            option = dict(id=option_id, description=canonical(value).decode("utf-8"))
            if kind == "score":
                option["value"] = value
            options.append(option)
            bindings.append(dict(optionId=option_id, scalarKind=scalar, value=value))
        self.questions.append(dict(id=question_id, type=kind, instructions=_INSTRUCTION, options=options))
        self.bindings.append(dict(questionId=question_id, instancePointer=instance, schemaPointer=schema_pointer,
                                  resolvedSchemaPointer=pointer, options=bindings))


def compile_schema(schema_bytes: bytes, *, cancellation: CancellationToken | None = None) -> Mapping:
    """Project the closed structural subset or return a sanitized complete refusal."""
    start = _monotonic_ns()
    if cancellation is not None and not isinstance(cancellation, CancellationToken):
        raise TypeError("invalid cancellation token")
    if cancellation is not None:
        cancellation.claim()
    try:
        compiler = _Compiler({}, start + 5000000000, cancellation)
        compiler.check()
        try:
            document = parse_json(schema_bytes)
            if len(canonical(document)) > MAX_BYTES:
                raise InvalidDecision()
        except InvalidDecision:
            return _refused("invalid-schema")
        compiler.document = document
        compiler.check()
        compiler.validate(document, "")
        compiler.resolve()
        compiler.emit("", "")
        fields = dict(contractVersion=VERSION, schemaDigest=digest(document), questions=compiler.questions, bindings=compiler.bindings)
        result = _packet(fields)
        def publish(cancelled: bool) -> Mapping:
            if cancelled:
                return _refused("cancelled")
            if _monotonic_ns() >= compiler.deadline:
                return _refused("deadline-exceeded")
            return result
        return cancellation.publish(publish) if cancellation is not None else publish(False)
    except _Refusal as exc:
        return _refused(exc.reason)
    finally:
        if cancellation is not None:
            cancellation.release()
