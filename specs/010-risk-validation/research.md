# Research: proportional validation without weaker gates

## Decision

Use deterministic path-based selection for development feedback, retain a complete
PR gate and reserve clean-room reproduction for evidence boundaries. Selection is
an optimization layer above existing validators, never a replacement for them.

## Observed cost distribution

Local observations on 2026-09-19 showed that foundational, contract and finite
scientific controls complete in well under one second. The complete unit suite took
about 45 seconds and the isolated Codex/Claude Spec Kit matrix about 97 seconds.
Clean-room release reproduction additionally creates a clone and environment and
installs pinned dependencies. Hardware, caches and repository growth will change
these durations.

The useful optimization is therefore not removing cheap invariants. It is avoiding
repeated full-suite, integration-matrix and clean-room work while a candidate is
still changing.

## Alternatives

### Always run every check

This has simple semantics but poor feedback and repeatedly invalidates evidence
before a candidate is stable. Retained only as the explicit final/sensitive option.

### Run only tests selected from changed paths

Rejected as the merge gate. Files can have undeclared transitive effects, so path
selection alone cannot protect repository-wide compatibility.

### Depend on a third-party CI path-filter action

Rejected. A small standard-library classifier is reviewable, testable locally and
avoids expanding the workflow supply chain.

### Infer semantic dependencies automatically

Out of scope. Static path mapping does not establish semantic independence and
must not be presented as Agent Braid analysis evidence.

## Limits and revision triggers

The path map can become stale when new directories or validators appear. Unknown
paths therefore select the sensitive fallback. Changes to the classifier, workflow
or validation instructions classify themselves as sensitive. Revisit the map when
adding a new top-level artifact class, public contract, evidence protocol or CI
integration.
