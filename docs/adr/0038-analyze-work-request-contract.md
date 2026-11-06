# ADR 0038: analyze-work request contract

- **Status:** Proposed 2026-11-06, awaiting owner review. Writing this record
  accepts nothing: acceptance, any publication, tag, plugin-dist push or release
  are separate owner decisions.
- **Date:** 2026-11-06
- **Deciders:** Juan Antonio Yáñez García (owner); proposed by the SPEC-069 P1
  implementation.
- **Constitutional articles:** 0, 5, 13, 14, 15, 16, 19, 20, 23, 24
- **Specification:** [SPEC-069](../../specs/069-aim-request-authoring/spec.md);
  normative text in the
  [request contract](../../specs/069-aim-request-authoring/contracts/analyze-work-request.md)

## Context

SPEC-068 T010 (row 16, finding F1) showed an OpenCode model sending
`{units: [{id, writes}]}` to `analyze-work` because the tool declared `request` only
as "object or array". With a valid AIM example the same call returned `conflicting`.
SPEC-069 T002 then showed that the published AIM and git request schemas and the
runtime validators disagree in both directions (404 probes, 10 root causes), that no
schema exists for the analysis-input envelope, and that refusals do not say where a
request failed. Interim guidance (PR #1099) describes the shape in prose only.

## Decision

Owner decisions D1 to D13 of SPEC-069 are binding; this ADR records the ones that
shape the contract and how phase P1 applied them.

1. **Source of truth (D1).** The JSON Schemas are the public contract. The runtime
   validators stay hand-written and dependency-free. A differential test over a
   committed corpus compares each schema with the complete `analyze-work` service
   path and fails on any verdict that differs from the recorded expectation.
2. **Request forms.** `kind` `aim` accepts an analysis-input envelope, a single AIM
   record or a nonempty array of AIM records; `kind` `git` accepts a git analysis
   request. A new schema, `analysis-input.schema.json`, publishes the first.
3. **Alignment (D8).** Where a schema is looser than the runtime, the schema is
   tightened with a note and no new version (`pattern: "\S"` on strings the runtime
   refuses as blank). Where the runtime is looser, the runtime keeps its behaviour as
   a documented runtime-only difference and the tightening moves to the next AIM
   version, because it would refuse requests alpha.7 accepts. Checks JSON Schema
   cannot express (unique identifiers, known and acyclic dependencies, adapter
   bounds, roots) stay runtime-only and are listed in the contract.
4. **Refusals.** A structural refusal names the failing location as a JSON Pointer
   and the expected form; a semantic refusal carries a fixed code. Request keys the
   contract does not define are replaced by `<key:digest8>`; request values are
   never echoed; git output stays masked; a missing path and a path outside the
   roots return the same refusal; messages stay within 1,024 characters. The
   alpha.7 reason text leads, so substring consumers keep working.
5. **Declared-complete label (D7).** An `independent-candidate` pair whose two
   records carry only `method: declared` evidence gets the additive property
   `completenessBasis: declared-not-observed`. Classification and constraints are
   unchanged. `analysisId` digests the whole report, so it changes with the label.
6. **Compatibility.** Requests alpha.7 accepts are still accepted with identical
   reports (modulo the label and the recomputed digest); no contract version changes.
   The replay of 317 requests is the evidence.
7. **Deferred by D6, conditional on the P2 baseline.** Schema delivery inside the
   `analyze-work` `inputSchema` (top level stays a plain object; per-kind schemas
   under `request`; 1,500-token cap, D12) and the `units` authoring kind
   (declarations only, coverage forced to `partial`, lexical normalization,
   byte-golden construction table) are designed in the specification and are not
   part of this ADR's P1 contract. They enter this contract only if P3 runs.
8. **Native evidence (D4, D9, D11, D13).** Host behaviour is measured only by the
   automated driver of P2; this ADR claims none.

## Alternatives considered

Generate the schema from code, or the code from the schema: rejected by D1 (loses
the reviewable contract, or needs a runtime dependency). Tighten the runtime to the
schema: rejected for the cases where alpha.7 accepts the request (D8). Skill-only
or resource-only delivery: rejected in the specification (hosts do not reliably read
resources; skill-only is the interim #1099). Echoing offending keys and values in
refusals: rejected (secret-shaped keys, A8).

## Consequences

- Positive: one reviewable contract per request form, enforced by a differential
  test; refusals that a host model can act on; no hidden acceptance change.
- Negative: a tightened schema still differs from ECMAScript validators on
  U+001C to U+001F, U+0085 and U+FEFF, and Python `jsonschema` accepts a trailing
  newline after a digest; both are declared limits. The runtime stays looser than
  the schema for `evidence` items, git `uncertainPaths` uniqueness and the
  single-record identifier bound until the next AIM version.
- Compatibility: `agent-braid-plugin/v0.2`, `agent-braid-tooling/v0.1`, AIM
  `0.2.0-draft`, git request and report `0.1.0-alpha` are unchanged; the report
  schema gains one optional property. Rollback is reinstalling
  `agent-braid--v0.1.0-alpha.7`.
- Security: refusals reveal no host path existence, no request values and no
  unknown key names.
- Research: engineering only; no scientific claim (clause zero, Article 0).

## Validation

`tests/test_spec069_differential.py` (with three negative controls),
`tests/test_spec069_refusals.py`, `tests/test_spec069_declared_label.py`,
`tests/test_spec069_alpha7_replay.py`, `tests/test_spec069_compatibility.py` and the
divergence inventory (`scripts/spec069_divergence_inventory.py`, `--check`).
Falsified if a request alpha.7 accepted changes verdict or report, or if a refusal
echoes a request value. Revisit when the next AIM version is drafted, and when P2
reports whether P3 is needed.

## References

[SPEC-069](../../specs/069-aim-request-authoring/spec.md), its
[plan](../../specs/069-aim-request-authoring/plan.md) and
[compatibility notes](../../specs/069-aim-request-authoring/compatibility.md);
ADR 0024, ADR 0030, ADR 0037; SPEC-068 T010 row 16;
`schemas/0.2.0-draft/agent-interaction-metadata.schema.json`,
`schemas/0.1.0-alpha/analysis-input.schema.json`,
`schemas/0.1.0-alpha/git-analysis-request.schema.json`,
`schemas/0.1.0-alpha/analysis-report.schema.json`.
