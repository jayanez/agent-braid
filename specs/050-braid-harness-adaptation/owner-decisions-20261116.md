# Owner decisions, 2026-11-16 (SPEC-050 and the HAR operational release)

These decisions come from the owner's interactive answers in the HAR wave-plan session. Each
question was guided: it listed options with risks and undo paths, and the owner chose one.
They add to [owner-decisions-20261113.md](owner-decisions-20261113.md), which stays as
written. None of them authorizes native execution, adopts an ADR or a contract, or activates
anything.

| # | Topic | Chosen option, as offered | Effect |
|---|---|---|---|
| E1 | T004 E3 effect contract ([effect-contract-decision.md](effect-contract-decision.md)) | "B: adopt now, qualify after T014 (Recommended)" | 1. Draft the E3 contract (allow-list by hash, caps, timeout, no network, private `out/`, distinct checker) as a versioned amendment to `contracts/interface.md` §7 and §8.<br>2. Implement the subprocess adapter against deterministic doubles only.<br>3. After SPEC-049/T014, a separate SPEC-065 re-qualification adds the pinned helpers to the exec allow-list. That re-qualification is light only under FD-20261114-STANDING, which holds until HAR.1 closes or 2027-01-31.<br>4. One contained helper run then becomes the T004 evidence.<br>E4 (network, provider or model session) stays blocked. Nothing changes the containment before T014. |
| E2 | Harness product surface | "Contrato MCP ya, publicar tras T014 (Recommended)" | Native execution over MCP is excluded in every case.<br>1. Specify a versioned, read-only MCP contract now, under its own spec.<br>2. Publish it only if, after T014, the D7 ADR does not close the harness as experimental.<br>Until then, access stays the experimental CLI (D3). |
| E3 | Codex | "Revisor ahora + nativo como tareas (Recommended)" | Codex runs in the operator account on this Mac (ChatGPT.app CLI 0.169.0-alpha.11.1). It reviews and verifies through repository packets. Native Codex qualification becomes concrete tasks in a later milestone, and HAR.1 closes as "native Claude; Codex pending with tasks". Codex is never copied into the contained lab. |

E2 and E3 are recorded here because they set the scope of the SPEC-050/T012 portfolio and of
the HAR.3 closure. They also cover SPEC-048 and SPEC-049, whose own records may cite this file.
