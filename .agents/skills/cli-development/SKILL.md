---
name: building-python-clis
description: Build or extend Agent Braid's Python command-line interface with stdlib argparse. Use for subcommands, arguments, help, exit codes, and CLI tests; consult Click or Typer references only when that stack is explicitly chosen.
---

# Python CLI Development

## Project route

`agent_braid/cli.py` implements the `agent-braid` entry point with `argparse`.
Preserve its `main(argv: list[str] | None = None) -> int` interface and the
project's zero-runtime-dependency policy. Read the current CLI and its tests
before changing argument names, output, or exit status. Preserve the distinction
between a verified result, a bounded rejection, and an input or runtime error.

Build subcommands with the existing parser pattern:

```python
parser = argparse.ArgumentParser(description=__doc__)
subparsers = parser.add_subparsers(dest="command", required=True)
analyze_parser = subparsers.add_parser("analyze", help="analyze AIM records")
analyze_parser.add_argument("input", type=Path)
analyze_parser.add_argument("--format", choices=("json", "text"), default="json")
args = parser.parse_args(argv)
```

Return a documented integer from `main` and use `raise SystemExit(main())` in
the module entry point. Give `argparse` clear help text and use its type and
choice validation. Keep machine-readable output stable when adding options.
Check the actual command with `python3 -m agent_braid --help` and test success,
rejection, and invalid input through the public module or console entry point.
The existing CLI tests in `tests/test_analysis.py` and `tests/test_git_adapter.py`
show the project's `unittest` and subprocess conventions.

## Optional framework references

Use [CLICK_PATTERNS.md](CLICK_PATTERNS.md) or [TYPER_GUIDE.md](TYPER_GUIDE.md)
only for a separately approved Click/Typer CLI or an explicit framework
comparison. Their installation steps, decorators, `CliRunner`, and shell
completion conventions do not apply to the current `agent-braid` command.

## CLI checklist

- Keep the entry point in `pyproject.toml` aligned with the callable.
- Check `--help` for each added subcommand and preserve existing invocations.
- Route failures to the established output and exit-status contract.
- Test both useful results and rejected inputs via `unittest discover`.

This skill is adapted from the [Guide to Developing High-Quality Python
Libraries](https://mcginniscommawill.com/guides/python-library-development/)
by Will McGinnis. Its original Click/Typer examples remain in the optional
references.
