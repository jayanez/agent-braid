# Proposed source promotion contract

Version: runtime-refinement-assessment-v1. Status: proposed, not adopted.

The first proposed publication operation targets one exact local branch ref in a
named owned repository. Bind expected old commit, verified result tree and full
input/operation identities. Existing private-run grants are refused, including
caller records claiming promotion scope. A later separate implementation must
verify the consumer evidence, obtain a promotion-specific operator grant, acquire
an exclusive coordinator boundary and revalidate the ref, worktrees/index, source
ownership and expected old object immediately before CAS. No dirty, attached,
locked, prunable, missing or unknown worktree target is eligible in this first cut.
Untracked files are dirty state. Reject unrelated refs and unsupported identities.

This assessment invokes only bounded read-only Git observations with optional
locks disabled and filesystem monitoring disabled. It never updates a ref, runs
hooks/project code or creates a grant. `proposal-only` means the observed state
passed these local checks; it leaves independent-result verification and all
publication prerequisites pending. It is not a TOCTOU-resistant publication check.
Read-only observation can race with concurrent mutation and must be repeated under
the later exclusive publication boundary.

Fault controls are explicitly abstract: before-CAS means no publication proposed;
after-CAS means a visible published effect would need reconciliation; unknown
means do not automatically retry. Never compensate by claiming published history
was not observed. Preserve durable intent and before/after object identities in a
future implementation; this script writes no coordinator state.
