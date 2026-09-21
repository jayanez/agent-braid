# ADR 0007: Python reference analyzer before runtime execution

## Status

Accepted for implementation by the founder's explicit request to implement the
open-tooling plan. This decision does not authorize production execution.

## Context

The M1 analyzer needs a small, inspectable implementation that can reuse the
bounded certificate checker while the public semantics remain draft contracts.
The repository already uses dependency-free Python for validators and the finite
laboratory. The roadmap had deliberately deferred the implementation language.

## Decision

Implement the first `agent-braid` CLI in Python 3.12. Its analysis core uses the
standard library, consumes AIM 0.2 records and emits a separate
`0.1.0-alpha` analysis report. The initial rules use exact resource identity and
conservative effect footprints. They may return `independent-candidate`, but no
classification authorizes concurrent execution.

The CLI is read-only. It does not invoke agents, tools, Git, network services or
external effects. Vendor traces require a reviewed adapter that preserves
identity, effects and evidence before the core analyzes them.

## Alternatives

- A production runtime would freeze execution semantics before M1 evidence exists.
- An LLM classifier could cover more cases but would not supply deterministic or
  independently checkable premises.
- A plugin-first implementation would privilege a distribution channel before a
  useful product surface exists.

## Consequences

Python is a reference implementation choice, not a permanent protocol
requirement. New languages may implement the contracts independently. A future
runtime, adapter or stronger semantic rule requires its own review and tests.

