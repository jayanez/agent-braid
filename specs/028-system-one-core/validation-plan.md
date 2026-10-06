# SPEC-028: Prospective validation procedures

These are planned procedures, not executed tests or obtained evidence.

## procedure_001: REQ-001 / SC-001

Given a valid request and a pinned backend. Exercise each primitive is evaluated. Expect boolean P(true), choice distribution and score expected value are returned with stable identities; no generated text or arbitrary numeric regression.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-001.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_002: REQ-002 / SC-002

Given duplicate IDs, NaN, bool-as-number, empty rubrics or over-budget input. Exercise validation runs. Expect an explicit refusal identifies the boundary and the backend is never called.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-002.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_003: REQ-003 / SC-003

Given uncalibrated logits or a changed artifact. Exercise a response is constructed. Expect calibratedProbability is absent unless supported and response digests bind all decision inputs.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-003.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_004: REQ-004 / SC-004

Given a confidence of 1.0 and a forged verified field. Exercise a consumer inspects the response. Expect executionAuthorization remains false and existing semantic verification is still required.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-004.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_005: REQ-005 / SC-005

Given an offline base install with System 1 disabled. Exercise legacy commands run. Expect their outputs and failure behavior remain unchanged and optional backend imports are not attempted.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-005.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_006: REQ-006 / SC-006

Given two interleaved requests with different options. Exercise backend calls are overlapped or cancelled. Expect responses retain the correct request identities; ties use declared stable option-ID ordering.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-006.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.
