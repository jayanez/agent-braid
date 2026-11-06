# SPDX-License-Identifier: AGPL-3.0-only
"""Harness for the SPEC-069 schema/validator differential test (REQ-004)."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import jsonschema
from referencing import Registry, Resource

from scripts import spec069_divergence_inventory as inv

ROOT = inv.ROOT
CORPUS = ROOT / "tests/fixtures/analysis-requests"


def load_corpus(kind: str) -> list[dict]:
    return json.loads((CORPUS / f"{kind}.json").read_text())["cases"]


def aim_validator(aim_schema: dict | None = None, input_schema: dict | None = None):
    aim_schema = aim_schema or json.loads(inv.AIM_SCHEMA.read_text())
    input_schema = input_schema or json.loads(inv.INPUT_SCHEMA.read_text())
    registry = Registry().with_resources([(aim_schema["$id"], Resource.from_contents(aim_schema))])
    return jsonschema.Draft202012Validator(input_schema, registry=registry)


def git_validator(git_schema: dict | None = None):
    return jsonschema.Draft202012Validator(git_schema or json.loads(inv.GIT_SCHEMA.read_text()))


class Harness:
    """Evaluates corpus cases with the published schemas and the complete service path."""

    def __init__(self, aim=None, git=None) -> None:
        self.temp = tempfile.TemporaryDirectory()
        repo, results = inv.init_repo(Path(self.temp.name))
        self.prober = inv.Prober(repo.resolve(), results)
        self.repo = repo.resolve()
        self.validators = {"aim": aim or aim_validator(), "git": git or git_validator()}

    def close(self) -> None:
        self.temp.cleanup()

    def verdicts(self, kind: str, case: dict) -> dict[str, str]:
        request = copy.deepcopy(case["request"])
        if kind == "git":
            text = json.dumps(request).replace("<outside-root>", str(Path(self.temp.name).resolve()))
            request = json.loads(text)
            schema_ok = self.validators["git"].is_valid(json.loads(json.dumps(case["request"])))
        else:
            schema_ok = self.validators["aim"].is_valid(request)
        service_ok, _ = self.prober.service_verdict(kind, request)
        return {"schema": "accepts" if schema_ok else "refuses", "service": "accepts" if service_ok else "refuses"}

    def mismatches(self, kind: str, cases: list[dict]) -> list[tuple[str, dict, dict]]:
        out = []
        for case in cases:
            got = self.verdicts(kind, case)
            if got != case["expect"]:
                out.append((case["id"], case["expect"], got))
        return out
