# Native plugin candidate quickstart

The source is not a published release. Build into a new directory outside this checkout using scripts/build_native_plugin.py; install the generated marketplace with the selected host's native manager. The package includes the runtime and six skills. Open setup, choose repositories, inspect the preview, apply its digest and reconnect MCP.

Run `.venv-speckit/bin/python -m unittest discover -s tests -p 'test_plugin*.py' -v`. No provider prompts or public release are part of this command.
