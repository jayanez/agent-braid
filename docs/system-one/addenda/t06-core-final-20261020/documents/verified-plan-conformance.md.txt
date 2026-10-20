# Verified-plan conformance and migration — DDP-T01

Status: documentary candidate. The proposed [decision](../028-system-one-core/contracts/verified-plan-v1.md) and [consumer](../031-system-one-integration/contracts/verified-plan-consumer-v1.md) contracts are not implemented. [Vectors](verified-plan-vectors.json) contain concrete inputs/mutations, expected boundaries and source/test anchors. No new study, native preparation, fixture generation, model, training or calibration ran to author them. Historical outcomes below come from sealed **development** records, not a fresh or independent accuracy evaluation. New hardening/budget vectors are planned expectations, not historical passes.

## Sources and checked migration

Truth source is the read-only research checkout, HEAD48f4226 plus WIP, not a public committed implementation candidate. Exact per-file SHA-256 values are in vectors.sourceBindings and the local receipt. Current documentary baseline is fe6d25b3d9fb989c230aa11779b6a51d494d7a4e, which contains PR #593 and later unrelated SPEC-047 changes. No equivalence between those code trees is presumed. T025 packet89ed6eaf9260ff90b7d7513feecdd0df2b7139eb7f331e5a88ffd38a2b655f87 and prior receipt693c3c791eba2dd16a0b2449ef3e66b0e029f34b13a7d35e42e51733c5f482fc remain immutable.

| Existing source/identity | Retained meaning | New contract disposition / non-equivalence |
|---|---|---|
| agent_braid/system_one.py; decision-stdlib-v1 | Synthetic boolean/choice/score, probabilities/strict abstention and original byte/depth limits | No edits/coercion. Reuse parser/canonical/freeze utilities; new result rejected by old validator. Deterministic eligibility is not P(true). |
| eof_verification/ingress.acquire; t022-ingress-v1 | Immutable commit/base, owned fixture root/marker, complete observed effects outrank declarations | Retain source envelope as a nested source; new request adds explicit budgets/identity. No arbitrary repository or private-history admission. |
| boundary_verification/adapter.project + eof_verification/adapter.project | Acquire actual path/blobs/hunks and actual diff prefix markers; snapshot semanticVersion t024-eof-context-v1 | New AcquiredSnapshot wraps the full observed snapshot and raw program; new explicit IR/observation names are not old implementation wire versions. No digest renaming or declaration-as-observation shortcut. |
| eof_verification/verifier.validate/apply_changes/run_plan | Exact LF bounded domain, unique anchors, literal dependencies, staged multifile application; EOF constrained only without retained trailing context | Preserve unchanged. Final changed-path blob equality is narrower than whole native tree equality; do not call either universal commutation/confluence. |
| eof_verification/language.render/extract; t024-text-v1 | Exact EN/ES controlled/symbolic literal record round trip, <=65,536bytes/96lines | Retain grammar. Strict duplicate/nonfinite/bounded-number inner literal admission is proposed hardening; old inner json.loads is not claimed equivalent for malicious literals. |
| verifier.verify -> answered / semantic-defer / refused | All three non-null offered plans, min operation-count eligible set, ASCII lexical tie selection, null plan represented by its offered ID | Preserve eligible set/cost/tie rule. New outer selectedOptionId=null on defer/refused; retain defer ID in verifierResult. Do not equate raw wait choice with a prepared action. |
| t025-native-decision-v1 / engine.prepare_decision | Full observed-to-decision-to-consumer route; selectionMs includes acquisition; totalMs includes downstream route | No old record relabeling. New separate decision/acquisition/prepare spans and stage counters require implementation. No old timing becomes a supported cap. |
| t025-consumer-proposal-v1 / bridge.propose/check_handoff | Exact old keys format,verifierVersion,consumer,ingressDigest,snapshotDigest,payloadDigest,choice,runtimeRequest,executionAuthorization,packetDigest; independently reconstructs membership/source/tree | New proposal has a different format/complete bodies/pins. Legacy remains rejected at new ingress. Old T025 can accept any tied eligible choice; new policy-bound proposal requires first lexical minimum-cost choice. A new-packet k2 tie therefore refuses when k0 is policy choice, though an unchanged old T025 k2 packet was admissible. |
| bridge.final_tree/runtime_request | Private base-tree/index, predicted LF blobs, mode100644, whole expected tree; native_request adds predecessor dependencies for chosen serial order | Retain reconstruction and serial dependency closure, never T022's old builder. New native operation records remain exactly existing v0.1.0-alpha. |
| dispatch; native_check; prepare_consumer; core-api/mcp-service/mcp-stdio | Reacquire/reverify, fresh native evidence, then actual native prepare verifies again; complete schedule/tree/manifest binding and owned cleanup | Retain every check. New budget/termination/late-publication handling and source pin registry are not already present or proven. Actual existing T025 tests do not establish universal cancellation. |
| verifier.verify(hunk_budget=64) | Legacy candidate simulation cap excludes source-validation helper applications | New maxHunkApplications counts source validation, all candidate applications and revalidation cumulatively. Equal numbers are not equal whole-path budgets; tightened allowance may refuse earlier, never alter a completed semantic result. |
| research git helper subprocess timeout30s per command; native GitCommandBudget | Different enforcement boundaries; native child process limits and sampled scratch already exist | New shared outer/phase deadlines and aggregate accounting require T03/T05/T06 composition. No reset per command, implicit numeric SLA or universal hard termination claim. |

## Concrete developer vectors

Historical family/index correspondence is `eof-00-0` tail-one through `eof-09-0` wrong-goal in fixtures.FAMILIES. Each archived row chosen is core-api/controlled-en, variant0, with exact row number/digest in JSON; other language/consumer routes are not recounted as independent cases.

| ID | Input / mutation | Expected result and boundary | Evidence status |
|---|---|---|---|
| V01 | eof-00-0 tail-one, original program/payload | answered,k0; native tree equality in old recorded route | archived developer outcome |
| V02 | eof-02-0 tail-three, trailing context preserved | eligible k0,k2; choose k0 | archived; retained EOF recovery |
| V03 | eof-04-0 last-line, no retained trailing context | semantic-defer; k0 missing-context; new outer choice null, old wait | archived + explicit wrapper mapping |
| V04 | eof-06-0 bof-regression | k0 invalid/missing-context; answered,k2 | archived |
| V05 | eof-07-0 two-hunks | answered,k0, eligible k0,k2; two literal hunks remain | archived/source assertions |
| V06 | eof-08-0 four-ops-two-files | answered,k0; atomic staged multifile changes and dependencies | archived/source assertions |
| V07 | eof-05-0 context-conflict | semantic-defer, no goal-reaching offered plan | archived |
| V08 | eof-09-0 wrong-goal | semantic-defer, otherwise complete k0/k2 fail final-goal | archived |
| V09 | eof-02-0 optionOrder begins k2 but all same programs/goals | still min-cost lexical choice k0, preserve supplied order for binding | new wrapper expectation from verify source; old order changed would need reacquisition/rebinding |
| V10 | eof-08-0 set plans.k0=[a,a,b,c,d] | k0 valid=false, failure operation-precondition; no global malformed-IR refusal | existing named test/source |
| V11 | eof-08-0 set plans.k0=[] | k0 valid=false, incomplete/final-goal; evaluate remaining options | existing named test/source |
| V12 | source task operation uncertainPaths=[shared.txt] | refused/incomplete-observation; eligible=[],choice=null; unknown is not false | source rejection; new sanitized code mapping planned |
| V13 | flip final context prefix space→plus without updating old/new | refused/invalid-ir before selection | existing test, reconstruction mismatch |
| V14 | apply_changes with old block duplicated, both boundary flags false | technical ambiguous-anchor refusal, not a false goal judgment | existing runtime-ambiguity assertion |
| V15 | valid four-op program with hunk cap0 | refused/work-budget-exceeded, no partial answer | existing test + sanitized mapping |
| V16 | new/old proposal alter choice to inadmissible bof k0, then rehash | refusal before native/consumer; new code inadmissible-choice | existing T025 rehashed-option test, new wrapper planned |
| V17 | proposal verifierVersion=t021-boundary-v1 or new identity wrong | refused/unsupported-version or verifier-mismatch before dispatch | existing version-negative anchor |
| V18 | core-api packet delivered to mcp-service (valid rehash) | refused/consumer-mismatch; no native/consumer call | existing recipient-negative anchor |
| V19 | expectedFinalTree=40 zeroes, valid proposal rehash | refused/target-tree-mismatch (or invalid-envelope at zero-tree admission), never prepare | existing tree-negative anchor; new strict zero-tree admission |
| V20 | proposal.format=t022-consumer-proposal-v1 | refused/unsupported-version, no silent conversion | existing legacy-negative anchor |
| V21 | declaration a.after=40 ones; or text changes goal | refused/declaration-mismatch or text-mismatch; no native call | existing observed/text negatives |
| V22 | change immutable source/base pin after snapshot, rehash only packet | refused/source-drift when independent reacquisition/bindings differ; unavailable object is source-unavailable | source check_handoff; new wrapper planned, no fresh native run |
| V23 | omit verifierResult or any evidence reference/body/chunk | refused/invalid-envelope or evidence-incomplete; no hash-only success | new complete-body requirement; T06 test pending |
| V24 | valid request carries confidence=1 or executionAuthorization=true | refused/invalid-envelope, no backend/Git admission | new exact-key/no-authority requirement |
| V25 | duplicate JSON member, BOM, NaN, 17 nested containers, noncanonical literal text | refused at bounded parsing/interpretation; no silent normalization | stdlib parser + text-round-trip source; new inner-literal hardening pending |
| V26 | interpret stage starts100ns, parent end200ns; attempted child end300ns | effective child end<=200ns; at200 expired, no next stage | new budget-context test pending |
| V27 | cap128; verify consumes80 then revalidation requests fresh128 | second call has<=48 remaining; reset/enlargement refused | new aggregate-work test pending |
| V28 | decision expired/cancel set just before publish | no answered result, zero prepare calls; cancellation stays set | new request-local checkpoint test pending |
| V29 | terminationMode=hard | refused/invalid-budget at T05 request admission, before acquisition or consumer | new exact request-budget rule; no inherited SLA |
| V31 | budgets omits prepareBudgetMs | refused/invalid-budget at T05 request admission, no defaults/source/consumer | new exact missing-budget rule |
| V32 | two acquisitions share one GitCommandBudget with max_commands=1; then byte-cap/cancel subcases | second child is not started; cumulative command/output counters and original start persist; cancellation is irreversible | new explicit trusted seam; T03/T06 tests pending |
| V30 | child still alive or scratch removal unknown at response | usage termination/cleanup unknown; no successful cleanup/termination claim; retain admission until stopped | new T06 lifecycle test pending |

V19/23/25 deliberately describe multiple separate admission boundaries; JSON vectors split mutation/expected alternatives where validators can reject earlier. An earlier strict rejection is acceptable only if it is a specified earlier boundary and native/consumer calls remain zero; do not weaken tests to accept arbitrary errors. Exact domain reason mapping must be checked during T05/T06 before new software conformance is claimed. V09 is an identity/binding-sensitive new request, not an instruction to edit frozen evidence. Tied eligibility does not authorize changing a signed/bound choice in place.

## Acceptance and obtained versus planned evidence

Obtained here: exact source inspection; source hash readback; static comparison with ten already-recorded developer case outcomes; tests referenced by real class/method names; canonical-byte hash calculation; document link/ID/ownership/signature checks and applicable repository/Spec Kit validation as listed in the local receipt. **None is a pass of the new runtime contracts.** No reference oracle or study was rerun and no archived labels/evaluation set was used to select a new threshold/policy.

After T01 coordinator review, future T02–T04 tests implement their vectors on small owned developer fixtures; T05 checks the source-to-decision join; T06 checks actual consumers and supported time/resource envelopes; T07 checks legacy compatibility and adversarial boundaries. All logs, failures, skips and environmental limits are retained. Expected vectors are requirements-quality/conformance artifacts, not scientific evidence or human/Claude/Luna review. Canonical schema publication, public API/architecture adoption, representative accuracy/utility, human review, training/calibration, source rights, admission and activation remain pending. A passing document profile cannot close them.
