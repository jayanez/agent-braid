# Implementation plan

The numbered steps below retain the original local implementation preparation.
The [current integration record](integration-review.md) identifies the existing
review and the authorized source transfer; it does not repeat the original work.

1. T001 fixes this contract and proposed ADR 0025 against the existing SPEC-040/042 interfaces.
2. T002 implements one numeric collector and transactional bounded SQLite store; T006 adds strict reports and incremental exchange.
3. T003 and T004 instrument only the outer MCP/CLI boundaries. T005 threads explicit consent through preview, configuration, receipt and diagnosis.
4. T007 verifies privacy, disabled behavior, failures, cancellation, concurrency, retention, size, exchange and measured overhead on synthetic inputs.
5. T008 reconciles the original telemetry-only seven-spec M4.5 matrix, historical SPEC-044/T004 bounded completion, pending T017/T018, installation/README/navigation and unpublished tracking drafts.
6. T009 records actual focused and quick/PR validation. T010 records self-review and all pending independent/human/founder decisions without fabricating approval.

No new agents, hosts, providers, user installations, reproductions, commits, remote writes, merge or publication are part of that original local preparation. The separate full clone follows the documented unreachable-object recovery; the original checkout is preserved. Local source changes are reviewable before a later candidate freeze.

Technical dependencies are acyclic: T001→T002→{T003,T004,T006}; {T003,T004}→T005; {T003,T004,T005,T006}→T007; {T001,T007}→T008; {T007,T008}→T009→T010. The SPEC-044 pilot depends on validated SPEC-047 and new candidate admission; SPEC-047 development does not depend on the pilot.
