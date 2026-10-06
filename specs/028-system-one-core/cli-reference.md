# Offline reference CLI

`agent-braid system-one capabilities` reports the supported local reference
backend without allocating a runtime or loading provider/model packages.
`agent-braid system-one decide INPUT` accepts a regular local UTF-8 JSON file of
at most 1 MiB. Symlinks, FIFOs, directories and missing/oversized files are refused.
There is no stdin, socket or remote source mode. File acquisition occurs before
the core materialized-byte ingress deadline; the deadline does not bound file
I/O or process startup.

The request selects its policy explicitly. `strict-uncalibrated-v1` abstains;
`synthetic-diagnostic-v1` can return hand-authored synthetic fixture choices.
Neither outcome grants execution authority or establishes empirical confidence.
No flag overrides request policy or budgets. JSON is written only to stdout;
exit codes are 0 for answered/capabilities, 1 for abstain/defer and 2 for refused
or local input admission failure. Admission errors are fixed sanitized JSON.

Legacy analyzer, verifier, Git runtime and exchange commands retain their
existing dispatch and default behavior. Decision imports occur only after the
explicit `system-one` namespace is selected.
