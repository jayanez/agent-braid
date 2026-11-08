# ADR 0041: Consent, redaction and retention for content-bearing traces

- **Status:** accepted by the owner on 2026-11-08 ([founder decisions](../development/FOUNDER_DECISIONS_20261108.md), decision 3); applies when SPEC-074 is delivered
- **Date:** 2026-11-08
- **Deciders:** Juan Antonio Yáñez García (owner)
- **Constitutional articles:** 0, 13, 14, 15
- **Specification:** [SPEC-074](../../specs/074-lightning-trace-consent/spec.md); foundations in [SPEC-070](../../specs/070-braid-lightning-foundations/spec.md)

## Context

ADR 0025 keeps local telemetry content-free (daily counters only). SPEC-066
shadow episodes are closed-vocabulary. Optimization and dataset export need
prompt and response text, which those contracts deliberately exclude.

## Decision

1. Braid Lightning records are content-free by default: identifiers, closed
   vocabularies, numbers and SHA-256 digests (SPEC-070).
2. Content-bearing traces are a separate record kind, refused until the owner
   records consent `redacted` through a setup preview, and only for the sources
   listed in `traces.sources`.
3. Content is redacted before it is written (secrets, tokens, key patterns,
   emails, home paths), with a versioned redactor and canary tests.
4. Retention defaults to 30 days and is capped at 90; `purge` deletes a run.
5. Nothing is uploaded. Telemetry and System One contracts are unchanged.

## Alternatives

- *Reuse telemetry:* forbidden by ADR 0025's content boundary.
- *Store raw transcripts:* unacceptable secret and privacy exposure.

## Consequences

Optimization in SPEC-072 runs on rollout records and the laboratory's own
prompt sets; content-bearing traces become available only after SPEC-074.
