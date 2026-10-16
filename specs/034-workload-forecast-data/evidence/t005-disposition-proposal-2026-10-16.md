# Native resource harness: offline correction and T005 disposition proposal

Date: 2026-10-16. Status: proposal, not adopted. No execution approval requested.

## What failed and why tests missed it

The consumed request 7719672ee77a9cbbbca41d8ea8bd5818c3d494827441bc187774672a4dbc2a8a failed after 4.673785958 seconds. The request counter reached 257 and refused before launching that request; at most 256 parent Git processes launched. The canonical run state says completed/nextIndex=2 and the grant is consumed, but the independent final tree verifier did not return an acceptance result. Neither producer state nor eligibility is a substitute for that verifier.

In the original test_profile_driver.py, issue_operator_grant and execute_policy_run were replaced at module level by fake Python functions. The fake dispatch called the bootstrap wrapper then incremented effects by two without issuing any Git requests. verify_run was a lambda returning the desired tree without issuing requests. The healthy simulated flow therefore consumed zero Git requests and could not expose a 256-request end-to-end limit. The boundary test independently exercised refusal after a tiny cap, not the complete flow. The 12 mutations covered owner decision, canonical identity, verification result and cleanup guards; none removed a phase reservation or tested whether verification fit the remaining budget. They were valid for those narrow guards, not evidence of full-flow cost adequacy.

Our preparation/review incorrectly treated these guard and simulated orchestration results as sufficient to present a complete native-flow budget. The budget was an unverified engineering estimate. The failure was resource-accounting preparation, not model performance, unavailable hardware or a scientific negative result. No retained trace gives a complete per-phase upper bound. The 257th attempted request is a lower observation, not an exact required total, and must not be turned into a new 257/512 limit.

## Offline correction

The consumed package and all its receipts are untouched. This separate directory is a non-executable research repair: both script entrypoints refuse direct native use, no approval request/decision/grant/consumption record exists, and its policy has no gitPhaseUpperBounds. Therefore calling its driver without a test-supplied cost model refuses before host observation, grant or patch effects. No runnable next package is prepared.

RequestBudget requires positive separate grant, dispatch and independent-verification bounds whose sum fits the unchanged total. Each phase cannot consume another phase's reservation. Attempted, accepted and actually launched calls are distinct; a denied request cannot be reported as a launched process. The driver records the denied phase with an allowlisted error code, without exporting arbitrary exception text. The real runtime's complete bounds remain UNKNOWN; these changes do not manufacture them or establish future execution readiness.

New tests use the actual Processes wrapper and driver orchestration with only the native Popen superclass replaced by an inert fake. Synthetic grant/dispatch/verifier functions deliberately issue budgeted process requests. A 256-request modeled full flow must include the final verifier; a modeled minimum of 257 must refuse before host reads/grant; excess dispatch cannot spend the verifier reservation; excess verifier requests retain a failed attempt and cannot report success. The synthetic phase counts (1/254/1 etc.) are test inputs, not inferred actual runtime costs. Small-boundary cases also test missing/invalid bounds, unaccounted launches and caller mutation of declared bounds.

51 offline unittest cases pass. Three targeted in-memory mutations (omit total reservation, omit phase reservation, omit final verifier) are detected. No new native Git/runtime dispatch, sysctl collection, model, VM, Docker, installation, network measurement or approved-control execution is used. These are separate private tests, not repository CI or a new admission claim.

## Proposed T005 closure without another execution loop

Recommend a transparent **closed / not_planned** disposition for the remaining actual-profile acceptance obligation, following the already-used T007 distinction. Preserve the original T005 source checkbox and criterion UNCHECKED, record delivered synthetic software and retained partial actual observations, and state that the task was not completed. This requires explicit owner adoption and a reviewed source/tracking change; this document does not enact it.

The original criterion includes describing actual admitted local slots. No active/future-use profile is admitted and the complete approved control failed. Closing as completed now, or silently treating the synthetic tests as actual admission, would weaken that criterion. A terminal not_planned issue state must not be converted by tracking sync into a completed checkbox, nor counted as a satisfied dependency. Dependencies consuming T005 remain blocked/unavailable until independently satisfied or explicitly de-scoped; do not unlock real collection/launch merely because the issue is closed.

Recommended delivery after owner adoption: one bounded documentation/tracking PR that records (1) unchanged criterion, (2) completed engineering scope, (3) failed native control and exact evidence hashes with private identifiers redacted, (4) not_planned acceptance disposition and consumer impact, and (5) no active profile registration. Luna reviews it; normal structural/CI checks and GitHub readback apply, with no native resource/model/VM execution. Keep T001 open for its outstanding source/rights/privacy/window and architecture decisions.

Do not create another package or approval request now. Any future live-profile admission belongs to an explicitly resumed consumer with an actual operational need. Reopen this obligation (or link a clearly scoped successor) only then, reusing the evidence and requiring an independently supported complete cost bound before proposing a single execution. If its bound remains unknown, stop before resource work; no automatic next version. Native cleanup/recovery of the retained blocked run is separate and is not performed by these tests or disposition.

If the owner prefers eventual completed status to not_planned, retain T005 open as blocked on actual admission; that is the honest alternative, not another package today.
