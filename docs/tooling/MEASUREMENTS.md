<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Local capture measurements

`agent_braid.tooling_measurements` provides local measurement inputs for a
future registered capture. It does not start a host, provider, MCP client, grant,
or runtime operation. These observations are instrumentation primitives; they
are not an approved registration, a cost decision, or evidence that a capture
occurred.

## Observe elapsed time

Create one `WallClock` at the beginning of the bounded activity and call
`finish()` once it ends. Its `wall.value` uses `time.monotonic_ns()` from start
through finish, including pauses between phases. Named phase intervals are
annotations. They can overlap, and `phase_union_seconds` merges their overlap;
do not add phase durations to total wall time. An unclosed phase makes total
wall time unknown.

```python
from agent_braid.tooling_measurements import WallClock

wall = WallClock()
wall.start_phase("setup")
# Perform already-authorized local setup here.
wall.end_phase("setup")
wall.start_phase("capture")
# A future capture adapter would run only after its separate approval gates.
wall.end_phase("capture")
wall_observation = wall.finish()
```

Each observation records a UTC timestamp boundary and identifies the
monotonic-clock source. Phase timestamps are monotonic nanoseconds in the API;
the serialized phase records should be retained with the attempt receipt if
needed. A clock retains at most 1,024 phase intervals. Do not infer provider or
human time from these local intervals.

## Observe process RSS

Pass the exact process IDs that the caller has independently observed to
`ProcessRssSampler`. The explicit list is limited to 256 PIDs and the sampler to
100,000 samples. On Linux it reads `/proc/<pid>/statm` and process start
identity; on other POSIX systems it queries `ps` with those PIDs only. Repeated
samples return the highest aggregate RSS observed at those sample instants and
reject missing processes or PID identity changes. This is a maximum sampled
value, not a continuous peak. The reported scope is exactly the listed
processes. It does not claim a complete process tree, all host processes, or
memory between samples. It cannot by itself establish a 4 GiB aggregate
attempt-process peak limit. Permission errors, missing PIDs, unsupported
platforms, and identity drift produce `status="unknown"` and `value=None`.

```python
rss_sampler = ProcessRssSampler([observed_pid_a, observed_pid_b])
rss_observation = rss_sampler.sample().observation
```

The RSS source is bytes. A process absent from the list is not silently added;
the caller must establish which process IDs belong in the measurement boundary.

## Observe private output size

`measure_private_disk()` accepts at most 16 explicit roots, resolves them, and
sums logical file lengths without following links. The complete walk is bounded
to 100,000 files and 20,000 directories. Roots, nested directories, and files
must be owned by the current account; all must be inaccessible to group/other
users. Symlinks, special files, ownership/permission mismatch, traversal errors,
inventory limit exhaustion, or metadata changes during the scan make the whole
measurement unknown. The receipt digest includes each relative path and file
and directory identity/metadata, including `ctime_ns`; the collector scans
incrementally and rechecks files/directories after traversal. `ctime` semantics
vary by platform. POSIX mode bits are checked; platform ACLs are not inspected.
The final checks narrow the observation window but do not create an atomic
filesystem snapshot. This is logical file size, not allocated filesystem blocks
or total machine disk usage. It includes only files under the supplied roots.

```python
disk = measure_private_disk([private_result_root, private_receipt_root])
disk_observation = disk.observation
```

## Adapt observations to evaluation costs

`measured_costs()` adapts local observations to the existing `MeasuredCosts`
shape. It fills only `wall_seconds`, `rss_bytes`, and `disk_bytes` from these
collectors. EUR, total tokens, input/output tokens, and retry tokens remain
`None`; no values are estimated from text, model names, or reference rates.
Unknown local observations also remain `None`. The source hash binds the values
and provenance record; it does not authenticate the measuring process or
authorize a run. Sampled RSS is not complete peak-memory accounting, so an
external admission verifier still needs evidence that the registered cap's full
measurement boundary is covered.

```python
from agent_braid.tooling_measurements import measured_costs

costs = measured_costs(
    wall=wall_observation,
    rss=rss_observation,
    disk=disk_observation,
    source_ref="private-local-measurement-record",
)
```

The existing cap evaluator must treat unavailable required fields as a stop.
These observations alone therefore cannot establish compliance with monetary
or token caps. A future trusted capture adapter must define its complete process
scope, artifact roots, provider billing/token sources, timestamp boundaries, and
human-time collection before using the measurements for admission or accounting.
The collector does not retry failed observations; preserve unknown values and
the corresponding failure reason in the attempt record.
