# ADR 0034: System One shadow mode and advisory boundary

- **Status:** accepted as amended by the owner on 2026-11-01 (see [founder decisions](../development/FOUNDER_DECISIONS_20261101.md), decisions 2-3): no external services and no third-party decision models, ever; the learned layer is native. The SPEC-066 scope review (T001) was accepted on the same date ([owner review](../../specs/066-system-one-shadow/owner-review-20261101.md)).
- **Date:** 2026-11-01
- **Deciders:** Juan Antonio Yáñez García (owner)
- **Constitutional articles:** 0, 6, 13, 20, 21, 22, 24
- **Specification:** [SPEC-066](../../specs/066-system-one-shadow/spec.md) (track S1.5)
- **Episode contract:** [agent-braid-s1-episode/v0.1](../../specs/066-system-one-shadow/contracts/episode-v0.1.md), enriched by [v0.2](../../specs/066-system-one-shadow/contracts/episode-v0.2.md) (structural features and per-repo salted hashes; v0.1 stays readable)

## Context

The System One program (SPEC-028 onward, milestones S1.0–S1.4) ended in
engineering delivery and mostly negative or unregistered science. About 4,360
lines (`agent_braid/system_one*.py`, `mcp_advice.py`) are on `develop` but have no
product callers; the only entry point is the opt-in `agent-braid system-one`
command over synthetic fixtures. The backend is the rule fixture
`stdlib-rule-fixture-v1` with no calibration, and the SPEC-029 T009 registered
comparison never ran. The S1.0–S1.4 milestones were closed on 2026-10-31 by
founder decision ("Cerrar como diferido"); the remaining open S1 issues sit in the
Deferred milestone. SPEC-047 telemetry cannot observe System One, and real-use
sources show zero System One invocations against 44 product calls.

On 2026-11-01 the owner chose the option "Shadow + datos propios (Recommended)"
and asked to adopt the strongest Laya and Jev capabilities (decision record:
[founder decisions](../development/FOUNDER_DECISIONS_20261101.md); completeness
audit: [addendum](../system-one/addenda/completeness-audit-20261101/README.md)).
The upstream survey is in the
[2026-11-01 update](../../specs/028-system-one-core/reference-analysis.md) of the
reference analysis. Its numbers are upstream-reported, not reproduced.

Three constraints shape the decision. Hosted Jev sends state off the machine, is
paid, and documents adversarial state steering, so its output cannot be a
boundary. Laya's confidence is poorly calibrated out of the box (reported ECE
0.466 before refit) and its zero-shot accuracy is near chance. The SPEC-047/057
telemetry boundary allows aggregates only, which cannot carry per-decision
evidence. Article 20 separates analysis from execution.

## Decision

1. **Modes per decision point.** Each decision point has a mode: `off` (default),
   `shadow` or `advise`. Unconfigured means `off`. Only `off` and `shadow` are
   implemented by SPEC-066 S1.5a.
2. **Shadow never changes outputs.** In `shadow`, System One runs after the real
   output is fixed and its result goes only to the episode store. A shadow
   failure, refusal or timeout leaves the output byte-identical to `off`, checked
   by a byte-parity test over every wired decision point.
3. **Episodes are local, private and structural-only.** Episodes follow
   `agent-braid-s1-episode/v0.1`: no content, paths or identifiers, local files,
   bounded retention (30 days). They are a store separate from the SPEC-047
   telemetry aggregates, which stay aggregate-only and gain no metric beyond the
   `system-one` operation. `plugin-status` reports mode and store, never
   episode contents.
4. **No authority from confidence.** Confidence, abstention and any score never
   grant authority. `executionAuthorization` stays `false` on every System One
   output. State fed to a backend can be prompt-injected, so System One output is
   a signal for a human or for System 2, never a boundary or a permission.
5. **No deletion by score.** A score never removes, hides or skips an item. At
   most it reorders or annotates, and the full set remains available.
6. **Pinned identity with drift demotion.** Every episode records backend
   identifier, model-manifest digest and analyzer rule set. A different identity,
   or mixed identities in one batch is refused. S1.5a records `refused`
   (`identity-mismatch`); the demotion of the decision point to `off` until a new
   calibration is pinned is S1.5c (SPEC-066 REQ-203).
   Floating aliases (for example `jev-latest`) are never accepted as identity.
7. **Abstention and declared confidence.** Responses carry the tri-state
   `passed | abstained | unevaluated`, the echoed threshold, and two named
   confidence signals with stated formulas. Neither is called accuracy.
   Thresholds are fitted per bucket on a calibration split disjoint from
   evaluation.
8. **Promotion to `advise` by owner decision only.** A decision point moves to
   `advise` only after an owner go decision on recorded shadow evidence, against
   the hypothesis and risk budget of SPEC-066, with atomic rollback to `off`. No
   automatic promotion, no learned act head.
9. **External services and third-party models excluded (owner direction
   2026-11-01).** No external service (Jev/TypeSafe or any hosted service), no
   third-party decision model or local backend (Laya, Von, kev, Rizzo, SemIf,
   Nimble, NanoJev, Strands Decider) and no generic pretrained encoder
   (ModernBERT, mmBERT, Qwen and the like) is ever used, under or beside System
   One. Laya and Jev are design references only: their ideas are re-implemented by
   us.
10. **The learned layer is native.** The learned model (SPEC-066 REQ-301) is a
    small native stdlib model inside `agent_braid` (calibrated logistic regression
    or boosted trees over structural features) with our own architecture, training
    and weights, trained only on the owner's own work (real runs and git-history
    replay of plugin-registered workspaces). It has no downloads and no extra
    dependency. It is compared with the rule backend and the SPEC-019 linear model
    at a common risk budget; a NO-GO is a valid result.
11. **Claim level** (labels of
    [claim discipline](../theory/CLAIM_DISCIPLINE.md)): engineering, plus the
    hypothesis H-S1 of SPEC-066. Upstream capabilities are design references
    only; this carries no claim that upstream-reported accuracy transfers to
    Agent Braid.

## Alternatives considered

- **Retire System One.** Rejected by the owner: the contract and fail-closed
  machinery are reusable, and without real data the question stays untested.
  Retirement remains the outcome if shadow evidence is NO-GO.
- **Model-first (SPEC-030 learned backend before any wiring).** Rejected: without
  episodes there is no owned population to train, calibrate or evaluate on, and
  third-party sources stay excluded.
- **Wire `advise` immediately.** Rejected: no calibration, no pinned backend, no
  observed outcomes. It would let an uncalibrated signal influence outputs.
- **Hosted Jev, or any third-party model, as a backend.** Rejected permanently
  (item 9): egress, cost, documented adversarial steering, and the owner's
  direction that the decision layer be fully native.
- **Store episodes in the telemetry store.** Rejected: SPEC-047/057 boundaries.

## Consequences

- Positive: real-use evidence accumulates without any behavior change;
  promotion becomes an evidence-backed owner decision; the milestone history is
  reconciled with what is wired.
- Negative: more code on the hot path of the wired decision points (guarded by
  the parity test); a new local store; unwired code stays until wired or removed.
- Uncertain: whether any local backend beats rules at an acceptable false
  independence rate (hypothesis H-S1 in SPEC-066); upstream numbers may not
  transfer.
- Compatibility: additive; default `off` leaves every existing output unchanged.
- Security: the injection surface is state, not authority; episodes are
  structural-only and local; no network use in the core.
- Research: upstream results are reports, not reproductions. Observed outcomes
  from the owner's own work are the primary labels.

## Validation

SPEC-066 byte-parity, identity-mismatch, retention and plugin-status procedures
and the evaluation gate (REQ-206). The decision is revisited at the first
promotion checkpoint, when a backend identity changes, or if the shadow period
shows no usable signal (retire path).

## References

- [SPEC-066](../../specs/066-system-one-shadow/spec.md)
- [Episode contract v0.1](../../specs/066-system-one-shadow/contracts/episode-v0.1.md)
- [Episode contract v0.2](../../specs/066-system-one-shadow/contracts/episode-v0.2.md)
- [Reference analysis, 2026-11-01 update](../../specs/028-system-one-core/reference-analysis.md)
- [Founder decisions 2026-11-01](../development/FOUNDER_DECISIONS_20261101.md)
- [Completeness audit addendum](../system-one/addenda/completeness-audit-20261101/README.md)
- [ADR 0026: pure owned-work validation](0026-pure-owned-work-validation.md)
- [ADR 0032: activity viewer companion](0032-activity-viewer-companion.md)
- [Telemetry](../tooling/TELEMETRY.md)
