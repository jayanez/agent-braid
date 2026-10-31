# SPEC-065: Cross-artifact analysis (speckit-analyze, 2026-10-31)

Read-only pass over spec.md, plan.md, research.md, tasks.md, contracts/,
validation-plan.md and assurance.json against the Constitution, SPEC_KIT.md and
the cited code. No constitutional MUST conflict found. Human review: pending.
Findings were remediated in the same draft; the remediation column states where.

| ID | Severity | Location | Authority | Finding | Remediation |
|---|---|---|---|---|---|
| A1 | High | contracts/native-profile.md, limits table | `harness_admission.py` (`maxAdmissionSeconds` is admission-observation staleness) | The draft mapped the F3 30-minute unit cap onto `maxAdmissionSeconds`, which bounds admission freshness, not session wall time. | Keep `maxAdmissionSeconds` at the offline bound; state that session wall time is a host limit (A2). |
| A2 | High | plan.md "not expected to change"; T006 | `harness_lab.MAX_WALL_SECONDS = 60`, used by `HostLimits` in both host adapters | A native session is capped at 60 s by `HostLimits`, which conflicts with the F3 30-minute unit cap and makes realistic sessions time out. Raising the shared constant would also widen Codex and fixture bounds. | Plan and T006 now require a separate, reviewed native-only wall bound in `harness_host_claude.py` (≤ F3 cap, chosen in NC-8), leaving `MAX_WALL_SECONDS` and Codex unchanged. |
| A3 | Medium | plan.md; T010 | `harness_host_claude.SUBSCRIPTION_KEY_SOURCES` is a fixture assumption | If CRED-05 observes a subscription `apiKeySource` value outside `{"none","oauth"}`, the constant must change, which the plan said would not happen. | Plan and T010 now route any such change through a separate reviewed edit with the observation as evidence; never widened to make a run pass without the probe record. |
| A4 | Medium | tasks.md T005 | spec NC-3 | T005 refuses on an unsupported OS build but did not list NC-3 as a decision dependency. | T005 dependencies now name NC-2, NC-3, NC-4, NC-5, NC-7, NC-8. |
| A5 | Medium | contracts/containment-qualification.md, CRED-02 control | REQ-007 (no operator secrets touched) | A positive control that plants a dummy item in the operator's login Keychain would modify operator credentials. | Contract now requires a disposable keychain file for the CRED-02 positive control. |
| A6 | Low | spec.md F5 | SPEC_KIT.md (evidence in repository) | STRICT isolation is only an orchestrator brief so far. | Already covered: T001 binds it into a founder record before use. No change. |
| A7 | Low | assurance.json | SPEC_KIT.md | Draft stage, no obtained evidence, current authority snapshot. | Expected for a draft; re-snapshot after these edits. |

## Independent review findings (code-review-and-quality, 2026-10-31)

A separate read-only reviewer checked every code claim. Findings and
dispositions:

| ID | Severity | Finding | Remediation |
|---|---|---|---|
| A8 | Critical | `run_claude` parses output after the run returns, so a paid-route session would complete before refusal (F2). | REQ-002/SC-002 and plan K1: live `init` parsing kills the group before any `assistant`/`result` event is accepted; negative test in T006. |
| A9 | Critical | `_check_transport` never checks a containment backend. | REQ-002 and plan K2: transport refuses unless its backend passes the verified-containment check; negative test in T006. |
| A10 | Required | Native-profile contract moved profile dispatch before the key and format checks, changing offline refusal order. | Contract keeps the existing check order; multi-fault offline goldens in procedure_001. |
| A11 | Required | `ENV_ALLOW` lacks the variables the launcher needs; `argv[0]` resolves `claude` through `PATH`. | Plan K4: native environment per NC-5/NC-7, absolute pinned path hash-checked at every launch. |
| A12 | Required | "Run-scoped" config and temp directories pre-decided NC-7 and conflicted with NC-5 (a). | Wording now defers to NC-5/NC-7; interaction noted in both items. |
| A13 | Required | The pre-session probe subset silently decided what satisfies F4. | New founder item NC-11; contract keeps the subset only as a proposal. |
| A14 | Required | "Not-qualified record" cannot be expressed in either qualification format. | Now a not-qualified decision record, distinct from qualification records. |
| A15 | Required | SC-004 qualification hash and REQ-003 quota fields had no carrier in `LabResult`/`ClaudeHostResult`. | Both go into a run-evidence record; result types and `ClaudeTransport.run` signature unchanged. |
| A16 | Required | "Projected use" presumed a projection model; cohort caps need state outside this spec. | Per-session check folded into NC-6; cohort state is a caller-supplied SPEC-049 input whose absence refuses. |
| A17 | Required | Probe catalog missed escape classes. | Added FS-06/07, NET-07/08, CRED-06/07, PROC-06/07/08; PROC-03 widened; REQ-005 to REQ-008 updated. |
| A18 | Required | T010 lacked its K5 files; T007 needs T006 for live probes. | Fixed in tasks.md. |
| A19 | Required | `parse_version` import from the manifest would be circular. | Contract places a version validator in `harness_manifest.py`. |
| A20 | Nit | T002/T003 mix-up, "empty" simulated environment, positive-control wording, ADR exclusion wording, validation-plan negatives. | All aligned. |

Coverage: every REQ-001 to REQ-011 has one scenario, one procedure in
validation-plan.md and at least one task. Every NC item (NC-1 to NC-11) is referenced by a task
dependency after A4 and A13. H1 is stated as allowed to fail; T009 completes on a
negative outcome.
