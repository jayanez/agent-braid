<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# SPEC-041 real-use acceptance: owner decision, 2026-11-01

**Status:** owner decision, recorded by the coordinator session.
**Evidence:** [decision packet](evidence/decision-packet-20261101.md) and its receipts,
merged in #855.

## Decision

After reading the decision packet, the owner was asked what to do with the SPEC-041
tasks whose reopen criterion was observed. The owner answered
"Cerrar con evidencia (Recommended)" (close with evidence). For the partly observed
tasks, the owner answered "Mantener aparcadas (Recommended)" (keep parked).

## Effect

| Task | Issue | Disposition | Basis |
|---|---|---|---|
| T003 | #420 | **Ticked** | `plan` skill, then MCP `prepare` with a verified plan; order and missing operator grant disclosed in the same session |
| T004 | #421 | **Ticked** | `execute` on an owner grant reached `verified-completed` with independent `verify`; unissued, consumed and expired grants refused |
| T005 | #422 | **Ticked** | a real interrupted run recovered through MCP `recover` with a new owner grant and verified; `recover` on a completed run refused |
| T007 | #424 | **Ticked** | `execute` skill loaded without MCP `execute`; it refused and used the read-only `analyze-git` fallback |

Kept in `Deferred` under the 2026-10-31 reopen criteria, with the packet linked as
partial evidence: SPEC-041 T001, T006 and T008; SPEC-043 T001 and T003. SPEC-041 T009
and T010, and SPEC-043 T008 to T010, stay in `Deferred` unchanged.

## Boundaries

- The evidence is observational real use: one owner, one host (Claude Code), one
  scratch repository, guided order. It is not preregistered and not bound to a frozen
  candidate.
- The ticks accept the observed behaviour for these four tasks only. They imply no
  Codex coverage, comparison, utility claim, clean-room reproduction, candidate freeze
  (T009/T010) or founder acceptance of SPEC-041 as a whole.
- The parent SPEC-041 (#417) stays open.
