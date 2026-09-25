# ADR 0015: Real-repository M2 validation profile

- **Status:** Accepted by explicit founder decision on 2026-09-25 for the
  validation profile only. Repository-code execution remains unauthorized
  pending a separate decision on exact inputs.
- **Date:** 2026-09-25; accepted 2026-09-25
- **Deciders:** Juan Antonio Yáñez García, founder
- **Constitutional articles:** 2, 4, 6, 7, 9, 12–14, 19–20, 23

## Context

ADR 0014 accepts a local, read-only Git-only T013 prototype. Its synthetic
fixed-patch tree results do not establish behavior for real code, validation
commands, live agents, or concurrent tree merging. M2 needs a practical
falsification case before widening its scheduler claims.

## Proposal

Use two or three distinct, reviewed Agent Braid workstream commits descending
from one frozen `develop` commit. Each source and its pull request are registered
before running the experiment. A read-only preflight verifies local Git identity,
immutable commits, common ancestry and an unchanged target ref. This is a
necessary input check, not proof that the pull requests were approved or that
their effects are complete.

After a separate founder decision accepts this profile and the exact corpus,
run the existing Git-only T013 preparation and serial-reference comparison in
the pinned Linux Docker environment. Only if its result passes the declared
tree and stale-base checks may a later implementation materialize the candidate
and serial trees in separate private containers and run the single allowlisted
command `python -m unittest discover -s tests` in each. Use the same frozen
source, image digest and dependency set for both lanes. Disable network, hooks,
credentials, host writes and repository ref updates. Cap each container at two
CPUs, 2 GiB memory, 512 processes and 180 seconds; capture at most 8 MiB of
output and record truncation as inconclusive. If the image lacks the required
dependencies, stop rather than install them during the experiment.

Admit a useful result only when both lanes pass the same declared tests and
produce the same tracked tree, with complete provenance and no unsafe
admission in the negative corpus. Record elapsed time, CPU, peak memory,
temporary data, Git command count, test outcomes and rejected or inconclusive
cases. Test failure, hidden effects, stale base, missing input, resource breach
or non-repeatability must not be converted into a successful parallelism claim.
No result may promote a ref or set `executionAuthorization` to true.

## Founder decision

The founder accepted this validation profile on 2026-09-25, including its
allowlisted command, isolation policy, resource caps, observation contract and
fail-closed outcomes. The [decision record](../../specs/013-m2-real-workload/adr-0015-founder-decision.json)
binds the reviewed proposal bytes and the exact scope of that approval.

No real-workstream corpus, frozen base, image digest or dependency set was
approved in this decision. Repository-code execution, the container command
stage and the experiment require a separate founder decision binding those
exact inputs. Acceptance of this profile is not a positive scientific result,
an M2 closure decision or execution authorization.

## Consequences and review boundary

The preflight checker may be implemented and tested without executing project
code. The container command stage, registered real corpus and actual experiment
remain pending until the founder separately approves the exact experiment
inputs under this accepted profile. Changing the command, image, resources,
observation contract or target repository requires renewed review. Even a
positive result supports only the registered finite workload and does not
close M2 or establish live-agent safety.
