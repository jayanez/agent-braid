# Code isolation readiness

The read-only inventory checks executable presence through local PATH lookup.
It does not launch Docker, sandbox-exec, bwrap or podman, inspect a daemon, install
anything or execute project code. Presence does not establish actual enforcement.
Every inventory result therefore reports code-check NO-GO until credential,
filesystem, network, descendant and memory controls are separately demonstrated.

Future harmless probes require exact reviewed command, isolated owned files,
network target, resource limits and operator execution authorization. This task
contains no probe runner. Installed Docker or OS wrappers are not an automatic
sandbox approval. Fallback is read-only analysis and private fixed-patch replay.
