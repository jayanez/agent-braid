# ADR 0040: Vendoring microsoft/agent-lightning (MIT) into AGPL modules

- **Status:** accepted by the founder on 2026-11-08 (SPEC-070 T001; [founder decisions](../development/FOUNDER_DECISIONS_20261108.md), decision 2)
- **Date:** 2026-11-08
- **Deciders:** Juan Antonio Yáñez García (owner, founder)
- **Constitutional articles:** 0, 23
- **Specification:** [SPEC-070](../../specs/070-braid-lightning-foundations/spec.md) REQ-002

## Context

GOVERNANCE.md requires an ADR and the founder for changes to the license
boundary. Precedents: ADR 0012 (MIT python-skills), ADR 0027 (Apache-2.0
Harness²) and ADR 0033 (MIT three.js). The owner asked to copy as much upstream
code as useful; agent-lightning is MIT on both pinned commits.

## Decision

1. Adapted upstream portions keep MIT terms; the license is retained verbatim
   in `LICENSES/Agent-Lightning-MIT.txt`.
2. Each adapted module is `SPDX-License-Identifier: AGPL-3.0-only` and carries a
   notice naming the upstream path, pinned commit, copyright holder, MIT
   license and a summary of changes.
3. `docs/development/THIRD_PARTY.md` and
   `specs/070-braid-lightning-foundations/third-party-inventory.md` bind the
   pinned commits and complete original file hashes; later specs extend the
   inventory before porting further files.
4. Only standard-library code enters the core. GPU dependencies (verl, vLLM,
   torch, Ray) may enter only through a deferred optional extra under ADR 0042.
5. "Braid Lightning" credits the upstream name and implies no endorsement.

## Alternatives

- *Depend on the `agentlightning` package:* pulls FastAPI, Hydra, kr8s and, on
  v0.x, AgentOps and LiteLLM into a dependency-free core. Rejected.
- *Clean-room rewrite:* loses provenance clarity with no licensing benefit.

## Consequences

MIT is compatible with AGPL-3.0-only distribution; the combined modules are
distributed under AGPL with MIT notices preserved. No existing license
assignment changes.
