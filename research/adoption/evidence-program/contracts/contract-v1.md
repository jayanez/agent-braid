# Synthetic adoption evidence v1

Version: `synthetic-adoption-evidence-v1`. Feature-local additive contract.
`program.validate` enforces this interface without third-party dependencies.
Objects reject unknown/missing fields. Inputs are at most 1 MiB when read from
files, depth 16, arrays 1,000 entries, strings 512 characters, keys 128 characters,
finite numbers of absolute value at most 2^53. IDs match `[a-z][a-z0-9-]{0,63}`;
bindings use lowercase SHA-256 hex. Duplicate JSON members and record IDs reject.
Integer magnitude is checked before conversion to floating point; huge JSON integers
produce a bounded refusal rather than an overflow traceback.

| Record | Required fields and rules |
| --- | --- |
| Register | version, population=`synthetic`, window, sources, organizations, workloads, episodes, contributions, reproductions, metrics |
| Window | id, ISO calendar start/end (start <= end), prospective=true |
| Source | id, kind=`synthetic`, permission=`generated/pending/withdrawn`, boundary |
| Organization | id, aliases, segments (overlapping labels), source, eligible boolean, reason; source resolves and ambiguous aliases reject |
| Workload | id, boundary; one to three distinct families |
| Episode | id, organization (canonical ID or resolving alias), workload, integration, source, window, condition=`baseline/report`, rubric, outcome=`completed/failed/abandoned/unknown/null`, errors=nonnegative integer/null, times, judgment=`useful/unhelpful/abstain/null`, binding |
| Times | setup, run, review, debug in nonnegative finite seconds or null; all fields present, total unavailable if any is null |
| Binding | candidate, input, protocol, environment, report: SHA-256 hashes |
| Contribution | id, source, rights=`generated/missing/withdrawn`, binding, outcome=`positive/negative/inconclusive`, commands, limits, author/conflicts/expected/observed (bounded text or null), workload, minimization=`minimized/not-minimized/unknown`, review=`pending/changes-requested/approved`, replay |
| Replay | null or initial bounded integer, left/right lists of one to six bounded integer literal writes; both lists have the same multiset, no callbacks, opcodes or external handles |
| Reproduction | id, source, rights, binding, outcome, commands, limits, reviewer, environment (text/null), review |
| Reviewer | identity, affiliation, conflicts (text/null), role=`founder/maintainer/external`, external boolean; declaring external cannot override a project role |
| Metric | id, unit, formula, evidenceClass, baseline, limit; exact supported pairs below, no arbitrary metric expressions |

| Metric | Unit | Formula | Evidence class |
| --- | --- | --- | --- |
| organizations | organization | unique-eligible-organizations | observed |
| workloads | workload | unique-eligible-workloads | observed |
| completion | episode | completed/known-eligible-episodes | observed |
| cost | seconds | sum(setup+run+review+debug) | observed |
| judgment | episode | useful/known-eligible-judgments | proxy |

Episode observation identity is the tuple of canonical organization, workload,
integration, source, window, condition, rubric and exact candidate/input/protocol/
environment/report bindings. Reusing this tuple under another row ID or alias is
rejected, including contradictory outcome copies. Distinct legitimate episodes
must have a distinct integration or exact source/input recording binding; a renamed
row alone cannot establish another observation. Outcomes and timing do not form
part of identity, so contradictory results cannot inflate the denominator.

Every output metric carries denominator, missing/excluded counts, eligible
population, window/input/manifest hashes, baseline hash, fixed interpretation
limit and validity/reasons. Counts do not sum segment labels. Completion and
judgment denominators exclude unknown/abstaining labels and disclose missingness.
Cost totals include complete admitted episodes only and disclose incomplete
ones. No missing observations are replaced by zero. Eligible workload means a
registered family with an admitted synthetic episode.

`freeze` outputs version, inputHash, windowHash, manifestHash and per-record hashes.
`report` requires that retained freeze packet and an exact candidate hash.
Changed frozen input/window/manifest/records or stale episode candidate
invalidates all metric values while preserving denominators and reasons. The
freeze packet's integrity is a caller responsibility; it does not authenticate
reviewer claims or grant permission. Unchanged denied sources are excluded.

Reports retain contribution replay outcomes/dispositions and reproduction
proposals; raw identity/conflict/command text is never emitted. Commands are
metadata only. All outputs are synthetic and non-authorizing, with realYield=0
and independentValidation=pending. Anonymous or incomplete external evidence
stays pending. No output mutates an existing release-validation contract.

## Migration and review impact

This is an additive local research interface, outside canonical governance,
market/adoption-track and release schemas. No existing input version migrates
implicitly. Unknown versions reject. A future real intake or changed semantics
needs a separately versioned contract, rights/privacy/migration review and
applicable architectural decision; no current permission is grandfathered.
Technical review concerns this software interface only. Human/scientific,
external reproduction and founder/publication acceptance remain separate.
