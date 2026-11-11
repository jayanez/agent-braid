# SPDX-License-Identifier: AGPL-3.0-only
"""Fake host executables for the SPEC-069 T013 driver self-test (``--fake-hosts``).

They imitate the command lines and JSON transcripts the driver relies on, replay a scenario file
and never contact a model. Evidence produced with them proves the pipeline, not any host.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CLAUDE_PREFIX = "mcp__plugin_agent-braid_agent-braid__"
OPENCODE_PREFIX = "agent-braid_"


def log(host, argv):
    path = os.environ.get("FAKE_LOG")
    if path:
        with open(path, "a") as handle:
            handle.write(json.dumps({"host": host, "argv": argv[:6]}) + "\n")


def scenario_for(prompt):
    if "FAKE_SCENARIO" not in os.environ:
        return {"steps": [], "text": "OK"}  # a plain prompt such as the sign-in check
    return json.loads(Path(os.environ["FAKE_SCENARIO"]).read_text()).get(prompt, {"steps": [], "text": "OK"})


def credential_text(*names):
    """Variant ``echo-credentials``: a leaky host that prints the credential file it was signed in with."""
    if os.environ.get("FAKE_VARIANT") != "echo-credentials":
        return ""
    for var, name in names:
        path = Path(os.environ.get(var, "")) / name
        if path.is_file():
            return path.read_text()
    return ""


def require_login(var, name, key_var):
    """Subscription self-test (FAKE_REQUIRE_LOGIN): without an API key the host needs the sign-in file, like the real ones."""
    if not os.environ.get("FAKE_REQUIRE_LOGIN") or os.environ.get(key_var) or (Path(os.environ.get(var, "/nonexistent")) / name).is_file():
        return
    print("Not logged in", file=sys.stderr)
    sys.exit(1)


def side_effects(text):
    """Variants that need the host process to misbehave."""
    variant = os.environ.get("FAKE_VARIANT", "default")
    if variant == "leak-secret":
        text += " " + os.environ.get("FAKE_PLANTED_SECRET", "") + " " + os.environ.get("ANTHROPIC_API_KEY", "")
    if variant == "straggler":
        subprocess.Popen(["/bin/sh", "-c", "sleep 300; echo " + os.environ["HOME"]], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return text + " " + credential_text(("CLAUDE_CONFIG_DIR", ".credentials.json"), ("CODEX_HOME", "auth.json"))


def emit(row):
    print(json.dumps(row), flush=True)


def copy_plugin(source, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, symlinks=True, dirs_exist_ok=True)
    return target


def claude(argv):
    require_login("CLAUDE_CONFIG_DIR", ".credentials.json", "ANTHROPIC_API_KEY")
    prompt = argv[argv.index("-p") + 1]
    denied = set(argv[argv.index("--disallowedTools") + 1:]) if "--disallowedTools" in argv else set()
    scen = scenario_for(prompt)
    emit({"type": "system", "subtype": "init", "model": "fake-claude-model", "tools": [], "mcp_servers": []})
    for number, step in enumerate(scen["steps"]):
        name = step["tool"]
        full = CLAUDE_PREFIX + name if name in ("analyze-work", "workspaces", "plugin-status") else name
        ident = "toolu_%d" % number
        emit({"type": "assistant", "message": {"model": "fake-claude-model", "content": [
            {"type": "tool_use", "id": ident, "name": full, "input": step["args"]}]}})
        if "result" in step:
            body, error = json.dumps(step["result"]), step["result"]["status"] in ("refused", "error")
        elif step.get("executed"):
            body, error = "bin\netc", False
        else:
            body, error = ("Permission to use %s has been denied" % name) if name in denied else "denied", True
        emit({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": ident, "content": body, "is_error": error}]}})
    emit({"type": "assistant", "message": {"model": "fake-claude-model", "content": [{"type": "text", "text": side_effects(scen["text"])}]}})
    emit({"type": "result", "subtype": "success", "total_cost_usd": 0.0, "num_turns": len(scen["steps"])})


def opencode(argv):
    if "--standalone" not in argv:
        print("Error: would use the background service", file=sys.stderr)
        sys.exit(9)
    prompt = argv[-1]
    model = argv[argv.index("-m") + 1] if "-m" in argv else ""
    if model.startswith("openrouter/"):  # the driver must configure the provider and inject only this key
        config = json.loads((Path(os.environ["XDG_CONFIG_HOME"]) / "opencode/opencode.json").read_text())
        if "openrouter" not in config.get("provider", {}) or not os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"):
            print("Error: openrouter is not configured", file=sys.stderr)
            sys.exit(8)
    scen = scenario_for(prompt)
    for number, step in enumerate(scen["steps"]):
        name = step["tool"]
        full = OPENCODE_PREFIX + name if name in ("analyze-work", "workspaces", "plugin-status") else name
        if "result" in step:
            state = {"status": "completed", "input": step["args"], "output": json.dumps(step["result"])}
        elif step.get("executed"):
            state = {"status": "completed", "input": step["args"], "output": "bin\netc"}
        else:
            state = {"status": "error", "input": step["args"], "error": "denied by permission"}
        emit({"type": "tool_use", "part": {"type": "tool", "tool": full, "state": state, "id": "prt_%d" % number}})
    emit({"type": "text", "part": {"type": "text", "text": side_effects(scen["text"])}})
    emit({"type": "step_finish", "part": {"type": "step-finish", "cost": 0, "tokens": {"input": 1, "output": 1}}})


def codex(argv):
    require_login("CODEX_HOME", "auth.json", "CODEX_API_KEY")
    prompt = argv[-1]
    scen = scenario_for(prompt)
    emit({"type": "thread.started", "thread_id": "fake"})
    for number, step in enumerate(scen["steps"]):
        name = step["tool"]
        if "result" in step:
            item = {"id": "item_%d" % number, "type": "mcp_tool_call", "server": "agent-braid", "tool": name,
                    "arguments": step["args"], "status": "completed",
                    "result": {"content": [{"type": "text", "text": json.dumps(step["result"])}]}}
        else:
            item = {"id": "item_%d" % number, "type": "command_execution", "command": step["args"]["command"],
                    "status": "completed" if step.get("executed") else "declined",
                    "aggregated_output": "bin\netc" if step.get("executed") else "", "exit_code": 0 if step.get("executed") else None}
        emit({"type": "item.completed", "item": item})
    emit({"type": "item.completed", "item": {"id": "m", "type": "agent_message", "text": side_effects(scen["text"])}})
    emit({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}})


def main(host):
    argv = sys.argv[1:]
    log(host, argv)
    if argv[:1] == ["--version"]:
        print("%s 0.0.0-fake" % host)
        return
    if host == "codex" and argv[:2] == ["plugin", "marketplace"]:
        (Path(os.environ["CODEX_HOME"]) / "market.txt").write_text(argv[-1])
        print("Added marketplace `agent-braid`")
        return
    if host == "codex" and argv[:2] == ["plugin", "add"]:
        market = Path((Path(os.environ["CODEX_HOME"]) / "market.txt").read_text())
        root = Path(os.environ["CODEX_HOME"]) / "plugins/cache/agent-braid/agent-braid/0.0.0-fake"
        copy_plugin(market / "plugins/agent-braid", root)
        print("Installed plugin root: %s" % root)
        return
    if host == "opencode" and argv[:2] == ["plugin", "add"]:
        source = argv[2].split("git+file://")[1].split("#")[0]
        copy_plugin(Path(source) / "plugins/agent-braid", Path(os.environ["XDG_CACHE_HOME"]) / "opencode/npm/git-cand-fake/1/node_modules/agent-braid")
        print("Plugin installed")
        return
    {"claude": claude, "codex": codex, "opencode": opencode}[host](argv)
