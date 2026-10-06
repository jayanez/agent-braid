# Proposed native decision contract v1

Draft interface; no public schema/API is changed by this planning record.
Initial envelope: 1 MiB canonical JSON, 1..32 independent questions, 2..32 options
per choice/score, at most 64 UTF-8 bytes per identifier, nesting depth 16.
Boolean has exactly false/true logical IDs with model-facing labels mapped separately.
Backend reports a tokenizer-bound window; full rendered state/question/options must
fit or evaluation refuses. No implicit truncation, implicit singleton certainty,
free-form generation or unconstrained regression. Defaults require T001 review.

Request: `contractVersion`, `requestId`, `state`, `stateDigest`, `questions`,
`capabilityId`, `contextVersion`, `backendId`, `policyId`, `budgets`.
Questions: `id`, `type` (boolean/choice/score), `instructions`, ordered `options`
with stable `id`, `description`; score adds finite strictly increasing rubric values.
Preserve order in the digest; serialized object-key order is not an option-order API.

Response: matching IDs/digests; `status` answered/abstain/defer/refused;
`answers` with full option distribution, choice ID, boolean P(true) or rubric expectation;
`calibrationStatus` absent/fitted/validated/stale; `rawTopProbability`,
`concentration` with named formula/version and optional `calibratedProbability`;
`reasonCodes`, `inputCoverage`, `usage`, `modelManifestDigest`,
`calibrationManifestDigest`, `policyDigest`, `capabilityVersion`;
`evidenceClass: heuristic`, `executionAuthorization: false`.

Distributions contain finite nonnegative probabilities summing to 1 within 1e-6
in the external response. Logits and head/softmax/calibration run in fp32 or stronger;
deterministic/backend tolerance is reported separately. Ties use stable option IDs;
do not pretend a tie has calibrated certainty. A score expectation is not necessarily
an actual discrete rubric level. Preserve argmax level and expectation separately.
Validation rejects unknown fields/versions, duplicate IDs and non-finite numbers;
booleans do not count as numeric budgets. Unsupported capability refuses before load.

No external inference endpoint is configured by default. Initial local worker: one
active neural evaluation, queue bound 8, request deadline 5 s, zero retry by default;
backend memory/token cap must be frozen per device before use. Cancellation stops
consumption and produces no late recommendation. A hard compute deadline requires a
killable worker boundary: a Python thread timeout is insufficient to stop GPU work.
Admission, queue time, model load, tokenization and compute all count toward the
deadline. A wider envelope needs versioned contract review and measured coverage.

Probability is a claim about the labeled decision population, never resource
integrity, semantic commutation, grant authority, confluence or Yang–Baxter.
Default policy abstains when calibration/domain support is missing. Future shortlist
responses must bind a subset and use a separately validated chain policy.

`rawTopProbability` names the uncalibrated readout's maximum mass; the returned
decision distribution states whether temperature calibration was applied. Optional
`calibratedProbability` refers to the reported categorical outcome within the
validated labeled group, never to the ordinal expectation, entropy concentration or
probability that a semantic/execution contract holds. Include calibrator version and
numeric representation used by threshold fitting; rounded display values do not
replace the values used by the policy.

Proposed backend boundary: `capabilities()` returns immutable supported primitive,
window, option, device and calibration-domain information; `evaluate(request,
deadline, cancellation)` returns a typed advisory response; `close()` releases only
idle resources. The consumer recomputes state/question/manifest digests rather than
trusting hashes supplied by a caller. No backend method issues grants or certificates.
Transport and ML-backend exceptions map to precise refusal/defer reasons.

Illustrative decision: a boolean "Does the proposed call have a supplied city?"
has logical options false/true. If probabilities are [0.9, 0.1], P(true) is 0.1 and
raw top probability is 0.9 for the false answer. Neither value means a 90% guarantee
that all arguments or effects are valid. The deterministic argument validator and
the independently bound operator authority are still required. A rule-derived row
does not become calibrated merely by returning a normalized distribution.

## Standard-library v1 technical resolution

The bounded first implementation is specified in the
[standard-library reference profile](stdlib-v1.md). This resolves T001's
conditional technical gaps: exact raw/canonical budgets, finite JSON and depth
handling, status/distribution invariants, synthetic-only rule capability,
separate default/diagnostic policies and monotonic cancellation publication.
These are provisional feature-local choices pending fresh Luna review, not
founder acceptance or canonical ADR adoption. T001 remains pending.

The initial 1 MiB bound applies to raw UTF-8 bytes **before parsing** and also
to canonical output. The reference's character-token unit is explicit and
counts the entire rendered envelope. Binary64 standard-library reference
arithmetic meets the general fp32-or-stronger minimum without implying neural
hardware support. Unknown numeric/token/device envelopes cannot be inferred
from this reference profile. No neural backend is implemented under it.

For SPEC-028/T002–T008, the linked `stdlib-v1.md` profile is the exact implementation scope. The generic neural-worker/device ceilings above describe a future profile only; this cut has no neural backend. Core ingress accepts already-materialized bounded UTF-8 bytes. CLI source-file I/O is separately bounded and is outside the core deadline guarantee; no stdin/socket ingress or interruptible filesystem-read guarantee is shipped.
