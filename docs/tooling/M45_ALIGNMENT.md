> **Integration source:** telemetry `b2cf477fe9f9d586d6431ae9ed9a14abb3266706`, reconstructed over `e474320e`, is being integrated on public develop `f0854d63a37f3d6dba777dcfd36524d7de37067c`. [Existing review and integration provenance](../../specs/047-local-technical-telemetry/integration-review.md) separate the reviewed source from this combined candidate. Historical tests, assurance and owner decisions keep their original identities. Pilot **NO-GO**; T017/T018/T010 remain open.

# Current M4.5 source alignment — 2026-10-20

**Owner documentary update — 2026-10-17:** [E9-D17/E9-D18/E9-D10](../../specs/046-local-technical-telemetry/owner-decisions-e9-20261017.md)
are now incorporated for exact frozen candidate `e9d4153cc880`. Contract
applicability, acknowledged coverage/gaps with pilot **NO-GO**, and bounded
engineering acknowledgment do not supply native evidence or final acceptance.
T017/T018/T010 remain open. This later documentary lot changes no product,
consent, registration, authority, historical record or task state.

**Disposition:** source integration candidate; operational admission withheld and M4.5 open. Ten source specs, 131 task obligations (99 checked, 32 unchecked), 3 historically closed parents, 1 closed SPEC-054 parent and 6 open parents: 141 desired records; SPEC-054 adds the plugin surface naming policy and draft SPEC-060 adds the portable MCP prompt names contract (`agent-braid-tooling/v0.2`, 11 tasks, no implementation).

Counts are derived from `sync_github_tracking.source_inventory`, not remote issue closure. The [machine-readable map](../../specs/047-local-technical-telemetry/alignment.json) records typed dependencies. Original portfolio: 60 original obligations plus 19 auxiliary tasks. The combined portfolio adds 15 SPEC-046 plugin tasks, ten SPEC-047 telemetry tasks and pending SPEC-044/T017/T018; existing IDs and original satisfied criteria are preserved. Checked implementation/documentary tasks record their stated bounded evidence only.

| Spec | Responsibility and current alignment | Technical predecessors | Observation/review/acceptance boundary |
|---|---|---|---|
| [SPEC-039](../../specs/039-ai-tooling-program/spec.md) | Original bounded acceptance retained; additive program map and closure boundaries pending review. | M1, M2, M4 | Original bounded acceptance retained; integration-delta review and acceptance remain separate |
| [SPEC-040](../../specs/040-portable-mcp-surface/spec.md) | Outer ToolingService.invoke instrumentation; tools, results, permissions and protocol unchanged. | SPEC-039 | Original bounded acceptance retained; integration-delta review and acceptance remain separate |
| [SPEC-041](../../specs/041-ai-tooling-skills/spec.md) | Five skills unchanged; no telemetry activation/collection; native loading/use still pending. | SPEC-040 | Independent/native/human/founder gates remain separate |
| [SPEC-042](../../specs/042-ai-tooling-packaging/spec.md) | Explicit mode in preview/server arguments/receipt/static diagnosis; uninstall and purge distinct. | SPEC-040, SPEC-041 | Original bounded acceptance retained; integration-delta review and acceptance remain separate |
| [SPEC-043](../../specs/043-ai-tooling-journey/spec.md) | Privacy, report and aggregate exchange separate from full evidence exports. | SPEC-040, SPEC-041, SPEC-042 | Independent/native/human/founder gates remain separate |
| [SPEC-044](../../specs/044-ai-tooling-evaluation/spec.md) | Product metrics separate from receipts/native/cost; preserve T004; T017/T018 pending. | SPEC-043, SPEC-047 | Independent/native/human/founder gates remain separate |
| [SPEC-046](../../specs/046-native-ai-plugins/spec.md) | Native plugins, registry, setup and self-contained distribution remain owned by their accepted candidate. No new telemetry consent or package publication here. | Existing 040/042 interfaces | External candidacy T014/T015 and final M4.5 gates remain open |
| [SPEC-047](../../specs/047-local-technical-telemetry/spec.md) | Own collector, data contract, bounded storage, retention, report/exchange and synthetic validation. | SPEC-040, SPEC-042 | Independent/native/human/founder gates remain separate |

The technical graph is acyclic. SPEC-047 validation precedes the future pilot; native evaluation is not a development predecessor of SPEC-047. Installation consent requires the instrumented interfaces, not native acceptance. Neither a checked source task nor an issue closure supplies observation/review/acceptance evidence.

## Canonical owner decisions

[D17/D18/D10](../../specs/046-local-technical-telemetry/owner-decisions-20261016.md) are now incorporated as documentary decisions: additive observation contract approved, coverage reviewed with pilot **NO-GO**, and bounded engineering acknowledged with final acceptance deferred. T017/T018/T010 remain open. Counts, historical accepted scopes, T002, T004 and ADR 0025's proposed status are unchanged.

## Consumed contracts and external boundaries

- M1: advisory exact-resource analysis and conservative unknowns (ADRs 0007/0008); no algorithm change or new execution authorization.
- M2: immutable Git replay and advisory planning (ADR 0013); measurements do not alter replay/equivalence or supply a concurrency proof.
- M4: existing private bounded fixed-patch/grant/isolation/recovery contracts (ADRs 0019/0020); historical negative utility and G4 NO-GO retained.
- SPEC-034: permissioned workload data keeps its source consent/yield and cancellation boundaries. Product diagnostics are not an admitted workload feed.
- SPEC-035: optional forecast adapter has no telemetry dependency, activation or model download here.
- SPEC-036: complete-cost prospective experiments keep their registered inputs, accounting and outcome denominators.
- SPEC-037: shadow/promotion requires its own governed evidence; no telemetry-derived promotion.
- SPEC-045: synthetic/local forecasting capability and episode telemetry remain separate; no FC.1/FC.2 completion is required for product telemetry.

## Historical completion and new candidate

[Previously approved SPEC-044/T004 completion](../../specs/044-ai-tooling-evaluation/t004-bounded-closure-reconciliation.md) is incorporated for exact candidate `482fbcc`, preserving A, original failures/omissions, skipped checks, Linux point-in-time HOME-corrected scope and all exclusions. No reproduction, independent review or original approval is repeated. Frozen assurance/evidence bytes are not rewritten.

PR #509 was historically observed at head `482fbcc` before the rewrite and is now integrated in rewritten develop. The registration/interface/receipt source modules are present at their recorded byte identities. Their presence does not establish native observation, process authentication, admission or pilot GO. The local validation report records the source-port checks; it does not supply admission. [T017](../../specs/044-ai-tooling-evaluation/native-observation-contract-proposal.md) separates prior discovery, instructions loaded and observed use without lowering the frozen gate. [T018](../../specs/044-ai-tooling-evaluation/candidate-admission-matrix.md) lists historical applicability and missing candidate-specific observations. Their owner documentary dispositions are now recorded in the canonical owner decisions above; native/admission obligations and both task checkboxes remain open; existing Luna review is retained at its b2cf boundary.

The original implementation snapshot is frozen at `4f0a6bf407797bc4b682e6c5726dcd7a4f61bc28`, with frozen assurance packaged at `b3809cbbaa0aa6ec1a1e50c6a841d840b753d94d`, based on `466ada29`. The later canonical decision incorporation is a separate documentary lot and does not rebind either commit. Actual synthetic checks and a source manifest live in [SPEC-047 evidence](../../specs/047-local-technical-telemetry/validation-plan.md). Passing tests/profiles do not freeze a commit, admit a pilot, validate a native host/provider, complete 108 attempts/CLI baseline/36 cases/72 ratings/cost closure, adopt an ADR or close M4.5.

## Tracking delivery boundary

[Issue drafts](../../specs/047-local-technical-telemetry/issue-drafts.md) and [structured drafts](../../specs/047-local-technical-telemetry/tracking-drafts.json) prepare one parent, ten telemetry subissues, two evaluation follow-ups and the existing T004 state reconciliation. No remote issue, milestone description or Project state has been changed. The retained historical read-only milestone API snapshot was open, 58 closed and 28 open items including PRs; it is not a new managed-issue count or acceptance result. The earlier 85-managed-issue snapshot remains historical.

The unpublished issue/milestone drafts retain their earlier preparation observation and unchanged task states; their owner-decision prose is superseded by the canonical decision record. Any future external apply requires a fresh source/digest audit, not reuse of stale draft bodies.

Future publication requires reviewed/integrated sources, scoped milestone-19 audit, exact missing-ID allowlist, approved digest apply and readback with no pending scoped operations. Source publication/integration and remote tracking remain distinct; tracking writes require their own approved digest. The private Project was not accessed; its membership/custom-state verification remains separate and pending.

## Concrete pending-source dependency

The historical source comparison found that the old PR #509 head supplied the registration, interface-observer and receipt-instrument modules. PR #509 is now integrated on rewritten develop; all three modules are present with the recorded hashes in `pr509-dependency.json`. This closes the source-presence dependency only. Native discovery/loading/use, authenticated process evidence, exact registration, candidate admission and the pilot remain blocked or pending.

SPEC-047 can use the source-route modules now present in the rewritten tree, subject to the existing reviewed registration/admission gates. Their presence and byte identity do not authenticate an account, process, receipt or budget and do not authorize execution. No provider, host or native process was launched.

The [exact milestone #19 description draft](../../specs/047-local-technical-telemetry/milestone-description-draft.md) is local and unpublished. Existing synchronizer title/state/issue audit does not cover description drift; eventual publication needs its own reviewed guarded update and readback, without broadening the current no-write scope.

## Local telemetry identity reconciliation

[The b137 identity map](../../specs/047-local-technical-telemetry/identity-reconciliation-b13737ed4584.md) reserves SPEC-046/ADR-0024 for native plugins and assigns SPEC-047/ADR-0025 to active telemetry documents. Historical telemetry evidence retains its IDs and bytes. The earlier telemetry-only lot had 65 checked / 26 open tasks; current counts above include Plugins. NO-GO and all pending gates remain unchanged.
