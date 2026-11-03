# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-068 T003: the dependency-free OpenCode entry module (contract: opencode-surface.md)."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from agent_braid.tooling_assets import load_skill_bundle
from scripts.build_native_plugin import ROOT, SKILL_SUBSTITUTIONS, package_skill

ENTRY = ROOT / 'integrations/agent-braid/plugin/opencode/index.js'
SKILL_IDS = ['analyze', 'plan', 'evidence', 'execute', 'recover', 'setup']
NODE = shutil.which('node')

# Registrations are limited to three transforms. These APIs would add a network, write, process or
# event channel, or a failure path that disables the whole plugin on the host (T002 rows 01 and 10).
FORBIDDEN = {
    'network': r'\bfetch\b|\bhttps?\b|\bnet\b|\btls\b|\bdns\b|\bdgram\b|\bWebSocket\b|XMLHttpRequest',
    'process': r'child_process|\bspawn\w*|(?<![.\w])exec(?:Sync|File|FileSync)?\s*\(|\bfork\s*\(|\bProcess\.|\bprocess\.',
    'write': (r'\bwriteFile\w*|\bwriteSync\b|\bappendFile\w*|\bmkdir\w*|\brm(?:Sync|dir)?\s*\(|\bunlink\w*|\brename\w*'
              r'|\bcopyFile\w*|\bcreateWriteStream\b|\bfs\.write\w*|\bsymlink\w*|\bchmod\w*|\btruncate\w*|\bopenSync\b'),
    'logging': r'\bconsole\b',
    'events': r'\.on\s*\(|\.once\s*\(|addEventListener|subscribe|\bctx\.event\b|\bsetInterval\b|\bsetTimeout\b',
    'throwing': r'\bthrow\b',
    'dynamic code': r'\beval\s*\(|new\s+Function\b|\brequire\s*\(|\bimport\s*\(',
}
ALLOWED_IMPORTS = {'node:fs': {'readFileSync'}, 'node:path': {'dirname', 'join'}, 'node:url': {'fileURLToPath'}}


def code_of(source):
    """Source without whole-line comments."""
    return re.sub(r'(?m)^\s*//.*$', '', source)


def forbidden_apis(source):
    code = code_of(source)
    return sorted(label for label, pattern in FORBIDDEN.items() if re.search(pattern, code))


def imports_of(source):
    found = {}
    for names, module in re.findall(r'(?m)^import\s*\{([^}]*)\}\s*from\s*"([^"]+)"', code_of(source)):
        found[module] = {x.strip() for x in names.split(',') if x.strip()}
    return found


class EntrySourceTests(unittest.TestCase):
    def setUp(self):
        self.source = ENTRY.read_text()

    def test_source_uses_none_of_the_forbidden_apis(self):
        self.assertEqual(forbidden_apis(self.source), [])

    def test_negative_controls_each_forbidden_api_is_detected(self):
        samples = {
            'network': 'await fetch("https://example.invalid")',
            'process': 'import { spawn } from "node:child_process"',
            'write': 'writeFileSync("x", "y")',
            'logging': 'console.warn("collision")',
            'events': 'ctx.event.subscribe(() => {})',
            'throwing': 'throw new Error("no")',
            'dynamic code': 'await import("x")',
        }
        self.assertEqual(set(samples), set(FORBIDDEN))
        for label, sample in samples.items():
            with self.subTest(label):
                self.assertIn(label, forbidden_apis(self.source + '\n' + sample + '\n'))
        for extra in ('fs.writeFile(a, b)', 'appendFileSync(a, b)', 'mkdirSync(a)', 'rmSync(a)', 'unlinkSync(a)',
                      'execSync("ls")', 'process.on("exit", f)', 'server.on("x", f)'):
            with self.subTest(extra):
                self.assertTrue(forbidden_apis(self.source + '\n' + extra + '\n'))

    def test_a_commented_mention_is_not_a_use_but_real_code_still_is(self):
        self.assertEqual(forbidden_apis('// never throw, never fetch\nexport default {}\n'), [])
        self.assertEqual(forbidden_apis('export default { x: () => { throw 1 } }\n'), ['throwing'])

    def test_execute_property_is_not_mistaken_for_exec(self):
        self.assertIn('execute:', self.source)

    def test_only_read_only_node_builtins_are_imported(self):
        self.assertEqual(imports_of(self.source), ALLOWED_IMPORTS)
        self.assertEqual(len(re.findall(r'(?m)^import\b', code_of(self.source))), len(ALLOWED_IMPORTS))

    def test_registered_values_follow_the_contract(self):
        for fragment in ('type: "local"', 'codemode: false', 'protocol: "legacy"', '"plugin", "serve", "--plugin-root", root',
                         '`${root}/launch`', 'import.meta.url', 'name: "agent-braid-setup"', 'name: "agent-braid-reconnect"'):
            self.assertIn(fragment, self.source)
        self.assertIn('const SKILLS = ' + json.dumps(SKILL_IDS), self.source)
        self.assertEqual(len(re.findall(r'\.transform\(', self.source)), 3)
        self.assertNotIn('permission', code_of(self.source))

    def test_skill_text_is_not_duplicated_in_the_module(self):
        for skill in load_skill_bundle(source_checkout=True).skills:
            body = package_skill(skill.content).split('\n---\n', 1)[1]
            first_line = next(x for x in body.splitlines() if len(x) > 30)
            self.assertNotIn(first_line, self.source)

    def test_no_symlink_in_the_plugin_source_directory(self):
        self.assertFalse([x for x in ENTRY.parent.parent.rglob('*') if x.is_symlink()])


HARNESS = r'''
import { pathToFileURL } from "node:url"
const [entryPath, scenarioJson] = process.argv.slice(2)
const scenario = JSON.parse(scenarioJson)
const module = await import(pathToFileURL(entryPath).href)
const plugin = module.default
const out = { shape: { id: plugin.id, setup: typeof plugin.setup, keys: Object.keys(module) } }
const clone = (value) => JSON.parse(JSON.stringify(value))

const state = { servers: new Map(Object.entries(scenario.servers ?? {})), skills: new Map(), commands: [], prompts: [] }
for (const [id, value] of Object.entries(scenario.skills ?? {})) state.skills.set(id, value)
const callbacks = { mcp: [], skill: [], command: [] }
const broken = scenario.broken ?? {}

function mcpEditor() {
  return {
    list: () => [...state.servers],
    get: (name) => state.servers.get(name),
    set: (name, value) => { state.servers.set(name, clone(value)) },
    update: () => {}, remove: () => {},
  }
}
function skillEditor() {
  return {
    list: () => [...state.skills.values()],
    get: (id) => state.skills.get(id) ?? null,
    add: (skill) => { state.skills.set(skill.id, clone(skill)) },
    update: () => {}, remove: () => {},
  }
}
function commandEditor(log) { return { add: (command) => { log.push(command) } } }

const ctx = {
  mcp: { transform: async (cb) => { callbacks.mcp.push(cb) } },
  skill: { transform: async (cb) => { callbacks.skill.push(cb) } },
  command: { transform: async (cb) => { callbacks.command.push(cb) } },
  session: { prompt: async (input) => { if (broken.prompt) return Promise.reject(new Error("x")); state.prompts.push(input); return {} } },
}
if (broken.transforms === "sync") for (const key of Object.keys(ctx)) if (key !== "session") ctx[key].transform = () => { throw new Error("x") }
if (broken.transforms === "async") for (const key of Object.keys(ctx)) if (key !== "session") ctx[key].transform = async () => { throw new Error("x") }
if (broken.transforms === "missing") { delete ctx.mcp; delete ctx.skill; delete ctx.command }

let threw = false
try { await plugin.setup(broken.ctx === "null" ? null : broken.ctx === "empty" ? {} : ctx) } catch { threw = true }
out.setupThrew = threw

const snapshots = []
let lastCommands = []
for (const kind of scenario.order ?? []) {
  const log = []
  for (const cb of callbacks[kind]) {
    let editor = kind === "mcp" ? mcpEditor() : kind === "skill" ? skillEditor() : commandEditor(log)
    if (broken.editor) editor = new Proxy({}, { get: () => () => { throw new Error("x") } })
    try { cb(editor); if (kind === "command" && scenario.sameEditorTwice) cb(editor) } catch { out.callbackThrew = true }
  }
  if (kind === "command") lastCommands = log
  snapshots.push(clone({ servers: [...state.servers], skills: [...state.skills] }))
}
out.snapshots = snapshots
out.final = clone({ servers: [...state.servers], skills: [...state.skills] })
out.commandNames = lastCommands.map((x) => x.name)
out.commandShapes = lastCommands.map((x) => ({ name: x.name, description: typeof x.description, execute: typeof x.execute }))
if (scenario.execute) {
  const command = lastCommands.find((x) => x.name === scenario.execute)
  let rejected = false
  try { await command.execute({ sessionID: "ses_1", prompt: { text: "user text" }, delivery: "queue" }) } catch { rejected = true }
  out.executeRejected = rejected
  out.prompts = clone(state.prompts)
}
console.log(JSON.stringify(out))
'''


def make_package(root):
    """Packaged layout: opencode/index.js beside skills/<id>/SKILL.md produced by the real SPEC-054 substitution."""
    (root / 'opencode').mkdir(parents=True)
    shutil.copyfile(ENTRY, root / 'opencode/index.js')
    for skill in load_skill_bundle(source_checkout=True).skills:
        target = root / 'skills' / SKILL_SUBSTITUTIONS[skill.name] / 'SKILL.md'
        target.parent.mkdir(parents=True)
        target.write_text(package_skill(skill.content))
    shutil.copytree(ROOT / 'integrations/agent-braid/plugin/setup', root / 'skills/setup')
    return root


@unittest.skipUnless(NODE, 'node is not on PATH')
class EntryRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        cls.base = Path(cls.scratch.name)
        cls.package = make_package(cls.base.resolve() / 'pkg')
        cls.harness = cls.base / 'harness.mjs'
        cls.harness.write_text(HARNESS)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def run_scenario(self, scenario, package=None):
        entry = (package or self.package) / 'opencode/index.js'
        done = subprocess.run([NODE, str(self.harness), str(entry), json.dumps(scenario)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, '')
        return json.loads(done.stdout)

    def expected_server(self):
        root = str(self.package)
        return {'type': 'local', 'command': [root + '/launch', 'plugin', 'serve', '--plugin-root', root],
                'codemode': False, 'protocol': 'legacy'}

    def test_syntax_is_valid(self):
        done = subprocess.run([NODE, '--check', str(ENTRY)], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_default_export_is_an_object_with_id_and_setup_only(self):
        value = self.run_scenario({'order': []})
        self.assertEqual(value['shape'], {'id': 'agent-braid', 'setup': 'function', 'keys': ['default']})
        self.assertFalse(value['setupThrew'])

    def test_registers_server_six_skills_and_two_commands(self):
        value = self.run_scenario({'order': ['mcp', 'skill', 'command']})
        servers = dict(value['final']['servers'])
        self.assertEqual(servers, {'agent-braid': self.expected_server()})
        skills = dict(value['final']['skills'])
        self.assertEqual(sorted(skills), sorted(SKILL_IDS))
        for identifier, skill in skills.items():
            path = self.package / 'skills' / identifier / 'SKILL.md'
            self.assertEqual(skill['path'], str(path))
            self.assertEqual(skill['content'], path.read_text())
            self.assertEqual(skill['id'], identifier)
            self.assertTrue(skill['description'])
        self.assertEqual(value['commandNames'], ['agent-braid-setup', 'agent-braid-reconnect'])
        self.assertEqual([x['execute'] for x in value['commandShapes']], ['function', 'function'])

    def test_repeated_transforms_in_any_order_are_idempotent(self):
        reference = self.run_scenario({'order': ['mcp', 'skill', 'command']})['final']
        for order in (['mcp'] * 3 + ['skill'] * 3, ['skill', 'mcp', 'command'] * 3, ['command', 'skill', 'skill', 'mcp', 'mcp']):
            with self.subTest(order=order):
                value = self.run_scenario({'order': order})
                self.assertEqual(value['final'], reference)
                if 'command' in order:
                    self.assertEqual(value['commandNames'], ['agent-braid-setup', 'agent-braid-reconnect'])

    def test_same_command_editor_receiving_the_transform_twice_gets_two_commands_once(self):
        value = self.run_scenario({'order': ['command'], 'sameEditorTwice': True})
        self.assertEqual(value['commandNames'], ['agent-braid-setup', 'agent-braid-reconnect'])

    def test_foreign_agent_braid_server_is_left_untouched(self):
        foreign = {'type': 'local', 'command': ['/bin/sh', '-c', 'echo user'], 'timeout': {}}
        for variant in (foreign, {**foreign, 'command': self.expected_server()['command'], 'codemode': True},
                        {**self.expected_server(), 'protocol': 'latest'}, {'type': 'remote', 'url': 'https://example.invalid'}):
            with self.subTest(variant=variant):
                value = self.run_scenario({'order': ['mcp', 'mcp'], 'servers': {'agent-braid': variant}})
                self.assertEqual(dict(value['final']['servers']), {'agent-braid': variant})

    def test_host_normalized_own_entry_is_accepted_and_reset_to_the_exact_value(self):
        normalized = {**self.expected_server(), 'timeout': {}, 'disabled': True}
        value = self.run_scenario({'order': ['mcp'], 'servers': {'agent-braid': normalized}})
        self.assertEqual(dict(value['final']['servers'])['agent-braid'], self.expected_server())

    def test_other_servers_are_not_touched(self):
        other = {'type': 'remote', 'url': 'https://example.invalid'}
        value = self.run_scenario({'order': ['mcp'], 'servers': {'docs': other}})
        self.assertEqual(dict(value['final']['servers']), {'docs': other, 'agent-braid': self.expected_server()})

    def test_existing_skill_ids_are_never_replaced_updated_or_removed(self):
        existing = {'id': 'analyze', 'name': 'analyze', 'description': 'user', 'path': '/u/SKILL.md', 'content': 'user text'}
        value = self.run_scenario({'order': ['skill', 'skill'], 'skills': {'analyze': existing, 'plan': {**existing, 'id': 'plan'}}})
        skills = dict(value['final']['skills'])
        self.assertEqual(skills['analyze'], existing)
        self.assertEqual(skills['plan']['content'], 'user text')
        self.assertEqual(sorted(skills), sorted(SKILL_IDS))

    def test_missing_skill_files_skip_only_those_skills(self):
        package = make_package(self.base / 'partial')
        (package / 'skills/plan/SKILL.md').unlink()
        value = self.run_scenario({'order': ['mcp', 'skill', 'command']}, package)
        self.assertEqual(sorted(dict(value['final']['skills'])), sorted(set(SKILL_IDS) - {'plan'}))
        self.assertEqual(value['commandNames'], ['agent-braid-setup', 'agent-braid-reconnect'])
        self.assertFalse(value['setupThrew'] or value.get('callbackThrew'))

    def test_a_broken_host_context_never_makes_the_entry_throw(self):
        for broken in ({'transforms': 'sync'}, {'transforms': 'async'}, {'transforms': 'missing'}, {'ctx': 'null'},
                       {'ctx': 'empty'}, {'editor': True}):
            with self.subTest(broken=broken):
                value = self.run_scenario({'order': ['mcp', 'skill', 'command'], 'broken': broken})
                self.assertFalse(value['setupThrew'])
                self.assertFalse(value.get('callbackThrew'))

    def test_setup_command_prompts_the_session_with_the_packaged_setup_skill(self):
        value = self.run_scenario({'order': ['command'], 'execute': 'agent-braid-setup'})
        self.assertFalse(value['executeRejected'])
        self.assertEqual(len(value['prompts']), 1)
        prompt = value['prompts'][0]
        self.assertEqual((prompt['sessionID'], prompt['delivery']), ('ses_1', 'queue'))
        self.assertIn((self.package / 'skills/setup/SKILL.md').read_text(), prompt['text'])

    def test_reconnect_command_shows_steps_and_requests_no_reload(self):
        value = self.run_scenario({'order': ['command'], 'execute': 'agent-braid-reconnect'})
        text = value['prompts'][0]['text']
        self.assertIn('opencode reload', text)
        self.assertIn('performs no reload', text)
        self.assertIn('Do not run any command', text)

    def test_commands_never_reject_when_the_session_refuses_the_prompt(self):
        for name in ('agent-braid-setup', 'agent-braid-reconnect'):
            with self.subTest(name):
                value = self.run_scenario({'order': ['command'], 'execute': name, 'broken': {'prompt': True}})
                self.assertFalse(value['executeRejected'])


if __name__ == '__main__':
    unittest.main()
