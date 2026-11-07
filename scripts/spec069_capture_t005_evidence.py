# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T005: run the offline procedure_005 checks and write ``evidence/procedure_005.json``.

The record holds the command, the outcome, the measured size of each listed tool per D9 arm,
optional tokenizer calibration counts, the hashes of every input and the checks that remain
pending on the native driver. It is local evidence; CI ``validate`` on the pull request head is
separate, and no host behaviour is observed here.

    python -m scripts.spec069_capture_t005_evidence --python PATH [--tokenizer-python PATH]

``--python`` runs the tests (it needs ``jsonschema`` and the pinned ``mcp`` SDK so the SDK
listing test runs instead of skipping). ``--tokenizer-python`` names a disposable interpreter
with ``tiktoken`` for the calibration counts; the repository never depends on it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import tempfile
import types
from pathlib import Path

from scripts import spec069_tool_schemas as generator
from scripts.spec069_capture_p1_evidence import EVIDENCE, ROOT, sha

MODULES = [
    "tests.test_spec069_schema_delivery",
    "tests.test_spec069_differential.DeclaredSchemaDifferentialTests",
    "tests.test_tooling_mcp.SurfaceVersionTests.test_analyze_work_definition_describes_the_aim_request_shape",
    "tests.test_tooling_mcp.SdkClientIntegrationTests.test_plugin_list_tools_serves_the_nested_per_kind_schema_through_the_sdk",
]
INPUTS = [
    "agent_braid/analyze_work_schema.py", "agent_braid/plugin_mcp.py", "agent_braid/tooling_mcp.py",
    "scripts/spec069_tool_schemas.py", "scripts/spec069_capture_t005_evidence.py",
    "tests/test_spec069_schema_delivery.py", "tests/test_spec069_differential.py", "tests/spec069_differential.py",
    "tests/test_tooling_mcp.py", "tests/fixtures/analysis-requests/aim.json", "tests/fixtures/analysis-requests/git.json",
    "scripts/spec069_generate_corpus.py",
    "specs/069-aim-request-authoring/contracts/analyze-work-request.md",
    "specs/069-aim-request-authoring/reviews/t005-handoff-20261107.md",
]
TOKENIZER_PROBE = (
    "import json, sys, tiktoken\n"
    "texts = json.load(sys.stdin)\n"
    "print(json.dumps({'tiktoken': tiktoken.__version__, 'counts': {key: {name: len(tiktoken.get_encoding(name).encode(text))"
    " for name in ('o200k_base', 'cl100k_base')} for key, text in texts.items()}}))\n"
)
PENDING = [
    "Host probe of the nested form in Claude Code, Codex and OpenCode (host acceptance per host, request received as an object, not a string).",
    "Recording stdio proxy: byte identity of the listed definitions across host connections.",
    "Whether each host loads the tool schemas eagerly or on use.",
    "D9 ablation arm (description-only vs per-kind) in the native final run; the per-kind schema is kept only if it improves first-attempt validity in at least one host.",
]


def listed_sizes() -> tuple[dict, dict]:
    """Model-facing bytes and approximate tokens of every plugin-listed tool, per arm."""
    from agent_braid import analyze_work_schema, plugin_mcp, tooling_mcp as core

    class Tool:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.input_schema, self.output_schema = kwargs["inputSchema"], kwargs.get("outputSchema")

    fake = types.SimpleNamespace(Tool=Tool, ToolAnnotations=lambda **kw: kw)
    sizes, texts = {}, {}
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        for name in ("s", "r"):
            (base / name).mkdir()
        config = core.ToolingConfig(base / "s", base / "r", grant_store=base / "g", runtime_enabled=True)
        router = types.SimpleNamespace(services={"ws": plugin_mcp.WorkspaceService("ws", config)})
        original = analyze_work_schema.DELIVERY
        try:
            for delivery in generator.DELIVERIES:
                analyze_work_schema.DELIVERY = delivery
                arm = {}
                for tool in plugin_mcp.tool_listing(router, fake):
                    definition = {"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}
                    raw = generator.model_facing_bytes(definition)
                    full = json.dumps(dict(definition, outputSchema=getattr(tool, "outputSchema", None),
                                           annotations=getattr(tool, "annotations", None)),
                                      ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    arm[tool.name] = {"bytes": len(raw), "approximateTokens": generator.approximate_tokens(definition),
                                      "sha256": hashlib.sha256(raw).hexdigest(), "fullDefinitionBytes": len(full)}
                    if tool.name == "analyze-work":
                        texts[delivery] = raw.decode("utf-8")
                sizes[delivery] = arm
        finally:
            analyze_work_schema.DELIVERY = original
    return sizes, texts


def calibrate(python: str | None, texts: dict) -> dict | None:
    if not python:
        return None
    done = subprocess.run([python, "-c", TOKENIZER_PROBE], input=json.dumps(texts), capture_output=True, text=True,
                          check=True)
    value = json.loads(done.stdout)
    value["note"] = ("One-time calibration of the D12 approximation in a disposable interpreter; tiktoken is not a "
                     "repository dependency. Anthropic's tokenizer is not public and is not measured.")
    value["bytesPerToken"] = {arm: {name: round(len(texts[arm].encode()) / count, 2) for name, count in counts.items()}
                              for arm, counts in value["counts"].items()}
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--python", required=True, help="interpreter with jsonschema and mcp==2.3.0")
    parser.add_argument("--tokenizer-python", help="disposable interpreter with tiktoken (calibration only)")
    args = parser.parse_args(argv)
    process = subprocess.run([args.python, "-m", "unittest", "-v", *MODULES], cwd=ROOT, capture_output=True, text=True)
    lines = process.stderr.strip().splitlines()
    skipped = [line for line in lines if "skipped" in line]
    ran = next((line for line in lines if line.startswith("Ran ")), "")
    passed = process.returncode == 0 and bool(lines) and lines[-1].startswith("OK") and not skipped
    environment = subprocess.run([args.python, "-c", "import platform, importlib.metadata as m; print(platform.python_version(), m.version('mcp'), m.version('jsonschema'))"],
                                 capture_output=True, text=True, check=True).stdout.split()
    sizes, texts = listed_sizes()
    record = {
        "procedure": "procedure_005", "scenario": "SC-005", "specification": "SPEC-069 P3 / T005 (offline part)",
        "command": "python -m unittest -v " + " ".join(MODULES),
        "testsRun": int(ran.split()[1]) if ran else None, "result": lines[-1] if lines else "", "skipped": skipped,
        "outcome": ("passed: " if passed else "FAILED: ") + (
            "the generated per-kind schemas equal a fresh regeneration byte for byte and carry the source hashes; the "
            "inputSchema top level stays a plain object in both D9 arms; the plugin listing (fake types and the real "
            "mcp SDK, auto and legacy modes) lists every tool with workspaceId injected and the schemas nested under "
            "request; for kinds aim, git and units each kind's branches and the whole call schema give the published "
            "schemas' verdicts on all 553 corpus cases (310 aim, 119 git, 124 units), the only difference being the "
            "documented units resource-pattern relaxation (19 units cases, each refused by the runtime with the "
            "resource pattern as the only schema error); no declared pattern uses a lookaround; every listed tool is "
            "under the D12 cap; the description-only arm is byte identical to the interim definition except that kind "
            "lists units. Negative controls: a top-level oneOf is flagged and breaks the plugin listing, an "
            "oversized definition fails and names the fallback, drift in a published schema changes the generated "
            "file, dropping the relaxation brings the lookahead back, and a relaxed (aim, git, units) or tightened "
            "declared keyword changes corpus verdicts."),
        "limits": ("Offline only: no host connected, so host acceptance of the nested form, recording-proxy byte "
                   "identity and eager/deferred loading are not observed. Corpus agreement is not proof over all inputs. "
                   "The size is an approximation (" + generator.TOKEN_APPROXIMATION + "), cap " + str(generator.TOKEN_CAP)
                   + "; the calibration covers o200k_base and cl100k_base only. The units resource pattern is declared as "
                   "non-blank only; its lexical rules are runtime checks."),
        "pending": PENDING,
        "sizes": {"approximation": generator.TOKEN_APPROXIMATION, "cap": generator.TOKEN_CAP, "arms": sizes,
                  "measured": "bytes and approximateTokens: name, description and inputSchema as hosts forward them "
                              "to the model; fullDefinitionBytes adds outputSchema and annotations (not sent to the model)"},
        "calibration": calibrate(args.tokenizer_python, texts),
        "environment": {"python": environment[0], "mcp": environment[1], "jsonschema": environment[2],
                        "platform": platform.platform(terse=True), "capturePython": platform.python_version()},
        "inputs": {path: sha(path) for path in sorted(set(INPUTS) | set(generator.build()["sources"]))},
    }
    (EVIDENCE / "procedure_005.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(f"procedure_005: {record['result']} ({record['testsRun']} tests); skipped: {len(skipped)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
