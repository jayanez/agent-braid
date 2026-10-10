<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Offline tooling journey

This walkthrough exercises the candidate service with owned synthetic input. It
creates one temporary Git fixture, analyzes it, prepares a bounded plan, checks
that an unissued grant identifier is refused, then renders and exports the
returned envelope. It makes no host connection, provider call, real project
change, grant, execution, or capture. Run from a source checkout with Python
3.12+, Git, and the repository's development environment.

## Analyze, prepare, and refuse an unissued grant

The fixture materializer creates only its own Git repository under the system
temporary directory. The result directory and grant store are separate sibling
paths. The code calls the public `ToolingService.invoke` adapter directly, so
this checks the same envelope and core path without requiring an MCP client or
the optional SDK.

```sh
DEMO_ROOT=$(mktemp -d)
.venv/bin/python - "$DEMO_ROOT" <<'PY'
import json
from pathlib import Path
import sys
import threading

from agent_braid.tooling_fixtures import load_inventory, materialize_fixture
from agent_braid.tooling_mcp import ToolingConfig, ToolingService

root = Path(sys.argv[1]).resolve(strict=True)
inventory = load_inventory(source_checkout=True)
fixture = materialize_fixture(
    inventory, "m45-prepare-advisory-plan-01", root / "fixture")
results = root / "results"
results.mkdir(mode=0o700)
service = ToolingService(ToolingConfig(
    source_root=fixture.repository_root,
    result_parent=results,
    grant_store=root / "operator-grants.json",
    runtime_enabled=True,
))
cancelled = threading.Event()

analysis = service.invoke("analyze-work", {
    "kind": "git", "request": fixture.analysis_request,
}, cancelled)
assert analysis["status"] == "ok"
prepared = service.invoke("prepare", {
    "request": fixture.request,
    "runDirectory": str(results / "synthetic-run"),
    "mode": "parallel",
}, cancelled)
assert prepared["status"] == "ok"
plan = prepared["result"]
print("Inspect planDigest:", plan["planDigest"])

# This reserved sentinel was never issued and is not grant metadata.
refusal = service.invoke("execute", {
    "plan": plan, "grantId": "00000000-0000-0000-0000-000000000000",
}, cancelled)
assert refusal["status"] == "refused"
assert not (results / "synthetic-run").exists()

(root / "prepared-envelope.json").write_text(
    json.dumps(prepared, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
(root / "missing-grant-envelope.json").write_text(
    json.dumps(refusal, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
print("Prepared and refusal envelopes:", root)
PY
```

Inspect `planDigest`, source/revision IDs, declared paths, destination, mode,
budgets, and the returned limits before treating a plan as useful. The fixture's
expected classification is only a deterministic oracle for these exact owned
synthetic bytes. A refusal is not evidence that a real host denied access, and
the sentinel above is not an issued authorization.

## Present and export a returned value

Pass the saved, complete envelope to the local presentation command. An empty
`--evidence-ref` selection exports the complete envelope and no separately
selected evidence objects. The temporary parent created above is private; keep
the resulting `evidence.json` private because complete envelopes can contain
local paths or other sensitive values.

```sh
.venv/bin/python -m agent_braid tooling present "$DEMO_ROOT/prepared-envelope.json" --format text
.venv/bin/python -m agent_braid tooling present "$DEMO_ROOT/prepared-envelope.json" --format json
.venv/bin/python -m agent_braid tooling present "$DEMO_ROOT/prepared-envelope.json" \
  --export-directory "$DEMO_ROOT/export"
```

The export directory contains a sanitized summary/graph and a receipt binding
the files to the canonical envelope bytes. For an artifact-reference result,
reconstruct the complete bytes from its manifest and ordered chunks, verify each
chunk and the complete SHA-256 and byte count, and only then save and present the
complete envelope. A reference alone is not a complete result.

## Separate operator-authorized runtime path

The source integration control in `tests/test_tooling_journey.py` exercises the
complete offline path in its own temporary roots. It previews/applies isolated
assets for both host formats, checks the five installed skill hashes and the
service catalog, analyzes and prepares one owned fixture, and verifies that an
unissued grant refuses before allocating a run. A separate test operator then
uses the existing policy API to issue the exact plan-bound grant. The control
interrupts an actual local run at a committed checkpoint, inspects its prefix,
issues a distinct recovery grant, resumes, verifies the expected tree, and
exports the complete verified envelope deterministically. It checks that the
source revision/tree remain unchanged and removes only the installed assets.

```sh
.venv/bin/python -m unittest tests.test_tooling_journey
```

This is a synthetic engineering control with local test-only operator grants,
not a user tutorial that issues authority, an MCP host connection, a provider
call or an actual M4.5 evaluation attempt. Its command and result must be bound
to the final candidate before use as procedure evidence.

The walkthrough stops before execution. If an operator later elects to use the
synthetic fixture for a local runtime demonstration, follow the explicit
`grant-policy-run` → `execute-policy-run` → `verify-git-run` commands in the
[owned fixture tutorial](../../examples/runtime/README.md). Grant issuance is a
separate CLI action after inspecting the exact digest; MCP tools and skills do
not issue grants. Recovery is conditional on an actually interrupted owned run:
inspect its status first, then separately authorize the selected `resume` or
`abort` action and use `recover-policy-run` as documented there. Do not create
an interruption merely to complete this offline walkthrough.

MCP cancellation signals the worker and waits for it to settle so a caller is not
told that an effectful operation stopped while it may still be running. Git child
commands have enforced command and end-to-end budgets and are killed on
cancellation. A filesystem call stalled below Python has no separate hard
deadline, so in that condition cancellation may remain pending; do not replay an
operation until its owned run has been inspected.

For the new configured stdio endpoint, [installation](INSTALL.md) documents the
server command and client configuration. The existing runtime's
[MCP quickstart](../../specs/021-m4-alpha-runtime/quickstart.md) describes its
separate legacy endpoint. Starting a server does not establish host
discovery, authentication, user approval, or actual host acceptance. Those
observations and any M4.5 evaluation require their separate registration and
human decisions; this tutorial records none of them.
