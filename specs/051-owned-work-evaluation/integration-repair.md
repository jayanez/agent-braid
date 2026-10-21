# Integration metadata correction

The first new quick/pr attempt completed with seven errors per profile (not
independent failures): four inventory callers, two assurance subcases and the Spec Kit baseline check.
Three concrete causes: omitted local SPEC-051 mapping, unqualified new Python test
references, and a stale CURRENT draft/pending SPEC-047 authority inventory after
adding ADR 0026. No pure-module fix was required. Raw attempts are retained.

Add SPEC-051 as OPEN under existing FC.2 in local tracking metadata; this creates
no remote issue/milestone and closes none. Qualify our scenario test references.
For SPEC-047, scope-reviewed the new ADR's isolation from numeric aggregates,
defaults and source admission; add only its authority hash to the CURRENT draft.
All old hash bindings, requirements/scenarios/evidence/scope, stage=draft and
human_review=pending remain unchanged. Historical snapshots and sealed packets
remain byte-exact. This refresh is not human approval or activation.

Re-run the three affected test methods and actual profiles on the corrected
metadata candidate. Earlier failed profiles remain failed and are never relabeled.
