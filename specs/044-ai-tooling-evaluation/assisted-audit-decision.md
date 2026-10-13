<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Prospective assisted audit decision — 2026-10-13

The owner approved implementation of the M4.5 track plan in this conversation,
including a prospective 36-case human audit with two independent people,
exceptions, and compact blinded evidence. This records implementation scope and
the selected audit design. It does not approve an exact registration, source,
capture, appointed reviewer, observed rating, ADR adoption or milestone closure.

Registration-v6 keeps all 108 original intended attempts, 18 owned synthetic
fixtures, six prompts, three arms, two hosts, counterbalancing, original descriptive
thresholds, full technical accounting, and the EUR 0 additional-spend boundary.
Legacy registration-v1 through v5 and their human obligations remain unchanged.
The original CLI arm remains human operated. Additional automated CLI controls
have a separate synthetic/control domain and never replace its operator metrics.

Before capture, freeze a seed, the `sha256-host-class-fixture-v1` algorithm, the
complete roster and rubric, and two independent human roles. For each host and
journey class choose one fixture by the smallest canonical SHA-256 of
`{seed, host, journeyClass, fixtureId}`, with fixture ID breaking a tie. Review that
same fixture in all three arms: 36 cases and 72 initial human ratings. Outcomes
never influence this initial selection.

Evaluate all 108 cases using deterministic oracles and separate technical and
adversarial Luna Latest model reviews. Their labels do not become human ratings.
Missing/inconclusive evidence, unexpected outcomes, oracle disagreements and model
disagreements require human review. A confirmed human discrepancy expands its
host/class/arm cell to all three instances. Authority, privacy or false-success
incidents expand review to all 108 and suspend acceptance. Preserve every earlier
escalation when building the later required-case set.

Human packets retain expected/observed outcomes, required steps, bounded selected
redacted excerpts, immutable evidence links and limits. Omit model predictions and
structured host/arm/order from independent human packets; disclose remaining
blinding clues in source text. Full private source material remains inspectable.
Unknown values stay unknown. Report actual human coverage and unreviewed cases;
do not extrapolate human labels to the unaudited portion or a general population.

Appoint people and authenticate their records through the later human addendum
bound to the immutable technical registration. Resolve disagreements explicitly.
Human fees/time, cash reconciliation, economic completeness and founder decisions
retain their separate gates. Positive utility is unavailable until the applicable
registered evidence and costs support the stated claim.

Implementation: `agent_braid.tooling_human_audit`,
`agent_braid.tooling_evidence_packets`, and the separate source registration-v6.
Synthetic tests establish bounded software behavior, not native or human evidence.
