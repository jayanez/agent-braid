# T02/T03/T04 — final quick and PR profile receipts

S1-DDP-COMPONENT-PROFILES-FINAL-20261020. Tasks: SPEC-029/T026 (DDP-T02), SPEC-031/T010 (DDP-T03), SPEC-028/T010 (DDP-T04). This supersedes only the unknown/running status in the [profile start record](../component-profiles-started-20261020.md). The [focused join](../t03-and-component-join-20261020/README.md) remains a separate, overlapping software check.

| Profile | Unit result | Unit duration | Whole profile duration | Exit |
|---|---|---|---|---|
| Quick, escalated to sensitive | 2014 cases, 1995 passed, 19 skipped, zero failures/errors | 1992.303s | 2155.31922187499s | 0 |
| PR | 2014 cases, 1995 passed, 19 skipped, zero failures/errors | 1990.396s | 2153.644948375004s | 0 |

The two runs use identical candidate inputs and overlapping cases; do not sum them as independent evidence. Skips are explicitly not passes. Exact original [quick receipt](quick-receipt.json), [PR receipt](pr-receipt.json), [quick log capsule](quick-log.json) and [PR log capsule](pr-log.json) preserve commands, skip names, validator output and paths. Decode each capsule's text as UTF-8 to recover the original log bytes and verify its originalSHA256. The log capsules avoid altering whitespace in raw evidence.

## Binding and verification

Each original receipt binds 2247 input files. Both maps are identical: the 2230 [baseline source bindings](baseline-files.json), unchanged, plus17 new files (seven frozen T01 documentary files and ten component/test/fixture files). This documentary conversation rechecked every bound input against the actual coordinator candidate and both original log hashes at incorporation time. Both receipts report sourceInputsStillMatch=true and ownedTemporaryCopyRemoved=true. These checks establish recorded byte agreement and reported cleanup, not a hermetic reproduction or independent implementation/scientific review. No tests were rerun by this conversation.

The parent interpreter and literal child python3 PATH point to the existing isolated Python3.12 environment. Each profile ran in its own local source-equivalent clone with shared installed dependencies, file-only Git transport and offline model flags. Both logs finish with successful executable validation, including finite scientific controls, Spec Kit structure/render, constitution replica and whitespace. No new empirical study, model, training/calibration or human review occurred; source-equivalent software validation does not establish scientific acceptance. EUR0 and no network use are receipt claims within that run scope.

The failed earlier DDP-T01 full profile (1962 cases, three environment failures, 19 skips), interrupted obsolete candidate and localized29-test correction remain immutable earlier evidence. These passing profiles cover a different, explicitly bound component candidate; they do not relabel the older run as passed.

## Publication, next authority and unresolved boundaries

The [prior-head CI snapshot](prior-head-ci.json) records documentary PR594 at cc5b5575184654319a6236e9e0dbbd498d28b023: validate and tracking passed, specialist matrix skipped. This does not cover the subsequent commit adding this receipt. Read current-head CI/review separately; no independent or human approval is claimed.

At incorporation, completion.json/final component package was not yet received. Both profile passes and byte agreement provide the evidence for the coordinator to check the previously authorized T05 condition; this document does not issue GO or claim T05 started. The coordinator owns final packet verification and implementation assignment. T05 typed wire/request context and T06 native consumers are not obtained outcomes of these component profiles. No task/parent/milestone is closed here. Final package receipts and any actual T05 start/results require new additive bindings. Human/scientific/representative/rights/admission/promotion/activation gates remain pending.
