# SPEC-087 T001 owner review (2026-11-27)

The owner reviewed the spec and plan through AskUserQuestion prompts in the
orchestrator session, each option explained with examples from the code, risks and a
recommendation. Answers:

| Question | Answer |
| --- | --- |
| OD-5, SPEC-069 drivers (`scripts/spec069_native_runs.py`, `spec069_scoring.py`, `spec069_capture_t005_evidence.py`, `spec069_host_probe.py`; 18 collections) | Keep as exceptions; SPEC-088 migrates what it touches (recommended option). |
| OD-5, remaining exceptions (`scripts/run_m45_skills_acceptance.py`, `scripts/spec066_t030_receipt.py`, Spec Kit tooling: `spec_kit.py`, `test_spec_kit_integration.py`, `validate_spec_kit.py`, `validate_m0_closure.py`) and the REQ-017 fake-host test | Confirmed both (recommended option), after a second explanation with concrete code examples. |
| Capability names of the plan's membership table (`plugin-assets`, `tooling-measurement`, `host-events`, `lightning-run`, `lightning-tool-classes`, `harness-gated`, `harness-inventory`, `viewer-hosts`) | Approved as written (recommended option). |

T001 is complete. This record approves the specification for implementation; it is not
acceptance of the implementation, which T010 and later reviews cover.
