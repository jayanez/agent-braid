# Implementation plan

## Technical context and scope

Use the existing 2–4 operation Git request, M1 provenance and fixed patches.
Keep `produce`, `verify`, the CLI, evidence and advisory plan schemas exhaustive.
Add a private order reducer and comparison function that runs selected orders
in isolated scratch state and checks them against independently verified full
replay evidence.

## Constitution check before research

Clause zero and Articles 2, 4, 6, 9, 13, 14, 19, 20 and 23 require explicit
order, observation, finite domain, negative controls and non-authorizing
results. ADR 0013 prohibits turning patch replay into an execution scheduler.
The private experiment changes none of these boundaries.

## Research, assumptions and alternatives

See `research.md`. The selected equivalence is generated only by adjacent
swaps of conservative path-disjoint operations. Unlike a sleep-set search, the
algorithm still enumerates at most 24 topological orders and reduces only the
number of Git replays. The exhaustive engine remains an independent oracle.

## Design and compatibility

1. Derive path sets from existing Git provenance, supported-operation
   assessment and fixed patches. Treat uncertain, binary and unsupported
   operations as dependent on all others. Close declared dependencies
   transitively and include path-prefix collisions.
2. Build connected components of admissible orders under legal adjacent
   independent swaps. Select one stable representative per component and keep
   a complete coverage map.
3. Add a private selected-order replay path using the existing sanitized Git
   environment, fresh index, patch application and resource bounds. Compare
   those schedules against independently verified exhaustive evidence. Never
   serialize a partial schedule list as public evidence.
4. Use a repeated-context real-Git divergence plus one disjoint patch to
   exercise SPEC-015's verified positive reduction path.

## Validation strategy

REQ-001/SC-001–002: pure relation tests with common prerequisites, prefix
collisions and unsupported operations. REQ-002/SC-003–004: exhaustive finite
partition controls. REQ-003/SC-005–006: real-Git selected replay and oracle
comparison, tamper and incomplete controls, and byte-compatible public replay
regressions. REQ-004/SC-007: real-Git reducer fixture with an independently
verified smaller witness. Run focused tests, Spec Kit validation, proportional quick
and stable PR profiles. Capture actual commands and outputs in feature evidence;
the profile does not itself grant a scientific or human decision.

## Constitution check after design

No reduced replay result is promoted to a certificate, plan, ref update or
execution authority. The experiment reports syntactic finite evidence only.

## Human review and unresolved decisions

Freeze the candidate and request scoped review of the independence predicate,
oracle comparison and limitations. Independent external validation remains
pending. Promotion to a public reducer or broader adapter requires a separate
contract and review.
