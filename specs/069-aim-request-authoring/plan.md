# SPEC-069 implementation plan

## Technical context and scope

`analyze-work` (in `agent_braid/tooling_mcp.py`) accepts `kind` `aim` (validated
by `agent_braid/analysis.py`) and `kind` `git` (shape checked in
`_analyze_work`, then `git_adapter`). Its tool definition declares `request` as
`object | array`. The runtime has no third-party dependencies; `jsonschema` is a
dev/CI dependency. The native plugin bundles the runtime and serves the same
tool definitions to Claude Code, Codex and OpenCode (ADR 0024, ADR 0037).

Scope follows spec REQ-001 to REQ-015. Owner decisions D1–D9 are binding.

Delivery is phased (D6). P1 aligns the contracts and refusals and adds the
REQ-015 label; it is justified on its own because the divergences reproduce
today. P2 builds the automated driver and measures the interim guidance (alpha.7
plus PR #1099) as a baseline. P3 (`units`, schema delivery, telemetry for
`units`, guidance rewrite) runs only if the baseline misses D4 in a required
host. The closing phase runs the final measurement, documentation and the
owner-gated release. Debugging the driver before any new public contract
exists lowers the risk of measuring a broken harness.

## Constitution check before research

- Clause zero, Article 0: engineering only; no algebraic or Yang–Baxter claim.
- Article 5: `units` effects use the Article 5 families; hidden effects are not
  inferred, and declared-only coverage is surfaced as `partial`.
- Article 13: constructed records carry `method: declared` and an assurance
  class no higher than the declaration (syntactic at most); confidence is never
  labelled a guarantee.
- Article 14: the response returns the constructed AIM and digests for replay.
- Article 15: declared unit metadata is not trusted as observed; the report says
  so.
- Article 16: any change to what AIM 0.2.0-draft accepts is a versioned,
  recorded decision with a migration message (REQ-002, REQ-009).
- Articles 19, 20: the problem is real (T010 F1); analysis stays separate from
  execution (`executionAuthorization` false).
- Articles 23, 24: no production semantics are frozen by convenience; the
  `units` contract is a new versioned surface.

No MUST contradiction found. No SHOULD deviation proposed.

## Research, assumptions and alternatives

Observed on 2026-11-05 (pre-specification, to be recorded by T002):

- Schema/validator divergence in both directions (spec, Purpose and scope).
- Compact sizes (descriptions and metadata stripped, `chars / 4` estimate):
  AIM record schema ≈ 650 tokens, git request schema ≈ 270 tokens. With an
  envelope and a `units` schema the per-kind `inputSchema` is estimated at
  ≈ 1,100–1,300 tokens. Real tokenizer counts per host are measured in T005.
- Headless host modes exist: `claude -p` with `--plugin-dir`,
  `--strict-mcp-config` and `--output-format stream-json`; `opencode run
  --format json`. `codex exec` is expected; Codex is not on this machine's
  `PATH`, so T013 research confirms its binary and JSON output.

Alternatives considered (decided by the owner, D1–D3): schema generated from
code or code generated from schema (rejected: loses the reviewable contract or
needs a runtime dependency); MCP resource or skill-only delivery (rejected:
hosts do not reliably read resources; skill-only is the interim #1099); a
separate builder tool (rejected: one more tool in three hosts).

Open research for the owner: host authentication inside disposable profiles
(OD-4). Claude Code and OpenCode may accept an API key through the environment;
the driver must take it from the operator's environment or keychain, never from
a file or prompt text, and never log it.

## Design and compatibility

1. **Contract files.** New `schemas/0.1.0-alpha/analysis-input.schema.json`
   (envelope, `$ref` to the AIM record schema) and
   `schemas/0.1.0-alpha/units-request.schema.json`. Existing AIM and git schemas
   change only per REQ-002 decisions, each recorded in
   `evidence/divergence-inventory.json` and ADR 0038.
2. **Corpus.** `tests/fixtures/analysis-requests/<kind>/{valid,invalid}/*.json`,
   each case with an expected verdict and, for invalid cases, the expected JSON
   Pointer. Generated mutations come from a deterministic script so the corpus is
   reproducible; generated files are committed.
3. **Differential test.** Validates each case with `jsonschema`
   (Draft 2020-12) and with the runtime; equal structural verdicts; batch-level
   runtime-only refusals listed explicitly.
4. **Refusals.** `InvalidAnalysis` and git/units shape errors carry a pointer and
   an expected form; `tooling_mcp` exposes them (already unmasked by #1030),
   bounded to 1024 characters, without request values.
5. **Tool definition.** The top level of `inputSchema` stays a plain object
   with `properties` (`kind`, `request`, and the plugin-injected
   `workspaceId`) and `required`. The per-kind schemas sit under
   `properties.request` (`oneOf` with a discriminating field per kind, or a
   documented equivalent if a host refuses it), generated at build time from
   the published schemas (descriptions stripped, `$ref` inlined) and checked by
   a test for equality with a regenerated copy. A unit test runs the plugin's
   `list_tools` so the `workspaceId` injection cannot break every tool (A1).
   Size cap OD-2 (proposed 1,500 tokens, approximated with named tokenizers;
   hosts do not expose per-tool counts).
6. **`units` kind.** New module `agent_braid/units.py`: validate the request,
   normalize resources lexically (NFC, `.` collapsed, `..`, absolute paths and
   schemes refused, case-only duplicates refused), build records in input order
   from the construction table in the contract, compute `inputDigest` over the
   canonical normalized declaration and `definition.digest` over the
   construction-rules version, force coverage `partial`, add the fixed declared
   evidence item (class 0), and return `{report, constructedRequest,
   provenance}`. Because `plugin_mcp` strips `workspaceId` before calling the
   service (A4), the workspace scope is passed explicitly to the service or
   construction happens in the plugin layer; T006 decides and documents it.
   `_operation_count` and identifier bounds cover `units` (A7).
7. **Guidance.** Skill and tool description rewritten for three kinds; drift test
   validates every embedded request; `examples/analysis/units-*.json` added.
8. **Automation (D5).** `scripts/spec069_native_runs.py` creates disposable
   `HOME`/XDG profiles and a sandbox Git workspace with fixed content inside an
   OS sandbox or container that denies the user's real configuration, keychain
   and home (A10); builds the candidate plugin; installs it per host with a
   tool allowlist limited to the Agent Braid MCP tools; registers the
   workspace; runs the prompts through headless modes; parses JSON transcripts;
   scores them with the pre-fixed rules; redacts and secret-scans transcripts;
   writes `evidence/native-runs.json`; and tears down. It never opens the
   user's real configuration; isolation is proven by a denied-access probe and
   a canary fake configuration. A `--fake-hosts` mode runs the same pipeline
   with fake executables in CI. `runbook.md` lists the remaining manual steps
   with reasons.
10. **Refusals (A8).** Structural refusals use JSON Pointers with unknown keys
    replaced by a fixed token and short digest; semantic refusals use fixed
    codes; git errors stay masked; missing and outside paths share one refusal.
11. **Telemetry (A12).** Shadow and telemetry record `units` with defined
    outcome keys; no silent drop.
12. **Declared-complete label (D7).** `analysis.py` adds an optional label to
    `independent-candidate` interactions whose records carry only declared
    evidence; the analysis report schema documents it; nothing else changes.
13. **Alignment (D8).** Schema keywords are tightened only where the runtime
    already refuses; runtime-looser cases are listed as runtime-only
    differences for the next AIM version.
14. **Measurement (D9).** The driver supports arms (interim guidance vs schema
    delivery), repetitions, held-out prompts, pinned models and interval
    reporting, and a release hook re-runs it when the plugin, host version or
    pinned model changes.
9. **Compatibility.** Alpha.7-accepted requests replayed (REQ-009). Contract
   versions change only if T009 shows an incompatible change; rollback is
   reinstalling the previous plugin tag.

## Validation strategy

Requirement → scenario → procedure → evidence is in `assurance.json` and
`validation-plan.md`. Negative controls per procedure are listed there. Every
increment runs targeted tests plus `quick`; CI `validate` is the `pr` evidence.
Native evidence comes only from the driver. Authority and evidence snapshots are
captured with `scripts.validate_spec_kit snapshot` and frozen before review.

## Constitution check after design

The design adds a declared-only construction path whose outputs state their
coverage, method and class (Articles 5, 13, 15), returns replayable evidence
(Article 14), versions every contract change (Article 16) and keeps analysis
read-only (Article 20). No contradiction found.

## Human review and unresolved decisions

- OD-1 milestone; OD-2 token cap; OD-3 hosts required for release; OD-4 host
  authentication method in disposable profiles.
- Each REQ-002 divergence decision that changes what AIM 0.2.0-draft accepts.
- OD-5 and OD-6 resolved by D8 and D9 (2026-11-05).
- Adversarial and counterfactual reviews of this definition (owner instruction,
  2026-11-05) precede commit, push and PR; findings and dispositions are in
  `reviews/`.
