# SPEC-032: Prospective validation procedures

These are planned procedures, not executed tests or obtained evidence.

## procedure_001: REQ-001 / SC-001

Given an export with changed tokenizer, logits or unsupported operator. Exercise backend selection runs. Expect parity failures disable it and the unoptimized supported path remains available.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-001.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_002: REQ-002 / SC-002

Given non-English, uncertain language, code-mix or unknown task. Exercise routing occurs. Expect unsupported input defers or uses an explicitly validated backend and calibration group.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-002.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_003: REQ-003 / SC-003

Given local refs, nullable enums, cycles or unrestricted strings. Exercise schema compilation occurs. Expect supported meanings are preserved and unsupported generation/ref recursion is refused precisely.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-003.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_004: REQ-004 / SC-004

Given the correct option is pruned or finalists change. Exercise a narrowed decision is evaluated. Expect dropped options and subset identity are logged; shortlist recall and full-catalogue baseline are measured.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-004.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_005: REQ-005 / SC-005

Given concurrent batches, reload, cancellation and memory pressure. Exercise serving lifecycle runs. Expect no request reads another state or loses its model; overload refuses within the declared deadline.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-005.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.

## procedure_006: REQ-006 / SC-006

Given a hook mutates inputs, stalls or an installed wheel lacks a backend. Exercise the packaged consumer runs. Expect mutation is rejected, timeout stays bounded and backend capabilities match installed contents.

Include both the positive case and the stated refusal/adversarial boundary;
record all attempted cases and discrepancies. Implementation must replace this
prospective reference with named executable tests or an obtained research report
before marking the scenario validated. Evidence: `evidence/sc-006.json`,
exact candidate/input/command/environment hashes and limitations. A protocol
report with negative/inconclusive outcome may complete research without promotion.
