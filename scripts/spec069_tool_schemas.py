# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T005: deterministic generator of the compact analyze-work request schemas.

Derives one compact schema per request ``kind`` from the published schemas and writes
``agent_braid/analyze_work_schema.py``, which the runtime reads without any dependency.
Annotations (``$schema``, ``$id``, ``$comment``, ``title``, ``description``,
``examples``) are stripped; references inside one published file are inlined; a
reference to another published file becomes one shared entry under the top-level
``$defs`` of the tool ``inputSchema`` (the AIM record is used by three request forms,
so inlining it three times would triple its size). Each request form becomes one
``oneOf`` branch of ``properties.request`` labelled with its ``kind``; the top level of
the ``inputSchema`` stays a plain object (SPEC-069 D2, A1).

``--delivery`` is the D9 ablation switch: ``per-kind`` (default, committed) declares the
schemas; ``description-only`` makes the build serve the interim definition (``request``
declared only as object or array, plus the prose description). Only ``per-kind`` may be
committed; ``description-only`` is for disposable ablation builds.

    python -m scripts.spec069_tool_schemas                      # write
    python -m scripts.spec069_tool_schemas --check              # fail when the committed file differs
    python -m scripts.spec069_tool_schemas --delivery description-only   # ablation build only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "agent_braid/analyze_work_schema.py"
SCHEMAS = ROOT / "schemas"
DELIVERIES = ("per-kind", "description-only")

# kind -> published request schema. Order is the order of the ``oneOf`` branches.
KIND_SOURCES = {
    "aim": "schemas/0.1.0-alpha/analysis-input.schema.json",
    "git": "schemas/0.1.0-alpha/git-analysis-request.schema.json",
}

# Subschemas repeated verbatim in a published schema, declared once under ``$defs`` and referenced
# wherever an equal subschema occurs: name -> (published $id, JSON Pointer of the first occurrence).
SHARED = {
    "effect": ("https://agent-braid.dev/schemas/0.2.0-draft/agent-interaction-metadata.schema.json",
               "/properties/effects/properties/declared/items"),
}

ANNOTATIONS = frozenset({"$schema", "$id", "$comment", "title", "description", "examples"})
SCHEMA_MAPS = frozenset({"properties", "$defs", "patternProperties"})
SCHEMA_VALUES = frozenset({"items", "additionalProperties", "propertyNames", "not", "contains"})
SCHEMA_LISTS = frozenset({"oneOf", "anyOf", "allOf", "prefixItems"})
VALUES = frozenset({"type", "enum", "const", "required", "minItems", "maxItems", "uniqueItems", "minLength",
                    "maxLength", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                    "minProperties", "maxProperties", "format"})

# D12 size cap (owner decision, 2026-11-05) and its approximation. No tokenizer is among the
# installed development requirements and none may be added, so the cap is checked with a named,
# conservative approximation: ceil(UTF-8 bytes / 3.7) of the compact JSON a host forwards to its
# model (name, description, inputSchema). A one-time calibration on 2026-11-07 (tiktoken in a
# disposable environment, never a dependency; evidence/procedure_005.json) measured 4.13 to 4.23
# bytes per token for these definitions with o200k_base and cl100k_base, so the approximation
# over-counts those two tokenizers by about 12 to 14 %. Anthropic's tokenizer is not public and is
# not bounded by this approximation.
TOKEN_CAP = 1500
TOKEN_APPROXIMATION = "ceil(utf8-bytes / 3.7) of the compact model-facing JSON (conservative for o200k_base and cl100k_base; not a tokenizer)"
BYTES_PER_TOKEN_TENTHS = 37


class GeneratorError(ValueError):
    """A published schema uses a construct this generator does not translate."""


def _published() -> dict[str, tuple[str, dict]]:
    """Every published schema with an ``$id``: id -> (repository path, document)."""
    found = {}
    for path in sorted(SCHEMAS.rglob("*.schema.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(document, dict) and isinstance(document.get("$id"), str):
            found[document["$id"]] = (path.relative_to(ROOT).as_posix(), document)
    return found


def _definition_name(identifier: str) -> str:
    stem = identifier.rsplit("/", 1)[-1].removesuffix(".schema.json")
    head, *rest = stem.split("-")
    return head + "".join(part.capitalize() for part in rest)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _pointer(document: dict, fragment: str) -> Any:
    node: Any = document
    for token in fragment.lstrip("/").split("/") if fragment.strip("/") else []:
        node = node[token.replace("~1", "/").replace("~0", "~")]
    return node


class _Compactor:
    def __init__(self) -> None:
        self.published = _published()
        self.definitions: dict[str, Any] = {}
        self.sources: set[str] = set()
        self.shared: dict[str, tuple[str, Any]] = {}
        for name, (identifier, pointer) in SHARED.items():
            document = self.published[identifier][1]
            value = self.schema(_pointer(document, pointer), document)
            self.shared[_canonical(value)] = (name, value)

    def document(self, path: str) -> dict:
        for identifier, (where, document) in self.published.items():
            if where == path:
                self.sources.add(where)
                return document
        raise GeneratorError(f"{path} has no $id")

    def schema(self, node: Any, document: dict) -> Any:
        if isinstance(node, bool):
            return node
        if not isinstance(node, dict):
            raise GeneratorError(f"not a schema: {node!r}")
        if "$ref" in node:
            if set(node) - ANNOTATIONS - {"$ref"}:
                raise GeneratorError("$ref with sibling keywords is not translated")
            return self.reference(node["$ref"], document)
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in ANNOTATIONS or key == "$defs":
                continue  # local definitions are inlined where they are referenced
            if key in SCHEMA_MAPS:
                out[key] = {name: self.schema(item, document) for name, item in value.items()}
            elif key in SCHEMA_VALUES:
                out[key] = self.schema(value, document)
            elif key in SCHEMA_LISTS:
                out[key] = [self.schema(item, document) for item in value]
            elif key in VALUES:
                out[key] = value
            else:
                raise GeneratorError(f"keyword {key!r} is not translated")
        if out.get("pattern") == "\\S" and out.get("minLength") == 1:
            del out["minLength"]  # implied: a string with a non-whitespace character is not empty
        shared = self.shared.get(_canonical(out))
        if shared is not None:
            self.definitions.setdefault(shared[0], shared[1])
            return {"$ref": f"#/$defs/{shared[0]}"}
        return out

    def reference(self, reference: str, document: dict) -> Any:
        target, _, fragment = reference.partition("#")
        if not target:
            return self.schema(_pointer(document, fragment), document)
        if fragment.strip("/") or target not in self.published:
            raise GeneratorError(f"unsupported reference {reference}")
        name = _definition_name(target)
        if name in SHARED:
            raise GeneratorError(f"definition name {name!r} of {target} is reserved for a shared subschema")
        if name not in self.definitions:
            where, referenced = self.published[target]
            self.sources.add(where)
            self.definitions[name] = None  # reserve: a reference cycle is refused below
            self.definitions[name] = self.schema(referenced, referenced)
        elif self.definitions[name] is None:
            raise GeneratorError(f"reference cycle through {target}")
        return {"$ref": f"#/$defs/{name}"}

    def branches(self, kind: str, document: dict) -> list[dict]:
        """One labelled branch per request form; a root ``oneOf`` of references is one form each."""
        forms = document.get("oneOf") if set(document) - ANNOTATIONS - {"$defs"} == {"oneOf"} else None
        if forms is None:
            return [dict({"description": f"kind={kind}"}, **self.schema(document, document))]
        out = []
        for form in forms:
            reference = form.get("$ref", "") if isinstance(form, dict) else ""
            label = reference.rsplit("/", 1)[-1].removesuffix(".schema.json") or "form"
            out.append(dict({"description": f"kind={kind} {label}"}, **self.schema(form, document)))
        return out


def build() -> dict[str, Any]:
    """The compact schemas: ``{"kinds", "request", "$defs", "sources"}`` (deterministic)."""
    compactor = _Compactor()
    branches = []
    for kind, path in KIND_SOURCES.items():
        branches.extend(compactor.branches(kind, compactor.document(path)))
    sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sorted(compactor.sources)}
    return {"kinds": list(KIND_SOURCES), "request": {"type": ["object", "array"], "oneOf": branches},
            "$defs": compactor.definitions, "sources": sources}


def render(delivery: str = "per-kind") -> str:
    if delivery not in DELIVERIES:
        raise GeneratorError(f"unknown delivery {delivery!r}")
    value = build()
    schemas = json.dumps({"request": value["request"], "$defs": value["$defs"]}, indent=1, ensure_ascii=True)
    if "'''" in schemas:
        raise GeneratorError("schema text cannot be embedded")
    sources = "".join(f"    {path!r}: {digest!r},\n" for path, digest in value["sources"].items())
    return (
        "# SPDX-License-Identifier: AGPL-3.0-only\n"
        '"""Compact per-kind analyze-work request schemas (SPEC-069 REQ-005).\n\n'
        "Generated by scripts/spec069_tool_schemas.py from the published schemas listed in\n"
        "SOURCES; do not edit. DELIVERY is the D9 ablation switch read by the tool definition.\n"
        '"""\n\n'
        f"DELIVERY = {delivery!r}\n"
        f"KINDS = {tuple(value['kinds'])!r}\n"
        f"SOURCES = {{\n{sources}}}\n"
        f"SCHEMAS = r'''{schemas}'''\n"
    )


def model_facing_bytes(definition: dict) -> bytes:
    """The part of a listed tool that hosts forward to the model, as compact JSON."""
    return json.dumps({key: definition[key] for key in ("name", "description", "inputSchema")},
                      ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def approximate_tokens(definition: dict) -> int:
    """D12 approximation (``TOKEN_APPROXIMATION``); deliberately over-counts known tokenizers."""
    return -(-len(model_facing_bytes(definition)) * 10 // BYTES_PER_TOKEN_TENTHS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail when the committed file differs")
    parser.add_argument("--delivery", choices=DELIVERIES, default="per-kind",
                        help="D9 ablation arm baked into the build (commit only per-kind)")
    args = parser.parse_args(argv)
    text = render(args.delivery)
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != text:
            print(f"{OUTPUT.relative_to(ROOT)} is stale or not delivery={args.delivery}; rerun without --check",
                  file=sys.stderr)
            return 1
        print(f"{OUTPUT.relative_to(ROOT)} is current (delivery={args.delivery})")
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)}: delivery={args.delivery}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
