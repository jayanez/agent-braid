# M2 adversarial scientific source review

**Prepared:** 2026-09-27

**Status:** internal adversarial assessment for the SPEC-017 candidate. This is
neither an independent reproduction nor a founder scientific decision.

**Question:** Do adjacent scientific results support a stronger reading of the
four M2 exit criteria than the repository's finite Git evidence actually
establishes? The answer below is deliberately framed as attempted
falsification. External papers define other systems and cannot validate Agent
Braid's implementation by association.

## Source method and provenance

Consensus search was used to discover records; `fetch(id)` was called before
using each record. Claims below were checked against the linked primary
author/publisher pages, not inferred from search snippets or citation counts.
This is a targeted comparison, not a systematic literature review. No external
paper's code, benchmark or proof was reproduced here.

| Source | Retrieval and status | Adversarial use |
| --- | --- | --- |
| [Flanagan and Godefroid, *Dynamic Partial-Order Reduction for Model Checking Software* (POPL 2005)](https://escholarship.org/content/qt47c9f29c/qt47c9f29c_noSplash_80358420125f3e8fde2042820c861864.pdf) | Consensus `df5c498cfba25d68b794bf4494a3d69e`; original paper | Its valid independence relation requires preservation of enabledness and commutation across relevant states. Test whether SPEC-016's syntactic path relation proves either. |
| [Bailis et al., *Coordination Avoidance in Database Systems* (PVLDB 2014)](https://arxiv.org/abs/1402.2237) | Consensus `c1c16bfccdb35374a332a01b7113277a`; author preprint of published work | Application invariants determine when coordination can be omitted. Test whether disjoint Git writes establish an application invariant. |
| [Lyu et al., *CoAgent: Concurrency Control for Multi-Agent Systems* (arXiv 2026)](https://arxiv.org/html/2606.15376v1) | Consensus `3c0ef19d9a81540eb3ec2d990ae55a5c`; unreviewed author preprint, submitted to ATC 2026 | Compare correctness objects, assumptions and workloads before any novelty, serializability or speed claim. |
| [Yang et al., *Position: Multi-Agent Systems Should Prioritize Concurrency Control* (arXiv 2026)](https://arxiv.org/abs/2608.18092) | Consensus `1fc86dbaa02253188eac9da25fbfc117`; argumentative preprint | Problem framing only. Its arXiv page says submitted 2026-06-06 although `2608` denotes August; metadata discrepancy remains unresolved. |
| [Debenedetti et al., *AgentDojo* (arXiv 2024)](https://arxiv.org/abs/2406.13352) | Consensus `2767c52e68cc5c859885fda9822f69d4`; author preprint | Challenge any extrapolation from a read-only Git prototype to live agents with external tools and untrusted observations. |

## Adversarial checks against the four exit criteria

| Criterion and attempted counterargument | Evidence actually available | Bounded finding |
| --- | --- | --- |
| **1. Reproducible certificates.** A regenerated oracle and a verifier can agree while sharing a faulty replay engine; finite schedule coverage says nothing about arbitrary tool traces. | SPEC-012 checks immutable 2–4 fixed-patch Git schedules and the verifier reruns the replay. SPEC-016's private reduction regenerates the exhaustive oracle, then calls the existing verifier, which shares the replay implementation. The final combined-candidate clean-room run is still required. | Support only deterministic reproduction within the fixed-patch Git model. Do not call the verifier implementation-independent or the reduction a proof of general partial-order soundness. |
| **2. Recovered parallelism.** A speedup on one selected corpus could be implementation overhead or hardware-specific; it cannot establish a better scheduler or universal agent throughput. CoAgent's ten hand-constructed contended two-agent cells and ten trials per cell use live tools and a different correctness target, so its reported speedup is not a comparable baseline. | The accepted SPEC-013 retest contains two registered batches of 30 paired Git-only samples. Its median paired improvement against equally optimized serial preparation was 11.33% and 12.62%, with the registered bootstrap lower bounds above zero. All 60 paired trees matched and unsafe admissions were zero. Both candidate and path-overlap schedulers formed the same single wave in this corpus. | Support a finite improvement in **parallel patch preparation** against the registered serial lane. The path-baseline gain is overhead reduction. No demonstrated wave-selection advantage, end-to-end agent speedup, production performance or comparison with CoAgent. |
| **3. Fixed observation.** Equal final tracked trees can conceal different intermediate results, hidden reads, external effects and violated application invariants. The POPL independence conditions and invariant-confluence work show why path separation alone cannot justify semantic interchange. | ADR 0013 fixes `tracked-tree-v1` before replay; raw step traces remain available; incomplete runs are not normalized into complete outcomes. The repository's CE3 and CE5 controls exhibit contextual and invariant counterexamples. `uncertainPaths` prevent SPEC-016 interchange. | The observation protocol is explicit and reproducible for complete Git replay. It is intentionally weaker than contextual equivalence, semantic commutation or invariant preservation. |
| **4. Safe default effects.** A plan flag and isolated Git preparation do not establish that arbitrary future agents cannot invoke a harmful tool or be redirected by untrusted data. AgentDojo studies such tool-use attacks in a different domain. | The present prototype prepares patches in isolated, read-only source workspaces and leaves `executionAuthorization: false`; registered tests and corpus checks found no unsafe admissions or source-ref promotion. Its temporary Git processes still have declared local resource limits and known overshoot/RSS caveats. | Support the current conservative default and absence of authorized execution in this bounded path. Do not claim a general sandbox, live-agent security, complete effect detection or safety for external adapters. |

## Cross-cutting attack on scientific interpretation

- **No theorem transfer:** POPL's reduction result assumes a valid semantic
  dependency relation. SPEC-016 uses a deliberately conservative syntactic
  heuristic plus finite comparison, not a proof that all possible Git/program
  states satisfy the theorem's premises.
- **No benchmark transfer:** CoAgent relies on declared tool footprints,
  undoable effects and agent self-healing; its proof and reported trials are
  conditional on those assumptions. Agent Braid does not implement that
  protocol. Its empirical results neither confirm nor refute Agent Braid's
  registered Git-only timing result.
- **No source-count authority:** Consensus indexing, a citation count or an
  arXiv abstract cannot upgrade an unreviewed preprint to peer-reviewed
  evidence. The position paper expresses an argument rather than an
  experimental validation of this repository.
- **Internal review is conflicted:** the founder is also the maintainer. Even a
  later founder scientific approval must retain
  `independent_validation: pending` until an external party reproduces or
  validates the claimed domain.

## Provisional conclusion for the frozen-candidate review

No cited source falsifies the possibility of a *bounded internal* M2 decision
under the existing fixed-patch Git scope. The sources do not support an inference
from that decision to general confluence, semantic interchange, serializability
of live agents, comparative superiority or production speed. The scientific
review must first inspect the exact candidate's clean-room result and retain
the narrower wording above. A failed or incomplete clean-room observation
would turn this provisional conclusion into an inconclusive or negative M2
finding; no literature comparison can override that result.
