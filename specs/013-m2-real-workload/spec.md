# Feature specification: bounded real-repository M2 validation

## Purpose and scope

Test whether the read-only Git integration prototype remains useful when its
source operations come from actual Agent Braid workstreams and a private
candidate tree is subjected to a pinned project test command. The experiment
does not run agents, merge to `develop`, promote refs or authorize concurrent
integration. ADR 0015 is a proposed profile and must be accepted before any
repository-code command is run under it.

## Requirements and scenarios

- **REQ-001 — registered immutable corpus.** A proposal names two or three
  distinct workstream PRs and source commits descending from one frozen public
  `develop` base. Preflight checks origin, exact commit IDs, common ancestry,
  and target-ref freshness without running project code.
  - **SC-043:** Valid distinct descendant commits produce a non-authorizing
    preflight record and do not change the source repository.
  - **SC-044:** A moved base, unavailable commit, duplicate source, unsupported
    profile or wrong repository fails before experiment execution.
- **REQ-002 — reviewed, isolated validation.** After explicit founder acceptance
  of the profile and corpus, compare private candidate and serial lanes from
  the same base in the pinned Docker runtime. Run only the declared unit-test
  command with network and host writes disabled. Report both Git and test
  outcomes; any failed, incomplete or mismatched lane is inconclusive.
  - **SC-045:** A registered compatible case produces equal tracked trees and
    separately recorded passing tests for candidate and serial lanes.
  - **SC-046:** A stale base, test failure, undeclared effect, resource breach or
    missing lane is rejected or inconclusive and never admitted as safe.
- **REQ-003 — bounded comparison and claim.** Compare wall time and resource
  use against serial and path-overlap baselines on the registered workload and
  retain negative controls. Report false admissions and limits, regardless of
  whether parallel preparation is faster.
  - **SC-047:** The evidence binds the corpus, image, commands, observations,
    baselines and complete outcomes while keeping `executionAuthorization: false`.

## Evidence and compatibility

The observation combines `tracked-tree-v1` with the exit status and bounded
output of one pinned unit-test invocation per lane. Passing tests do not prove
semantic equivalence, complete effect discovery, general confluence or runtime
safety. Existing AIM, analyzer, replay and T013 contracts remain unchanged.
This feature introduces an internal preflight manifest version only; it does
not add a public CLI or schema. Human review and clean-room reproduction are
separate from structural and unit checks.
