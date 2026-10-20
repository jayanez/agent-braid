# T05 — completed Luna review, row64 P2 correction pending

S1-T05-LUNA-ROW64-20261020; canonical SPEC-028/T011. This updates the earlier reported-active review for the [bound candidate](../t05-review-candidate-20261020/README.md). The [original report](original-review.txt) preserves its source paths/line references; the [exact reproduction output](row64-reproduction.txt) preserves the observed behavior. Reviewer/model is reported as Luna Latest (gpt-6-luna), scoped technical AI review; this is not human, scientific or T07 global acceptance.

The report reviews source109a182c1762b55acdb2575488ab1b573ca15d3e5dec760fec30621c164a6935 and testsf5c8dd0e48a74f338b813d1a56ba66c650beb94123add3735c356c179755313e, matching the preserved worker candidate. It reports one public-context software reproduction, without rerunning the full suite, and no file mutation. This documentary conversation compared the report's pins with the preserved candidate, copied/hashed the report and reproduction, and did not perform that reproduction itself.

## Confirmed P2 and exact limit of the result

Checkpoint auto-row creation reaches the64-row cap in _open, outside _check's failure catch. A trusted caller catches work-budget-exceeded, but immediate live state remains answered, failure=None and evidence is retained. Later close cannot add cleanup and publish returns refused. Thus the obtained reproduction establishes stale successful live producer state after caught budget exhaustion, **not a final publication bypass**. This is the remaining row-cap variant of the open T05-FIND-001 refusal-latch boundary.

Luna recommends immediate _fail('work-budget-exceeded') before raising and reserving the64th row for cleanup (at most63 operational rows). The coordinator assigned a narrow correction/regression to the same worker's two files. Required regression: catch the public automatic checkpoint error, verify immediate refusal and cleared semantic bodies, preserve a cleanup row and refused publication. Correction and same-reviewer recheck are pending; no new source pins, fixed-candidate pass or full profiles are claimed in this receipt.

## Scope and non-findings

The report identifies no other actionable P1/P2 within its scoped code/tests/governance review and inspects the one-log attributes exception. This is a bounded review outcome, not proof that no defect exists. T02–T04 implementation and future T06 consumers were outside scope. Earlier28focused passes and three mutation detections were coordinator evidence, not independently rerun by Luna. No full profile, empirical study, human review or scientific acceptance occurred here.

Next evidence: corrected source/test hashes, deterministic public-API regression, exact affected test log and Luna's targeted disposition, followed by stable new quick/PR receipts. Preserve this report on the reviewed pre-fix hashes. T05 remains open; T06, human/scientific/representative/rights/admission/promotion/activation gates remain pending. Product source is not published by this documentary receipt.
