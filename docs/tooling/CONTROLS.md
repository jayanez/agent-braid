# SPEC-044 deterministic controls

`scripts/run_tooling_controls.py` requires Python 3.12 or newer and runs the
bounded offline T003 matrix. It invokes
only the exact `unittest` methods named in its frozen manifest, one process per
case, without a shell, provider call, host session, user-data path, or caller-
supplied fixture/grant input. The methods themselves contain the domain oracle
assertions; the runner retains the method identity and expected oracle text for
each result. This is synthetic protocol-peer evidence, not actual-host or
clean-room acceptance.

Run it from a source checkout with an output directory that does not yet exist,
outside the checkout:

```sh
python3 scripts/run_tooling_controls.py \
  --output-root /private/tmp/spec044-t003-20261009
```

Each case has a bounded timeout (default 120 seconds, maximum 300). The runner
captures at most 256 KiB each of stdout and stderr per case, continues after
failed cases, and exits nonzero unless every mandatory case passes. It creates
the result directory exclusively with mode `0700`; manifest, receipt, case
records, and integrity index are `0600`. Before launching the first case it
freezes the commit, dirty status, candidate source files, complete test-source
tree, fixture inputs, protocol, runner hash, exact commands, and case oracle text.
Every intended case is first recorded as `not-started`; failed, timed-out,
interrupted, and not-started rows are retained. An interruption may leave the
matrix receipt `incomplete` with the interrupted case and all later cases still
`not-started`; interruption cannot be interpreted as a pass. Each child runs in
an owned process group. Timeouts, interrupts, lingering descendants, inherited
open pipes, or unknown group state trigger bounded TERM/KILL cleanup and cannot
pass the case. Cleanup targets only that owned group.

The receipt labels this `unittest-control-source` and `synthetic-protocol-peer`.
It does not claim that each case is a distinct independent experiment: test
methods are named assertion sources, and their relationship is stated in the
manifest. The runner verifies source hashes again after execution. The result
integrity index detects changed, missing, extra, or permission-weakened result
files:

The in-flight cancellation case exercises the application-level asyncio worker
checkpoint using Python's standard library. It asserts dispatch before caller
cancellation and completion before cancellation propagates. It does not exercise
the MCP SDK transport; actual client negotiation controls are separate.

```sh
python3 scripts/run_tooling_controls.py \
  --verify-root /private/tmp/spec044-t003-20261009
```

The matrix is limited to the exact local Python environment and synthetic
fixtures recorded in the manifest. It does not establish Codex or Claude host
discovery, provider identity, paid capture readiness, independent reproduction,
human scoring, utility, scientific validity, production safety, or founder
acceptance. No SPEC-044 task checkbox or evidence record is changed by running
the command.
