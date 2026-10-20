# Capability and evidence matrix

The initial target is Codex and Claude Code. Exact host builds are selected and
frozen before actual observation; a vendor document is not an integration result.

| Capability | Existing basis | M4.5 increment | Acceptance boundary |
|---|---|---|---|
| AIM/Git/worktree analysis | M1, ADRs 0007/0008 | Shared `analyze-work` input union | Report unchanged semantics and unknown/refusal cases |
| Fixed-patch preparation | M2/SPEC-021 | MCP `analyze`, `prepare` parity and resources | Advisory, immutable inputs, no execution authorization |
| Execute/status/recover/verify | ADRs 0019/0020 | SDK delegates existing RuntimeTools/policy | Opt-in existing grant, private result only |
| Discovery and structured output | SPEC-021 legacy stdio | SDK v2.3.0, new/legacy protocol, schemas/prompts/resources | Actual tool call receipts plus separate protocol controls |
| Workflow guidance | No product skill bundle assumed | Five portable Agent Skills | Both hosts load the exact bundle and use the expected tools |
| Installation/lifecycle | Existing Python CLI | Optional tooling extra and host wrappers | Exact versioned assets and root-bound configuration |
| Evidence presentation | Existing reports/verifier | Compact envelopes, graph and exports | Each statement linked to artifact, scope and provenance |
| Usability/total cost | Historical observations only | Preregistered three-arm comparison | All attempts, failures, missing costs and limitations retained |

## Supported target matrix

| Target | macOS arm64 | Linux x86_64 | Transport | Required record |
|---|---|---|---|---|
| Codex local CLI | Actual host mandatory | Protocol/core reproduction only initially | stdio | Host/model/build, bundle/candidate, tool receipts and outcome |
| Claude Code local CLI | Actual host mandatory | Protocol/core reproduction only initially | stdio | Same, including local tool permission behavior |
| Codex app/cloud | Unclaimed | Unclaimed | Unselected | Future distinct observation |
| Other development environments | Deferred | Deferred | Unselected | Future route 1 |

Capabilities are advertised only when available in the configured mode. Analysis
mode omits runtime mutation tools; resources cannot select a new source root.
Host approval never substitutes for the operator grant. A shared skill directory
does not establish native plugin compatibility; each wrapper has its own receipt.

## Current additive capability

| Capability | Basis | Local increment | Remaining boundary |
|---|---|---|---|
| Default-off technical diagnostics | SPEC-047; existing MCP/CLI boundaries | Local numeric reliability/duration/classification aggregates, private bounded retention, manual report/export/merge/purge, installation consent | Integration-candidate validation/delta review, architectural adoption and future pilot admission; no native/experimental or anonymity claim |

The [global dependency matrix](../../docs/tooling/M45_ALIGNMENT.md) preserves original accepted capabilities and distinguishes all technical, observation, review and acceptance edges.
