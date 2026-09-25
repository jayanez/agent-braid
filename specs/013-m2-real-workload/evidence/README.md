# T003 real-workload experiment evidence

The founder approved only the exact inputs in [the T003 decision](../t003-founder-decision.json).
The implementation candidate was cd14c5068e4a7b71ea2b8d037e7f20288c5f6a45.
The [reproduction record](reproduction.json) binds the code, corpus, dependency
bytes, image, raw reports and validation log.

The first [clean-room run](cleanroom-missing-history.json) was **inconclusive**:
both Git trees matched, but all four test lanes failed a Spec Kit check because
the fresh clone lacked the merged historical PR #104 head. The public PR head
f35c16ae790fd451a8824a069e0f1144d596fcfe was fetched into a local
keep ref. This added test history without changing the approved base, source
commits, image, dependencies or command. Spec Kit then passed in that clone.

The [repeated clean-room run](cleanroom-complete.json) completed: two Git
preparations produced the same tracked tree
fbc0d05bb42d2d94bb237d7f0b846457d0bd5940; four isolated test lanes
each exited successfully after 204 tests. No new worktree writes were observed
after the tests. The registered [selection controls](cleanroom-preflight.json)
rejected a moved base, substituted source, duplicate PR and undeclared
tracked-path write. The profile [pr validation log](pr-validation.log) is
development validation, separate from the experiment.

Candidate Git preparation took 201.5 and 207.4 ms; serial preparation took
175.0 and 184.9 ms. This finite sample shows **no speedup**. The candidate
still formed one admissible preparation wave versus two serial steps. Test
time was about 75 seconds per lane in both conditions.

The earlier [development harness check](development-harness-inconclusive.json)
is retained: it falsely flagged the expected difference between the combined
tree and the base commit as a test write. The corrected check compares each
container's state before and after its test command.

All claims remain bounded to static tracked paths, the pinned command and
this corpus. This is neither independent human validation nor M2 closure.
Execution authorization and promotion remain false.
