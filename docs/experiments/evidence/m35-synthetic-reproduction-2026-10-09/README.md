# SPEC-019 synthetic reproduction — 2026-10-09

This reproduction ran against candidate commit `06d7e85cff985e429f159132f6b383fa195c09cb` on macOS arm64 with Python 3.13.11. The runner completed successfully and confirmed the candidate inputs and working tree did not change during the run.

The receipt records 18 synthetic events, six examined sessions, six examined pairs, one admitted synthetic pair, and **zero real pairs**. It makes no source-rights, human-review, training, holdout-performance, or production claim. `executionAuthorization` is false.

Command:

```text
python -m unittest -v tests.test_m35_source_capture tests.test_m35_source_window tests.test_m35_lab_export tests.test_m35_seal_validate
```

Receipt SHA-256: `369f2db9e690bdc14f85676cf20d6601819efcad722fc2d63828bf6e3ede616d`.
