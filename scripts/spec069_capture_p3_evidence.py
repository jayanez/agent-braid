# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 P3: run each procedure's tests and write one evidence record per procedure.

Same record format as ``scripts/spec069_capture_p1_evidence.py`` (command, outcome,
input hashes, limits); the Spec Kit validator rejects a record when any input
changes, so rerun this after a change to one of them. Local evidence only; the CI
``validate`` aggregate on the pull request head is separate.

    python -m scripts.spec069_capture_p3_evidence
"""

from __future__ import annotations

import json
import platform
import sys

from scripts.spec069_capture_p1_evidence import EVIDENCE, SHARED_INPUTS, run, sha

GOLDEN = "tests/fixtures/analysis-requests/units/golden/"
PROCEDURES = {
    "procedure_006": {
        "requirement": "SC-006",
        "modules": ["tests.test_spec069_units", "tests.test_spec069_differential",
                    "tests.test_spec069_alpha7_replay"],
        "inputs": ["agent_braid/units.py", "schemas/0.1.0-alpha/units-request.schema.json",
                   "scripts/spec069_generate_corpus.py", "tests/spec069_differential.py",
                   "tests/test_spec069_units.py", "tests/test_spec069_differential.py",
                   "tests/test_spec069_alpha7_replay.py", "specs/069-aim-request-authoring/evidence/alpha7-replay.json",
                   "specs/069-aim-request-authoring/contracts/analyze-work-request.md",
                   *(GOLDEN + name + suffix for name in ("t010-readme-conflict", "dot-slash-alias",
                                                         "disjoint-claimed-complete", "ordered")
                     for suffix in (".request.json", ".constructed.json"))],
        "outcome_note": (
            "A units request with two units writing README.md is accepted through analyze-work; the constructed AIM "
            "validates against the AIM and envelope schemas and equals its byte golden; replaying it through kind aim "
            "returns a byte-identical report; the pair is conflicting with serialize-or-isolate, coverage partial, "
            "provenance names agent-braid.units-declaration/0.1.0-alpha. Negative controls: README.md and ./README.md "
            "(and //, trailing /, NFC variants) are one resource; claimed complete coverage gives partial and the same "
            "bytes; disjoint units are unknown and no accepted corpus case is independent-candidate; a .. path, an "
            "absolute path, a case-only duplicate, 33 units, a 257-byte id, a duplicate id, an unknown dependency and "
            "an unsupported effect kind are refused with a pointer and expected form or a fixed code, without request "
            "values; outputs are identical across runs, processes and hash seeds; construction opens no file. The units "
            "corpus (132 files: 124 cases, 8 goldens) matches the units schema and the service path, and relaxing the "
            "resource pattern, the effect-kind check or the lexical checks fails the comparison. The adapter bounds "
            "still refuse when the module's own bounds are loosened (A7). The scope equals the plugin workspaceId. "
            "The aim/git corpus (429 cases) and the alpha.7 replay (317 requests) are unchanged."),
        "limits": (
            "Corpus agreement is not proof over all inputs. Resources are declarations normalized lexically; symbolic "
            "links, case-insensitive file systems and generated files are not resolved. No host model was involved; "
            "the analyze-work tool definition lists kind units since T005 (procedure_005). Run on macOS only here; Linux runs in "
            "CI and Windows is T014. ECMAScript validators differ from Python on U+0085 and U+FEFF in the schema's "
            "non-blank checks (declared limit, tagged in the corpus)."),
    },
}


def main() -> int:
    status = 0
    for name, spec in PROCEDURES.items():
        result = run(spec["modules"])
        passed = result["returncode"] == 0 and result["result"].startswith("OK")
        inputs = sorted(set(SHARED_INPUTS + spec["inputs"]))
        record = {
            "procedure": name, "scenario": spec["requirement"], "specification": "SPEC-069 P3",
            "command": result["command"], "testsRun": result["testsRun"], "result": result["result"],
            "outcome": ("passed: " if passed else "FAILED: ") + spec["outcome_note"],
            "limits": spec["limits"],
            "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
            "inputs": {path: sha(path) for path in inputs},
        }
        (EVIDENCE / f"{name}.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        print(f"{name}: {result['result']} ({result['testsRun']} tests)")
        status |= 0 if passed else 1
    return status


if __name__ == "__main__":
    sys.exit(main())
