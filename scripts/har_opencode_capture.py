#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Observe which OpenCode configuration shapes the installed OpenCode reads (SPEC-080 T007/T008).

This script is NOT an authorization and qualifies nothing. It runs the installed ``opencode``
binary only with local, non-model subcommands, each time in a fresh temporary home: ``HOME``
and every ``XDG_*_HOME`` point below a ``tempfile.mkdtemp()`` root, the child environment is
built from scratch, and the child runs under ``sandbox-exec`` with a profile that denies every
read and write below the real home (except the binary's own directory and, for ``profile``,
the source checkout) and every outbound IP connection except the temporary service port on
localhost. OpenCode's own network attempts are recorded from its temporary log; they fail.

Two commands, both one-command, read-only with respect to any real host configuration::

    python3 scripts/har_opencode_capture.py schema    # T007: which shapes this version reads
    python3 scripts/har_opencode_capture.py profile   # T008: does it list the profile's server

``schema`` writes ``specs/080-harness-skill-every-host/evidence/t007-opencode-schema.json`` and
redacted fixtures under ``tests/fixtures/opencode/``. ``profile`` installs the Agent Braid
OpenCode profile (``agent_braid.tooling_install``) into a temporary home, runs its doctor, asks
the same OpenCode version to list MCP servers in that home, removes the profile and lists
again; it writes ``--out`` (default: standard output). When acceptance cannot be observed the
result is the stable code ``opencode-acceptance-unobserved``.

Exit status: 0 observed, 1 a check stopped it, 2 an observation failed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FORMAT = "braid-har-opencode-capture/v0.1"
DEFAULT_BINARY = Path.home() / ".opencode" / "bin" / "opencode"
SANDBOX = Path("/usr/bin/sandbox-exec")
EVIDENCE = ROOT / "specs/080-harness-skill-every-host/evidence/t007-opencode-schema.json"
FIXTURES = ROOT / "tests/fixtures/opencode"
COMMAND_TIMEOUT_SECONDS = 60
LIST_ATTEMPTS = 3
LIST_PAUSE_SECONDS = 2.0
UNOBSERVED = "opencode-acceptance-unobserved"
NO_SERVERS = "No MCP servers configured"
LOCAL = {"type": "local", "command": ["/usr/bin/true"]}
LISTING = [["debug", "config"], ["reload"], ["mcp", "list"], ["plugin", "list"]]


class Stop(Exception):
    """A precondition failed; the message is the stop reason."""


@dataclass(frozen=True)
class Case:
    """One fresh temporary home: a configuration (or none) and what to look for."""

    name: str
    family: str
    shape: str
    config: dict[str, Any] | None
    servers: tuple[str, ...] = ()
    key_paths: tuple[tuple[str, ...], ...] = ()
    note: str = ""
    oracle: tuple[str, ...] = ()  # an ``opencode`` command that writes the configuration itself


CASES: tuple[Case, ...] = (
    Case("baseline-empty", "control", "none", None, note="no configuration file"),
    Case("mcp-add-oracle", "mcp", "written-by-opencode", None, servers=("probe",),
         oracle=("mcp", "add", "--global", "probe", "--", "/usr/bin/true"),
         note="the shape this version itself writes with `opencode mcp add --global`"),
    Case("mcp-singular", "mcp", "singular", {"mcp": {"probe": LOCAL}}, servers=("probe",),
         key_paths=(("mcp", "servers", "probe"), ("mcp", "probe"))),
    Case("mcp-plural", "mcp", "plural", {"mcp": {"servers": {"probe": LOCAL}}}, servers=("probe",),
         key_paths=(("mcp", "servers", "probe"), ("mcp", "probe"))),
    Case("mcp-mixed", "mcp", "mixed", {"mcp": {"servers": {"probe": LOCAL}, "probe2": LOCAL}},
         servers=("probe", "probe2"),
         key_paths=(("mcp", "servers", "probe"), ("mcp", "servers", "probe2"), ("mcp", "probe2")),
         note="a plural container beside a singular sibling, as an install into a plural file would leave it"),
    Case("mcp-plural-list", "mcp", "plural-list", {"mcp": {"servers": [{"name": "probe", **LOCAL}]}},
         servers=("probe",), key_paths=(("mcp", "servers"),),
         note="list-shaped `mcp.servers`, the 2026-11-22 vendor-docs reading"),
    Case("mcp-plural-list-beside-singular", "mcp", "plural-list+singular",
         {"mcp": {"servers": [{"name": "probe", **LOCAL}], "probe2": LOCAL}}, servers=("probe", "probe2"),
         key_paths=(("mcp", "servers", "probe2"),),
         note="a singular entry inserted beside a list-shaped `mcp.servers`"),
    Case("mcp-mixed-same-name", "mcp", "mixed-same-name",
         {"mcp": {"servers": {"probe": LOCAL}, "probe": {"type": "local", "command": ["/usr/bin/false"]}}},
         servers=("probe",), key_paths=(("mcp", "servers", "probe"),),
         note="one name in both shapes: which command does OpenCode keep (true: plural, false: singular)"),
    Case("mcp-singular-codemode-false", "mcp", "singular+codemode-false",
         {"mcp": {"probe": {**LOCAL, "codemode": False}}}, servers=("probe",),
         key_paths=(("mcp", "servers", "probe", "codemode"),),
         note="the profile's `codemode: false` member (SPEC-068 D7)"),
    Case("mcp-singular-codemode-true", "mcp", "singular+codemode-true",
         {"mcp": {"probe": {**LOCAL, "codemode": True}}}, servers=("probe",),
         key_paths=(("mcp", "servers", "probe", "codemode"),),
         note="control for the `codemode` member: is it visible in `debug config` at all"),
    Case("mcp-unknown-key-control", "control", "unknown-key", {"mcpServers": {"probe": LOCAL}},
         servers=("probe",), key_paths=(("mcpServers",),),
         note="negative control: a key OpenCode does not define must not be listed"),
    Case("plugin-singular", "plugins", "singular", {"plugin": ["./probe-plugin-absent.js"]},
         key_paths=(("plugin",), ("plugins",))),
    Case("plugins-plural", "plugins", "plural", {"plugins": ["./probe-plugin-absent.js"]},
         key_paths=(("plugin",), ("plugins",))),
    Case("permission-singular", "permissions", "singular", {"permission": {"edit": "deny"}},
         key_paths=(("permission",), ("permissions",))),
    Case("permissions-plural", "permissions", "plural",
         {"permissions": [{"action": "edit", "resource": "*", "effect": "deny"}]},
         key_paths=(("permission",), ("permissions",))),
    Case("skills-plural-list", "skills", "plural-list", {"skills": ["./probe-skills"]},
         key_paths=(("skills",), ("skill",))),
    Case("skills-plural-object", "skills", "plural-object", {"skills": {"paths": ["./probe-skills"]}},
         key_paths=(("skills",), ("skill",))),
)


# --- isolation ---------------------------------------------------------------------------

def binary_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def _sb(path: Path | str) -> str:
    text = str(path)
    if '"' in text or "\\" in text:
        raise Stop(f"path not representable in a sandbox profile: {text!r}")
    return text


def sandbox_profile(real_home: Path, binary: Path, root: Path, port: int,
                    readable: Sequence[Path] = ()) -> str:
    """Deny the real home (reads and writes) and outbound IP; allow only what the run needs."""
    rules = ["(version 1)", "(allow default)",
             "(deny network-outbound (remote ip))",
             f'(allow network-outbound (remote ip "localhost:{port}"))',
             f'(deny file-read* (subpath "{_sb(real_home)}"))',
             f'(deny file-write* (subpath "{_sb(real_home)}"))',
             f'(allow file-read* (subpath "{_sb(binary.parent)}"))',
             f'(allow file-read* file-write* (subpath "{_sb(root)}"))']
    rules += [f'(allow file-read* (subpath "{_sb(path)}"))' for path in readable]
    return "".join(rules)


@dataclass
class Home:
    """A fresh temporary home with its own OpenCode service port."""

    root: Path
    port: int
    real_home: Path
    binary: Path
    readable: tuple[Path, ...] = ()
    commands: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(cls, real_home: Path, binary: Path, readable: Sequence[Path] = ()) -> "Home":
        root = Path(tempfile.mkdtemp(prefix="braid-opencode-")).resolve()
        if root.is_relative_to(real_home):
            shutil.rmtree(root)
            raise Stop("the temporary directory is inside the real home; set TMPDIR elsewhere")
        for name in ("home", "config", "data", "cache", "state", "cwd"):
            (root / name).mkdir()
        home = cls(root, free_port(), real_home, binary, tuple(readable))
        home.config_dir.mkdir(parents=True)
        (home.config_dir / "service.json").write_text(json.dumps({"port": home.port}) + "\n")
        return home

    @property
    def config_dir(self) -> Path:
        return self.root / "config" / "opencode"

    @property
    def config_file(self) -> Path:
        return self.config_dir / "opencode.json"

    def env(self) -> dict[str, str]:
        return {"PATH": "/usr/bin:/bin", "HOME": str(self.root / "home"),
                "XDG_CONFIG_HOME": str(self.root / "config"), "XDG_DATA_HOME": str(self.root / "data"),
                "XDG_CACHE_HOME": str(self.root / "cache"), "XDG_STATE_HOME": str(self.root / "state"),
                "TMPDIR": str(self.root) + "/", "LANG": "C.UTF-8", "NO_COLOR": "1"}

    def run(self, args: Sequence[str]) -> dict[str, Any]:
        profile = sandbox_profile(self.real_home, self.binary, self.root, self.port, self.readable)
        argv = [str(SANDBOX), "-p", profile, str(self.binary), *args]
        started = time.monotonic()
        try:
            done = subprocess.run(argv, cwd=self.root / "cwd", env=self.env(), capture_output=True,
                                  timeout=COMMAND_TIMEOUT_SECONDS, check=False)
            status: int | str = done.returncode
            stdout, stderr = done.stdout, done.stderr
        except subprocess.TimeoutExpired as exc:
            status, stdout, stderr = "timeout", exc.stdout or b"", exc.stderr or b""
        record = {"argv": ["opencode", *args], "exit": status,
                  "seconds": round(time.monotonic() - started, 2),
                  "stdout": stdout.decode("utf-8", "replace"), "stderr": stderr.decode("utf-8", "replace")}
        self.commands.append(record)
        return record

    def stop(self) -> dict[str, Any]:
        record = self.run(["service", "stop"])
        for _ in range(20):
            if not port_open(self.port):
                break
            time.sleep(0.25)
        record["portClosedAfterStop"] = not port_open(self.port)
        return record

    def network_attempts(self) -> list[str]:
        attempts: set[str] = set()
        for log in (self.root / "data" / "opencode" / "log").glob("*.log"):
            for match in re.finditer(r"\b(GET|POST|PUT|PATCH|DELETE) (https?://[^\s)\"]+)", log.read_text("utf-8", "replace")):
                attempts.add(f"{match.group(1)} {match.group(2)}")
        return sorted(attempts)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


# --- redaction and observation ------------------------------------------------------------

def redactor(home: Home, extra: dict[str, str] | None = None):
    pairs = [(str(home.root), "<TMP>"), (str(home.root).replace("/private/", "/", 1), "<TMP>"),
             (str(home.binary), "<OPENCODE>"), (str(home.real_home), "<HOME>")]
    pairs += sorted((extra or {}).items(), key=lambda item: -len(item[0]))
    user = getpass.getuser()

    def redact(text: str) -> str:
        for needle, replacement in sorted(pairs, key=lambda item: -len(item[0])):
            if needle:
                text = text.replace(needle, replacement)
        text = re.sub(rf"(127\.0\.0\.1|localhost):{home.port}\b", r"\1:<PORT>", text)
        text = re.sub(rf'("port":\s*){home.port}\b', r"\1<PORT>", text)
        if len(user) >= 3:
            text = re.sub(rf"\b{re.escape(user)}\b", "<USER>", text)
        return text
    return redact


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def listed(output: str, server: str) -> bool:
    """A server is listed when a status line of ``opencode mcp list`` names it."""
    return any(re.search(rf"(^|\s){re.escape(server)}(\s|$)", line) for line in output.splitlines())


def config_document(stdout: str, config_file_text: str) -> tuple[str, dict[str, Any] | None]:
    """The parsed ``info`` OpenCode reports for the configuration file, or why it is absent."""
    try:
        sources = json.loads(stdout)
    except json.JSONDecodeError:
        return "unparsed", None
    for source in sources if isinstance(sources, list) else []:
        if isinstance(source, dict) and source.get("type") == "document" and source.get("path") == config_file_text:
            info = source.get("info")
            return ("parsed", info) if isinstance(info, dict) else ("no-info", None)
    return "absent", None


def has_path(value: Any, path: Sequence[str]) -> bool:
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return False
        value = value[key]
    return True


def observe_listing(home: Home) -> dict[str, Any]:
    """``debug config``, ``reload``, then ``mcp list`` (bounded retries) and ``plugin list``."""
    out: dict[str, Any] = {}
    out["debugConfig"] = home.run(LISTING[0])
    out["reload"] = home.run(LISTING[1])
    attempts = []
    for attempt in range(LIST_ATTEMPTS):
        record = home.run(LISTING[2])
        attempts.append(record)
        if NO_SERVERS not in record["stdout"] or attempt + 1 == LIST_ATTEMPTS:
            break
        time.sleep(LIST_PAUSE_SECONDS)
    out["mcpList"] = attempts
    out["pluginList"] = home.run(LISTING[3])
    return out


def redact_record(record: dict[str, Any], redact) -> dict[str, Any]:
    stdout, stderr = redact(record["stdout"]), redact(record["stderr"])
    result = {"argv": record["argv"], "exit": record["exit"], "stdout": stdout, "stdoutSha256": sha(stdout),
              "stderr": stderr, "stderrSha256": sha(stderr)}
    if "portClosedAfterStop" in record:
        result["portClosedAfterStop"] = record["portClosedAfterStop"]
    return result


def run_case(case: Case, real_home: Path, binary: Path, keep: bool) -> dict[str, Any]:
    home = Home.create(real_home, binary)
    redact = redactor(home)
    try:
        if case.config is not None:
            home.config_file.write_text(json.dumps(case.config, indent=2) + "\n")
        oracle = home.run(list(case.oracle)) if case.oracle else None
        observed = observe_listing(home)
        stopped = home.stop()
        written = home.config_file.read_text() if home.config_file.exists() else None
        status, info = config_document(observed["debugConfig"]["stdout"], str(home.config_file))
        mcp_text = observed["mcpList"][-1]["stdout"]
        result: dict[str, Any] = {
            "case": case.name, "family": case.family, "shape": case.shape, "note": case.note,
            "input": case.config, "inputSha256": sha(json.dumps(case.config, sort_keys=True)) if case.config else None,
            "oracle": redact_record(oracle, redact) if oracle else None,
            "configAfter": json.loads(written) if written else None,
            "configChangedByOpenCode": (written is not None and case.config is not None
                                        and json.loads(written) != case.config),
            "debugConfig": {"document": status, "info": json.loads(redact(json.dumps(info))) if info is not None else None,
                            "keyPaths": {".".join(path): has_path(info, path) for path in case.key_paths}},
            "serversListed": {server: listed(mcp_text, server) for server in case.servers},
            "listedServers": [] if NO_SERVERS in mcp_text else sorted(
                {match.group(1) for match in re.finditer(r"^\S+\s+(\S+)\s", mcp_text, re.MULTILINE)}),
            "commands": [redact_record(record, redact) for record in
                         [observed["debugConfig"], observed["reload"], *observed["mcpList"], observed["pluginList"]]],
            "serviceStop": redact_record(stopped, redact),
            "networkAttempts": [redact(item) for item in home.network_attempts()],
        }
        return result
    finally:
        if keep:
            print(f"kept {case.name}: {home.root}", file=sys.stderr)
        else:
            home.cleanup()


def winner(case: dict[str, Any]) -> str:
    """Which entry OpenCode keeps when one name is in both shapes (by its distinct command)."""
    info = case["debugConfig"]["info"] or {}
    command = info.get("mcp", {}).get("servers", {}).get("probe", {}).get("command")
    return {("/usr/bin/true",): "plural", ("/usr/bin/false",): "singular"}.get(tuple(command or ()), "not observed")


def verdicts(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize which shape of each family this version reads, only from what was observed."""
    by = {case["case"]: case for case in cases}

    def mcp_read(name: str) -> bool:
        return all(by[name]["serversListed"].values())

    def kept(name: str, key: str) -> bool:
        return by[name]["debugConfig"]["keyPaths"].get(key, False)

    control = by["mcp-unknown-key-control"]
    return {
        "mcp": {"singular (mcp.<name>)": mcp_read("mcp-singular"),
                "plural (mcp.servers.<name>)": mcp_read("mcp-plural"),
                "mixed (mcp.servers.<a> beside mcp.<b>)": by["mcp-mixed"]["serversListed"],
                "plural-list (mcp.servers as an array)": mcp_read("mcp-plural-list"),
                "singular beside a plural list": by["mcp-plural-list-beside-singular"]["serversListed"],
                "same name in both shapes keeps": winner(by["mcp-mixed-same-name"]),
                "codemode visible in debug config": {
                    "false": kept("mcp-singular-codemode-false", "mcp.servers.probe.codemode"),
                    "true": kept("mcp-singular-codemode-true", "mcp.servers.probe.codemode")},
                "writtenByOpenCode": by["mcp-add-oracle"]["configAfter"],
                "normalizedTo": "mcp.servers" if kept("mcp-singular", "mcp.servers.probe") else "not observed"},
        "plugins": {"singular (plugin)": {"plugin": kept("plugin-singular", "plugin"),
                                          "plugins": kept("plugin-singular", "plugins")},
                    "plural (plugins)": {"plugin": kept("plugins-plural", "plugin"),
                                         "plugins": kept("plugins-plural", "plugins")}},
        "permissions": {"singular (permission)": {"permission": kept("permission-singular", "permission"),
                                                  "permissions": kept("permission-singular", "permissions")},
                        "plural (permissions)": {"permission": kept("permissions-plural", "permission"),
                                                 "permissions": kept("permissions-plural", "permissions")}},
        "skills": {"plural-list (skills: [...])": kept("skills-plural-list", "skills"),
                   "plural-object (skills: {paths})": kept("skills-plural-object", "skills")},
        "negativeControl": {"mcpServers listed": control["serversListed"].get("probe"),
                            "passes": control["serversListed"].get("probe") is False},
        "readMeans": ("mcp: the server appears in `opencode mcp list` after `reload`; other families: the key "
                      "survives in the `info` that `opencode debug config` reports for the file (OpenCode "
                      "normalizes what it reads); a dropped key is recorded as not read"),
    }


def preflight(binary: Path) -> dict[str, Any]:
    if sys.platform != "darwin" or not SANDBOX.is_file():
        raise Stop("sandbox-unavailable: this capture needs macOS sandbox-exec")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise Stop(f"opencode binary not found or not executable: {binary}")
    return {"sha256": binary_sha256(binary)}


def schema(args: argparse.Namespace) -> int:
    real_home = Path.home().resolve()
    binary = args.binary.expanduser().resolve()
    identity = preflight(binary)
    version_home = Home.create(real_home, binary)
    try:
        version = version_home.run(["--version"])
        help_root = version_home.run(["--help"])
        help_mcp = version_home.run(["mcp", "--help"])
        help_debug = version_home.run(["debug", "--help"])
        redact = redactor(version_home)
        preliminaries = [redact_record(record, redact) for record in (version, help_root, help_mcp, help_debug)]
        network = [redact(item) for item in version_home.network_attempts()]
    finally:
        version_home.cleanup()
    if version["exit"] != 0:
        raise Stop("opencode --version failed")
    cases = [run_case(case, real_home, binary, args.keep) for case in CASES]
    failures = [case["case"] for case in cases
                if case["serviceStop"]["exit"] != 0 or not case["serviceStop"].get("portClosedAfterStop")]
    record = {
        "format": FORMAT, "task": "SPEC-080 T007", "requirement": "REQ-007 / SC-007",
        "executionAuthorization": False, "qualifies": False,
        "binary": {"path": "<HOME>/.opencode/bin/opencode" if binary == DEFAULT_BINARY.resolve() else "<OPENCODE>",
                   "version": version["stdout"].strip(), "sha256": identity["sha256"]},
        "isolation": {"home": "fresh tempfile.mkdtemp() root per case; HOME and XDG_{CONFIG,DATA,CACHE,STATE}_HOME below it",
                      "environment": "built from scratch: PATH=/usr/bin:/bin, LANG, NO_COLOR, the six variables above",
                      "sandbox": "sandbox-exec: deny read and write below the real home except the binary directory; "
                                 "deny outbound IP except localhost:<service port>",
                      "service": "per-case `service.json` port; `opencode service stop` after each case, port checked closed",
                      "cwd": "<TMP>/cwd (empty)"},
        "commandsPerCase": [["opencode", *argv] for argv in LISTING] + [["opencode", "service", "stop"]],
        "preliminaries": preliminaries,
        "preliminaryNetworkAttempts": network,
        "cases": cases,
        "verdicts": verdicts(cases),
        "docs": {"source": "Context7 /anomalyco/opencode/v2.1.2 (queried 2026-11-24)",
                 "pages": ["services/www/src/docs/content/migrate-v1.mdx",
                           "services/www/src/docs/content/mcp-servers.mdx",
                           "services/www/src/docs/content/skills.mdx",
                           "services/www/src/docs/content/build/plugins/migrate-v1.mdx"],
                 "claims": ["V2 groups servers under mcp.servers; V2 does not place server names directly under mcp",
                            "the V1 config format remains supported; V1 and V2 fields may coexist at the top level",
                            "V2 replaces the plugin array with plugins and the permission map with an ordered permissions array"],
                 "status": "hypotheses; the observation above decides"},
        "limits": ["one OpenCode build on one macOS machine; another build may read other shapes",
                   "read means listed or normalized by local subcommands; no session, model call or MCP tool call",
                   "the probe servers run /usr/bin/true, so `mcp list` reports them as failed: listed, not connected",
                   "plugins are local relative paths that do not exist; no plugin code was loaded",
                   "OpenCode watches parent directories of its working directory and /Library/Application Support; "
                   "a system-managed configuration there, if any, could influence the result",
                   "OpenCode's own network attempts are recorded from its temporary log and were refused by the sandbox"],
        "stopFailures": failures,
    }
    text = json.dumps(record, indent=1, ensure_ascii=False) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    args.fixtures.mkdir(parents=True, exist_ok=True)
    for case in cases:
        fixture = {"format": FORMAT, "opencodeVersion": record["binary"]["version"],
                   "binarySha256": identity["sha256"], "case": case["case"], "family": case["family"],
                   "shape": case["shape"], "input": case["input"], "configAfter": case["configAfter"],
                   "debugConfigInfo": case["debugConfig"]["info"], "serversListed": case["serversListed"],
                   "mcpList": next((c["stdout"] for c in reversed(case["commands"])
                                    if c["argv"][1:3] == ["mcp", "list"]), None)}
        (args.fixtures / f"{case['case']}.json").write_text(json.dumps(fixture, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(record["verdicts"], indent=1))
    return 2 if failures else 0


# --- T008: the Agent Braid profile in a temporary home -----------------------------------

def profile(args: argparse.Namespace) -> int:
    from agent_braid.tooling_install import Selection, apply, doctor, plan

    real_home = Path.home().resolve()
    binary = args.binary.expanduser().resolve()
    identity = preflight(binary)
    source = ROOT.resolve()
    home = Home.create(real_home, binary, readable=(source,))
    redact = redactor(home, {str(source): "<SOURCE>", sys.executable: "<PYTHON>",
                             str(Path(sys.executable).resolve()): "<PYTHON>"})
    previous = os.environ.get("XDG_CONFIG_HOME")
    result: dict[str, Any] = {"format": FORMAT, "task": "SPEC-080 T008", "executionAuthorization": False,
                              "binary": {"sha256": identity["sha256"]}}
    try:
        os.environ["XDG_CONFIG_HOME"] = str(home.root / "config")
        results = home.root / "results"
        results.mkdir()
        selection = Selection(host="opencode", scope="user", source_root=source, result_root=results,
                              home=home.root / "home")
        config, skills, receipt = selection.paths()
        for path in (config, skills, receipt):
            if not path.resolve().is_relative_to(home.root):
                raise Stop(f"profile path escapes the temporary home: {path}")
        version = home.run(["--version"])
        result["binary"]["version"] = version["stdout"].strip()
        seed = next((case for case in CASES if case.name == args.seed), None)
        seeded = json.dumps(seed.config, indent=2) + "\n" if seed else None
        if seeded is not None:
            config.write_text(seeded)
        result["seed"] = {"case": seed.name, "config": seed.config} if seed else None
        transaction = plan(selection, operation="install", source_checkout=True)
        applied = apply(transaction, preview_digest=transaction.preview()["previewDigest"])
        written = config.read_text()
        result["install"] = {"status": applied["status"], "config": json.loads(redact(written))}
        checks = doctor(selection, source_checkout=True)["checks"]
        result["doctor"] = json.loads(redact(json.dumps(
            {key: checks[key] for key in ("configuration", "ownedEntry", "ownedSkills", "nativePlugin")})))
        installed = observe_listing(home)
        status, info = config_document(installed["debugConfig"]["stdout"], str(config))
        listing = installed["mcpList"][-1]
        accepted = listed(listing["stdout"], selection.name)
        result["acceptance"] = {
            "observed": status == "parsed" or listing["exit"] == 0,
            "listed": accepted,
            "seedServersListed": {server: listed(listing["stdout"], server) for server in (seed.servers if seed else ())},
            "code": None if accepted else UNOBSERVED,
            "debugConfigDocument": status,
            "debugConfigInfo": json.loads(redact(json.dumps(info))) if info is not None else None,
            "mcpList": [redact_record(record, redact) for record in installed["mcpList"]],
            "statusLine": next((redact(line) for line in listing["stdout"].splitlines()
                                if listed(line, selection.name)), None)}
        stopped = home.stop()
        transaction = plan(selection, operation="uninstall", source_checkout=True)
        removed = apply(transaction, preview_digest=transaction.preview()["previewDigest"])
        after = config.read_text() if config.exists() else None
        relisted = observe_listing(home)
        result["remove"] = {"status": removed["status"], "configAfter": after,
                            "restoredSeedBytes": (after == seeded) if seeded is not None else None,
                            "listedAfterRemove": listed(relisted["mcpList"][-1]["stdout"], selection.name),
                            "mcpList": redact_record(relisted["mcpList"][-1], redact)}
        stopped_again = home.stop()
        result["serviceStops"] = [redact_record(stopped, redact), redact_record(stopped_again, redact)]
        result["networkAttempts"] = [redact(item) for item in home.network_attempts()]
        result["commands"] = [record["argv"] for record in home.commands]
    finally:
        if previous is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = previous
        if args.keep:
            print(f"kept: {home.root}", file=sys.stderr)
        else:
            home.cleanup()
    text = json.dumps(result, indent=1, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        sys.stdout.write(text)
    ok = all(stop["exit"] == 0 and stop.get("portClosedAfterStop") for stop in result["serviceStops"])
    return 0 if ok else 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--keep", action="store_true", help="keep temporary homes for inspection")
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("schema", help="T007: observe which configuration shapes this version reads")
    one.add_argument("--out", type=Path, default=EVIDENCE)
    one.add_argument("--fixtures", type=Path, default=FIXTURES)
    two = commands.add_parser("profile", help="T008: install the profile and ask OpenCode to list it")
    two.add_argument("--out", type=Path, default=None)
    two.add_argument("--seed", choices=[case.name for case in CASES if case.config and case.family == "mcp"],
                     help="start from this T007 case's configuration instead of no file")
    args = parser.parse_args(argv)
    try:
        return schema(args) if args.command == "schema" else profile(args)
    except Stop as exc:
        print(f"stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
