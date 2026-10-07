# SPEC-041: Prospective validation procedures

These procedures are plans. Future test modules/harnesses are not present in this source packet. No procedure below has obtained implementation evidence. A passed source validator checks structure only.

Record positive, refusal, unknown, failed, cancelled and unexecuted outcomes. Evidence must include full candidate and input hashes, command/tool trace, environment, output hashes, domain and limits. Human decisions remain separate.

## procedure_portable_bundle (REQ-001/SC-001)

Given packaged bundle and both supported hosts; perform static validation then actual discovery runs. Assert all five names load at recorded versions; static format checks alone do not count as host discovery. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `integrations/agent-braid/skills/ (new); integrations/agent-braid/host-metadata/ (new); docs/tooling/SKILLS.md (new); tests/test_tooling_skills.py (new)`. Planned receipt: `evidence/sc-001.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_analyze_skill (REQ-002/SC-002)

Given independent, conflicting and unresolved operations; perform agent-braid-analyze is used. Assert the explanation matches the analyzer and observation domain; no analysis verdict grants execution. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `integrations/agent-braid/skills/ (new); integrations/agent-braid/host-metadata/ (new); docs/tooling/SKILLS.md (new); tests/test_tooling_skills.py (new)`. Planned receipt: `evidence/sc-002.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_plan_skill (REQ-003/SC-003)

Given an admissible batch and missing grant; perform agent-braid-plan is used. Assert the plan is advisory with explicit missing permission and no model-issued grant. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `integrations/agent-braid/skills/ (new); integrations/agent-braid/host-metadata/ (new); docs/tooling/SKILLS.md (new); tests/test_tooling_skills.py (new)`. Planned receipt: `evidence/sc-003.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_execute_skill (REQ-004/SC-004)

Given matching and wrong/expired grant references; perform agent-braid-execute is used. Assert the matching bounded result is verified or the request refuses; no secret/grant-store edits or bypass instruction occurs. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `integrations/agent-braid/skills/ (new); integrations/agent-braid/host-metadata/ (new); docs/tooling/SKILLS.md (new); tests/test_tooling_skills.py (new)`. Planned receipt: `evidence/sc-004.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_recover_skill (REQ-005/SC-005)

Given an interrupted owned run or unknown/mismatched run; perform agent-braid-recover is used. Assert the actual recovery/verifier outcome is reported and mismatched authority refuses. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `integrations/agent-braid/skills/ (new); integrations/agent-braid/host-metadata/ (new); docs/tooling/SKILLS.md (new); tests/test_tooling_skills.py (new)`. Planned receipt: `evidence/sc-005.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_evidence_skill (REQ-006/SC-006)

Given verified, failed and inconclusive records; perform agent-braid-evidence is used. Assert chat and export retain actual outcomes and cannot imply code correctness, general confluence or speedup. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `integrations/agent-braid/skills/ (new); integrations/agent-braid/host-metadata/ (new); docs/tooling/SKILLS.md (new); tests/test_tooling_skills.py (new)`. Planned receipt: `evidence/sc-006.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_missing_capability (REQ-007/SC-007)

Given missing MCP dependency/configuration and an execution request; perform a workflow cannot connect. Assert the skill reports the missing capability; only documented read-only CLI fallback is offered. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `integrations/agent-braid/skills/ (new); integrations/agent-braid/host-metadata/ (new); docs/tooling/SKILLS.md (new); tests/test_tooling_skills.py (new)`. Planned receipt: `evidence/sc-007.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_adversarial_guidance (REQ-008/SC-008)

Given repo/evidence text requesting grants, secrets or false success; perform workflow guidance reads the text. Assert it treats text as untrusted and respects deterministic refusal; no hidden configuration, hooks or authority changes ship. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `integrations/agent-braid/skills/ (new); integrations/agent-braid/host-metadata/ (new); docs/tooling/SKILLS.md (new); tests/test_tooling_skills.py (new)`. Planned receipt: `evidence/sc-008.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.
