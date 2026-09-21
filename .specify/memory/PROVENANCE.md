# Constitution replica provenance

Source: root `CONSTITUTION.md`. Generator: `scripts/constitution_replica.py`.
The replica preserves exact bytes; this separate file is not part of its content.
No upstream constitution template or constitution-sync preset controls it.

Run `python3 scripts/constitution_replica.py check` to detect missing or divergent
bytes without repair. After an authorized canonical amendment, explicitly run
`python3 scripts/constitution_replica.py generate`. Generation does not approve
the source, amend governance, or refresh feature review fingerprints.

Integration baseline: commit `868a33341f304723f007646628d1d59c0e9e6ede`;
Constitution SHA-256 `ff7196976a1736a639947c2ab26e8da157fef23c89ba9881312f2a36459964eb`.
