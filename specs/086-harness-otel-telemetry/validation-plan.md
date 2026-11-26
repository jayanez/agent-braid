# SPEC-086: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the
candidate commit, input hashes, command, exit, outcome and limits. Passing checks do
not prove privacy, safety or usefulness and are not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001) | OD-1 to OD-8 decided or deferred; spec approved, amended or rejected | review read as approval of unwritten code |
| procedure_002 | SC-002 | Codex read-only review (T002) | raw output kept; every finding triaged with a reason | a finding dropped without a reason |
| procedure_003 | SC-003 | pin tests over pinned, unknown and missing pins | only the pinned file is accepted; fixed reason codes | pin check removed and the unknown pin still refused |
| procedure_004 | SC-004 | convert committed fixture records twice | one `invoke_agent` per attempt; version equals candidate hash; untimed events counted; identical bytes | an invented time or a guessed required attribute |
| procedure_005 | SC-005 | seeded-content fixtures through the serializer | no seeded value in output bytes; each drop counted | allowlist removed and the test still passes |
| procedure_006 | SC-006 | default, `OTEL_*` set, skill call, explicit mode | spans only in explicit mode, only in the private store, with stated permissions and bounds | a span written by default or from an environment variable |
| procedure_007 | SC-007 | loopback listener; export with, without, refused and retried | delivery only by the explicit command; pending kept; each span once | export at run time, a non-loopback send, or a duplicate |
| procedure_008 | SC-008 | SPEC-047 suite and a v4 batch with emission on and off | identical results and batch bytes; no span id, hash or sub-day time in the store | any store or batch byte that differs |
| procedure_009 | SC-009 | outcome fixtures (correct, incorrect, ungraded, infrastructure error, missing) | fixed class and status each; missing is `unobserved`; no score or verdict | a task failure marked ERROR, or missing mapped to `ok` |
| procedure_010 | SC-010 | write-fault injection and overhead timing (T011) | harness output and exit codes equal the off run; losses counted | a fault that changes a harness result |
| procedure_011 | SC-011 | audit over a store with spans, drops and a pending export | counts reported; no write; no socket | the audit writes, repairs or connects |
| procedure_012 | SC-012 | adoption decision record (T003, T012, T015) | cites the ADR, H1 result and owner decision; a failed condition leaves export unreleased | adoption recorded with H1 failed or no ADR |
| procedure_013 | SC-013 | code search and filesystem monitor over trace commands, converter and host configuration files | no host exporter setting changes; no path ingests host OTLP | a host exporter setting written or host OTLP read |
| procedure_014 | SC-014 | inspect spans and results from conversion, store, export and audit | every span attribute and result field is exactly `false` | any `true`, missing or non-boolean value |
| procedure_015 | SC-015 | loopback listener, non-loopback destination and redirecting listener | spans only at the loopback destination without redirect; refused batches stay pending | a non-loopback send, a followed redirect or an unbounded body |
