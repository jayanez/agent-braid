# Offline harness repair after the consumed v8 attempt

Status: engineering repair in PR #520; no new execution package or approval.
T007 and T008 remain open. This supplement does not replace historical assurance
or accept the failed environment qualification.

The [scoped evidence index](evidence/offline-harness-repair-2026-10-15.json)
binds the retained input, current sources, failing regressions, 39 focused checks
and Luna review. Whole-PR validation retains its separate candidate/run identity.

## Retained outcome

Request `0e652b26e9ca719560b017f83f6e4b303383a86686a980fc0d378181865f6654`
was admitted and executed once. It failed after approximately 69.342 seconds.
No experimental daemon-crash signal was recorded. The claim remains consumed,
the approval pin was removed and the receipts report VM stop and cleanup. The
absence of an owned helper process and those receipts do not independently prove
VM absence. Raw console, receipts and sparse scratch are retained privately.
No model, inference or container creation was part of that attempt.

## Causes and bounded corrections

| Failure | Offline reproduction | Correction |
| --- | --- | --- |
| Native preflight/completion flags missed saved records | Foundation-only replay shows Swift treats CRLF as one `Character`; LF character splitting and substring checks miss those boundaries | Share Foundation line splitting across strict preflight and marker detection; ignore incomplete final records and return after terminal stop |
| `/info` capture stops at 4096 bytes | An owned synthetic Unix peer sends a 4096-byte block followed by a delayed remainder; the isolated socat client with the previous options exits zero after the first block | Remove the inner subsecond `-T0.8` inactivity path; preserve stdin EOF handling, the outer one-second deadline and 1 MiB byte cap |
| Incomplete diagnostic disappears into a generic wrapper error | Replaying the retained console raises a base64 error because `parse_events` has already decoded the 357-byte log | Validate the decoded bytes directly and encode once for the JSON field; correct previously double-encoded synthetic fixtures |

The socket comparison reproduces the observed cutoff outside the VM; it does not
establish which internal guest/Linux event caused the historical truncation.
The corrected runtime has not been executed in a guest. Pure replay of the
retained input still refuses preflight because its saved `/info` JSON is incomplete.
The recovered diagnostic remains `incomplete`, without execution authority.

## Regression boundary

The tests cover LF and CRLF, read boundaries between CR/LF, marker lookalikes,
large valid versus truncated HTTP, delayed multi-block Unix responses, stalled
responses, exactly-one-layer log decoding, log cap/count disagreement, missing
payload and existing admission negatives. Pure Swift tests compile the current
runtime parser source rather than a separately maintained implementation; explicit
linkage checks keep its embedded copies identical. Optional compiler, socat and
private retained-input checks report skips when their prerequisites are absent.

See [offline development commands](../../scripts/forecast_engine_probe/README.md).
These checks are software evidence only. They do not establish daemon-crash
qualification, worker conformance, complete deployment costs, utility, promotion,
independent VM-absence proof or renewed execution authority. The active stop rule
remains in force; another execution is neither prepared nor implied.
