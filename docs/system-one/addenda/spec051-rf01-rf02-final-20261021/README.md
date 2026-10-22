# SPEC-051 / RF-T01–RF-T02: final local software receipt

This is an additive documentary supplement. It publishes obtained local implementation evidence, failures and limits, while the canonical SPEC-051/ADR0026, modules, tests, assurance and tracking changes remain in the coordinator's unpublished product candidate. Their local adoption for bounded implementation is distinct from public integration, independent product review, real-source admission and human/scientific acceptance. This PR changes the corpus only.

Read the [source map](source-map.json), [failure chronology](failures-and-repairs.md) and [continuation gates](continuation.md). Exact [packet](source-capsules/packet.json), [completion](source-capsules/completion.json), [producer readback](source-capsules/final-readback.json), [control map](source-capsules/conformance-map.json) and [lossless original report](source-capsules/implementation-result.md.gz) preserve their observed identities. Local file paths and references inside capsules describe original provenance; they are not links to public code or a claim of product publication. Earlier [RF planning](../v1-publication-closure-20261021/forecast-feedback-proposal/README.md) remains a dated proposal, not rewritten as implementation evidence.

## What was implemented locally

The owner authorized separate SPEC-051 and pure RF-T01/RF-T02 implementation on M3 Pro, EUR0, at baseline `a6329c828011d1468fed3dfa4e98f5a8531167e2`. RF-T01/02 retain their original SPEC045/T009/T010 and REQ-CI001/002, SC-CI001/002 lineage; later local SPEC051 uses REQ001/002. ADR0026 and migration were adopted locally for this scope; canonical publication and review remain separate. RF03/store, RF04/observer and real collection were not implemented here.

`OperatorRegistry` / `resolve_authority` compare exact registered descriptor bytes, supplied root/scope/pins/actions and current caller-supplied expiry/revocation state to return immutable validation context or refusal. A wire admitted flag or callback returning True cannot manufacture it. This is an explicitly trusted Python caller boundary, not authenticated consent, physical path/link verification, artifact truth, fresh revocation discovery or a secure registry loader.

`FrozenRegistration` / `validate_append` re-resolve the supplied snapshot, revalidate bounded supplied history and return new canonical immutable state: chained origin/correction, source/clock/family/oracle binding, T0 availability, unknown values, intervals, spans, duplicate idempotence, missing supplied population and outcome eligibility. No file append, capture, model call or grant occurs. Late completion remains right-censored/ineligible for the original prediction horizon; later evidence cannot backfill original eligibility. Integer-token and UTC-Z (up to six fractional digits) admission are explicit implementation limits.

## Obtained checks and costs

| Check | Result | Observation boundary |
|---|---|---|
| Focused stable |42 tests; zero failures/errors/skips;0.135s | Synthetic software controls; overlaps full suite |
| Metadata repair controls |6 affected methods; zero failures/errors/skips;394.957s | Only affected integration/governance controls |
| Corrected quick |2,153 tests:2,130 passed,23 skipped;exit0;unit2198.039s/profile2424.9525901250017s | Normal planner escalated to sensitive |
| Corrected PR |2,153 tests:2,130 passed,23 skipped;exit0;unit2198.943s/profile2426.2510924579983s | Same candidate, overlapping suite |
| Guard mutation checks |6 detected:5 assertion failures,1 runtime error | Helper exit1 preserved; not six clean assertion detections |

Corrected receipts report2,932 source inputs unchanged and compare equivalent owned local copies using existing Python3.12.13 dependencies with child PATH pinned; temporary copies were removed. Producer packaging reports2,915 baseline files intact, with only two existing-file metadata exceptions, and four pure module/test files unchanged across repair. Those source-hash relationships, 68 bindings,18 source archive members and50 lossless raw representations were verified by documentary readback; no suite, mutation or patch application was repeated here. Archive/patch/code remain local. Reported external spend:EUR0. No representative accuracy, new forecast utility, independent scientific sample or complete deployment-cost claim follows.

Counts overlap and are not additive independent observations. Unit time is included in profile wall time. Missing/OS-level observations remain unknown; sampled process data and physical storage/capacity are not inferred from numeric caps. Corrected profiles do not erase the failed first attempt or close independent review/CI gates of a different commit.

## Traceability and limits

| Local requirement / task | Scenario and evidence | Remaining boundary |
|---|---|---|
| RF-T01 / SPEC051 REQ001 |SC001; exact trusted snapshot/refusal controls, focused suite and mutation evidence | Truth/physical roots/consent/freshness/secure loader external |
| RF-T02 / SPEC051 REQ002 |SC002; chain, causal-origin, correction, clock/family/oracle/missing-state/late-horizon controls | Supplied population only; no real-source completeness or truth |
| Compatibility / SPEC051 REQ003 |SC003; no I/O/model/collector side effects in pure controls | No integrated observer/noninterference or storage acceptance |
|21 named conformance controls |[Original map](source-capsules/conformance-map.json) and raw focused logs | N03 physical checks pending;N17 store andN18 observer deferred;N19 partial supplied population |

The fixed-schema interpreter was checked on sampled developer-validator controls, not proved generally equivalent to JSON Schema. Stage labels may repeat and completed inclusive intervals use union; unique span IDs/parent containment do not establish live observation truth. Annexes are refused. Current caps account for supplied canonical event bytes, not filesystem journals/maps or safe ownership/atomicity. Creating an oracle attestation or trusted Python constructor is not source capture or semantic/human gold. SPEC045 synthetic APIs, SPEC047 identity-free numeric aggregates/default-off, typed-v1 finite `.txt` domain and frozen historical packets are unchanged by this documentary publication.

The new code had coordinator self-review only at sealing; that historical packet stays unchanged. A later separate [Luna interface review](post-seal-interface-review/review.md), with [receipt](post-seal-interface-review/receipt.json), found no P1/P2 in three static properties: supplied snapshot authority, supplied-history replay and late-maturity censoring. It ran no product imports/tests and grants no whole-product, source, human or scientific approval. The independent documentary review of this PR is another distinct boundary. See [pending gates and next owner](continuation.md).
