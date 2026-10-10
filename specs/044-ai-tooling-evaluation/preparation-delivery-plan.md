<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# M4.5 five-task preparation delivery

The owner authorized implementation and integrated delivery of this plan on
2026-10-10. It supplements the prospective evaluation plan; it does not waive its
acceptance procedures. The active goal covers all five preparation tasks below,
including independent technical review, validated merges and tracking alignment.
Additional spending is EUR 0. Existing subscription quotas do not authorize API
pay-as-you-go use. Human outcome evaluation remains deferred.

## Ordered work and evidence

| Priority | Preparation task | Deliverable and completion evidence |
|---|---|---|
| 1 | Freeze dependencies | Target-specific complete MCP 2.3.0 closures for CPython 3.13.11 on macOS ARM64 and Debian bookworm Linux x86_64; exact distribution versions, hashes and declared license metadata; retained downloadable artifacts and offline installation inputs. Core dependencies remain empty. |
| 2 | Verify installed macOS artifacts | Fresh isolated core and tooling installations from a frozen candidate wheel, outside the checkout; installed module/CLI origins, five packaged skills and supporting assets, CLI/doctor boundaries, SDK stdio negotiation in auto and legacy modes, resources/prompts, read-only synthetic AIM parity and negative controls. Retain actual subprocess exit, time/output bounds, commands, hashes and failures. |
| 3 | Prepare Linux reproduction | A pinned Linux AMD64 image manifest and CPython 3.13.11 recipe consuming the frozen artifacts and shared verifier offline; explicit architecture/hash preconditions and refusal checks. Preparation is complete independently of executing registered Linux reproduction. |
| 4 | Consolidate evidence | Private complete traces and artifact inventory; reviewed privacy-minimized public proof with source/artifact/environment identities, executed checks, limitations and task mapping. Independent Luna Latest technical review of the exact candidate and evidence, with findings resolved or explicitly retained. |
| 5 | Align documentation and tracking | Audit M4/M4.5 documentation, including the main README, architecture, roadmap, plans and tooling guides. Preserve M4's bounded closure and G4 NO-GO. Merge only the reviewed, validated authorized lot. Reconcile scoped GitHub milestones/issues/tasks and independently verify the private Project Dashboard against canonical source state. |

Tasks 1 and 2 lead the delivery. Linux recipe preparation proceeds in parallel
using task 1's target closure and task 2's shared verifier. Documentation audit can
proceed alongside implementation; final status changes depend on observed evidence.
The primary session owns integration commits, evidence packaging, documentation
and remote reconciliation. Parallel helpers own non-overlapping implementation
paths. No helper may revert another contributor's edits.

## Validation and delivery gates

Start from current public `develop` in an independent clone, restore only reviewed
public provenance and pass Spec Kit preflight and feature prerequisites. Integrate
the existing implementation branch by normal merge. After coherent increments run
the quick validation profile; on the stable candidate run the PR profile and
independent review. Freeze source before building and installed-artifact checks;
later evidence/documentation commits retain the earlier exact candidate binding.
Every merged commit needs its own applicable validation and hosted checks.

After merge, audit M4 milestone 6 and M4.5 milestone 19 separately from clean
`develop`, review any proposed tracking plan, apply only its approved scope and
verify empty remaining operations. Project custom statuses require an independent
actual view; issue state alone does not establish Dashboard alignment.

## Completion boundaries

This preparation goal does not execute or claim the 108 registered attempts,
native Codex/Claude host acceptance, approved complete registration, registered
macOS/Linux reproduction, human ratings/adjudication, release or formal M4.5
closure. Those obligations remain in the canonical task list. Local installed
checks and Linux recipe preparation do not complete SPEC-044 T004. Technical
review of this preparation does not complete the later T008 decision packet.
Historical evidence retains its own source identities and observation boundary.
Check canonical task boxes only when their complete paired procedure is evidenced.

M4 is already closed under its separate bounded owner decision. This delivery
preserves its negative utility interpretation and G4 NO-GO. M3.5 software progress
does not establish real-source capture or predictor scientific acceptance; its
unrelated experimental gates remain open.
