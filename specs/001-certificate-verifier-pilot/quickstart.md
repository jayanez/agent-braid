# Equivalent guided exercise

From the repo root run `python3 scripts/validate_spec_kit.py`. Read the spec, plan,
tasks and assurance record. For either agent select this existing feature with
`SPECIFY_FEATURE_DIRECTORY=specs/001-certificate-verifier-pilot`; do not invoke
specify again. For a terminal session export this variable before starting either
agent; it selects the same feature directory regardless of the checkout branch.

In Codex use `$speckit-analyze`; in Claude use `/speckit-analyze`. Ask the same:
"Review REQ-001/002 against SC-001/002/003, existing tests and obtained evidence.
Do not edit artifacts, execute other agents or approve scientific claims. Report
scope, contradictions and pending checks." Then use the corresponding converge
skill for a read-only gap assessment. The output must retain the unsupported
proof as unverified and keep the human review pending.

Executable evidence, independent of agent access:

```sh
python3 scripts/run_spec_kit_pilot.py
python3 scripts/validate_spec_kit.py
```

The runner checks actual statuses and two existing tests, then writes raw results
and binds evidence hashes. It does not update authority hashes, record approvals,
start an agent or change algorithms. Reruns change environment/timestamp evidence
and require review. Structural adapter tests cover both renderings; they are not
interactive model sessions. Interactive Codex: pending. Interactive Claude: pending.
