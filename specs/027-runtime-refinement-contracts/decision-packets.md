# Technical capability packets

Founder dispositions for the three bounded-M4-alpha capability decisions are recorded in
[evidence/founder-capability-dispositions-20261008.json](evidence/founder-capability-dispositions-20261008.json)
(SHA-256 `c5a12182ba037420dac09661205636f027db4b72899bb84265c30265e7b0e42f`). All three are approved NO-GO/defer decisions for bounded M4 alpha only.
No expanded runtime capability or implementation was adopted. The frozen
[recommendation packet](capability-disposition-packet.md) remains unchanged; these
current dispositions supersede its pending-decision status without changing its text.

- Promotion: local proposal/refusal controls are implemented. Consumer verification,
  exact grant, exclusive state/CAS and adopted contract remain missing; bounded-M4-alpha disposition is NO-GO/defer. Fallback:
  export/manual integration. Reconsider after a separately reviewed publication cut.
- Code checks: installed executable inventory is implemented; zero probes run.
  Enforcement unverified; the bounded-M4-alpha disposition is NO-GO/defer. Fallback: read-only analysis. Reconsider
  after exact harmless-probe approval and measured enforcement, not command presence.
- External effects: synthetic attempt/failure controls implemented. No provider,
  rights or adapter refinement selected; the bounded-M4-alpha disposition is NO-GO/defer. Fallback:
  abstract simulation. Reconsider with a separately authorized adapter-specific cut.

Tests cover disposable clean/stale/dirty/attached/missing target observations,
existing grant refusal, before/after/unknown abstract publication faults, partial
visible effects and ambiguous timeout. These are bounded technical checks, not
scientific proof, production isolation or independent external validation.
