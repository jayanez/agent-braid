// SPDX-License-Identifier: AGPL-3.0-only
// Test harness for the braid-gate workflow script. It loads the shipped script
// text unchanged, supplies substituted agent()/phase()/log()/args globals and
// records every agent call. The substituted agent either replays a recorded
// result ("responses"/"patch" in the scenario) or acts as a reference agent that
// executes the exact command templates found in the prompt it was given, so the
// shipped hardened Git template is what runs. It is test code, never shipped.
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const scenario = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const repo = scenario.cwd || scenario.repo;
const calls = [];
const logs = [];
const phases = [];

// The workflow runtime rejects these; mirror it so the script cannot depend on them.
const RealDate = Date;
Date.now = () => { throw new Error('Date.now is unavailable in workflow scripts'); };
Math.random = () => { throw new Error('Math.random is unavailable in workflow scripts'); };
globalThis.Date = new Proxy(RealDate, {
  construct(target, argv) {
    if (argv.length === 0) throw new Error('argless new Date is unavailable in workflow scripts');
    return new target(...argv);
  },
});

// Shell commands run with the scenario's hostile inherited variables (GIT_* planted by a test) and
// an optional TMPDIR; the Python analyzer and the harness itself never see them.
function shellEnv(env) {
  const base = { ...process.env, ...(scenario.hostileEnv || {}) };
  if (scenario.tmpdir) base.TMPDIR = scenario.tmpdir;
  return { ...base, ...env };
}

function sh(command, cwd = repo, env = {}) {
  const done = spawnSync('sh', ['-c', command], { cwd, encoding: 'utf8', env: shellEnv(env), maxBuffer: 64 * 1024 * 1024 });
  return { rc: done.status, out: done.stdout, err: done.stderr };
}

function line(prompt, name) {
  const match = prompt.match(new RegExp('^' + name + ': (.*)$', 'm'));
  if (!match) throw new Error('prompt has no ' + name + ' line');
  return match[1];
}

function fill(template, values) {
  let text = template;
  for (const [token, value] of Object.entries(values)) text = text.split(token).join(value);
  return text;
}

function versionOf(text) {
  const match = text.match(/(\d+)\.(\d+)(?:\.(\d+))?/);
  return match ? match[0] : null;
}

function supportsMergeTree(version) {
  if (!version) return false;
  const [major, minor] = version.split('.').map(Number);
  return major > 2 || (major === 2 && minor >= 38);
}

function resolve(prompt, input) {
  const done = sh(fill(line(prompt, 'RESOLVE_TEMPLATE'), { '<INPUT>': input }));
  const commit = done.rc === 0 ? done.out.trim() : null;
  return { commit, state: done.rc === 0 ? 'resolved' : 'missing' };
}

function referenceValidate(prompt) {
  const inputs = JSON.parse(line(prompt, 'INPUTS_JSON'));
  const top = sh(line(prompt, 'TOPLEVEL'));
  const version = sh(line(prompt, 'VERSION'));
  const base = resolve(prompt, inputs.base).commit;
  const sources = inputs.sources.map((input) => {
    const commit = resolve(prompt, input).commit;
    let present = null;
    let descendantOfBase = null;
    if (commit) {
      present = sh(fill(line(prompt, 'PRESENT_TEMPLATE'), { '<SHA>': commit })).rc === 0;
      if (base) {
        const rc = sh(fill(line(prompt, 'ANCESTOR_TEMPLATE'), { '<BASE>': base, '<SHA>': commit })).rc;
        descendantOfBase = rc === 0 ? true : rc === 1 ? false : null;
      }
    }
    return { input, commit, present, descendantOfBase };
  });
  const replaced = sh(line(prompt, 'REPLACE_REFS'));
  return {
    replaceRefCount: replaced.rc === 0 ? replaced.out.split('\n').filter((item) => item !== '').length : null,
    workspacesOutcome: scenario.workspacesOutcome || 'ok',
    workspacesMessage: '',
    workspaces: scenario.workspaces || [],
    visibleToolNames: scenario.visibleToolNames || ['workspaces', 'analyze-work', 'analyze', 'prepare'],
    repoRoot: top.rc === 0 ? top.out.trim() : null,
    gitVersion: versionOf(version.out),
    base: { commit: base },
    sources,
  };
}

function referenceAnalyze(prompt) {
  const request = JSON.parse(line(prompt, 'ANALYSIS_REQUEST_JSON'));
  const code = 'import json,sys\nfrom agent_braid import git_adapter\n'
    + 'r,p=git_adapter.analyze_git_with_provenance(json.load(sys.stdin))\n'
    + 'print(json.dumps({"report":r,"provenance":p}))\n';
  const done = spawnSync(scenario.python, ['-c', code], { cwd: scenario.projectRoot, input: JSON.stringify(request), encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (done.status !== 0) return { outcome: 'failed', message: (done.stderr || '').slice(-400) };
  const { report, provenance } = JSON.parse(done.stdout);
  const sources = Object.fromEntries(provenance.operations.map((op) => [op.instanceId, op.resolvedSource]));
  return {
    outcome: 'ok',
    message: '',
    analysisId: report.analysisId,
    inputDigest: report.inputDigest,
    evidenceRefs: scenario.evidenceRef === 'plugin-format'
      ? [{ uri: 'agent-braid://evidence/fixture', sha256: 'd'.repeat(64), sizeBytes: 1234 }] : [],
    operations: report.operations.map((op) => ({ instanceId: op.instanceId, source: sources[op.instanceId], coverage: op.coverage.status })),
    interactions: report.interactions.map((i) => ({ left: i.left, right: i.right, classification: i.classification, sharedResources: i.sharedResources, coverage: i.evidence.coverage })),
    uncertainty: report.uncertainty,
    changes: provenance.operations.map((op) => ({ instanceId: op.instanceId, changes: op.changes })),
    toolNamesCalled: ['analyze-work'],
  };
}

function referenceBaseline(prompt) {
  const spec = JSON.parse(line(prompt, 'BASELINE_JSON'));
  const version = versionOf(sh(line(prompt, 'VERSION')).out);
  const supported = supportsMergeTree(version);
  const tmp = sh(line(prompt, 'SETUP_1')).out.trim();
  const common = sh(line(prompt, 'SETUP_2')).out.trim();
  const alt = common + '/objects';
  const place = (text) => fill(text, { '<SCRATCH>': tmp, '<ALT>': alt });
  sh(place(line(prompt, 'SETUP_3')));
  const env = {};
  const digest = (name) => sh(line(prompt, name)).out.trim() || null;
  const refsBefore = digest('STATE_REFS');
  const objectsBefore = digest('STATE_OBJECTS');
  const pairs = [];
  const trees = {};
  const mergeTree = (left, right) => {
    const command = place(fill(line(prompt, 'MERGE_TREE_TEMPLATE'), { '<BASE>': spec.base, '<LEFT>': left, '<RIGHT>': right }));
    const done = sh(command, repo, env);
    const parts = done.out.split('\0');
    if (done.rc === 0) return { result: 'clean', tree: parts[0], paths: [], message: '' };
    if (done.rc === 1) {
      const paths = [];
      for (const part of parts.slice(1)) { if (part === '') break; paths.push(part); }
      return { result: 'conflicted', tree: parts[0], paths, message: '' };
    }
    return { result: 'error', tree: null, paths: [], message: (done.err || '').slice(0, 300) };
  };
  for (const [i, j] of spec.pairs) {
    const outcome = supported ? mergeTree(spec.sources[i].commit, spec.sources[j].commit) : { result: 'unavailable', tree: null, paths: [], message: 'git merge-tree --write-tree is unavailable' };
    trees[i + ',' + j] = outcome.tree;
    pairs.push({ left: spec.sources[i].input, right: spec.sources[j].input, result: outcome.result, conflictedPaths: outcome.paths, message: outcome.message });
  }
  let chain = { outcome: 'skipped', finalTree: null, message: 'chain is derived only for 2 to 4 operations' };
  if (spec.chain) {
    chain = { outcome: 'unavailable', finalTree: null, message: 'not supported' };
    if (supported) {
      let tree = pairs[0].result === 'clean' ? trees['0,1'] : null;
      let outcome = tree ? 'completed' : (pairs[0].result === 'conflicted' ? 'conflicted' : 'error');
      for (let k = 2; tree && k < spec.sources.length; k += 1) {
        const step = mergeTree(tree, spec.sources[k].commit);
        if (step.result === 'clean') tree = step.tree; else { outcome = step.result; tree = null; }
      }
      chain = { outcome, finalTree: outcome === 'completed' ? tree : null, message: '' };
    }
  }
  const refsAfter = digest('STATE_REFS');
  const objectsAfter = digest('STATE_OBJECTS');
  const gitDir = sh(place(line(prompt, 'SCRATCH_GITDIR')), repo, env);
  const scratchGitDir = gitDir.rc === 0 ? gitDir.out.trim() : null;
  let cleanup = 'refused';
  if (/^\/tmp\/braid-gate\.[A-Za-z0-9]{8}$/.test(tmp)) {
    sh(fill(line(prompt, 'CLEANUP_REMOVE'), { '<SCRATCH>': tmp }));
    cleanup = sh('test ! -e ' + tmp).rc === 0 ? 'removed' : 'failed';
  }
  return {
    hardened: true, gitVersion: version, mergeTreeSupported: supported,
    refsDigestBefore: refsBefore, refsDigestAfter: refsAfter,
    objectsDigestBefore: objectsBefore, objectsDigestAfter: objectsAfter,
    scratchPath: tmp, scratchGitDir, cleanup, pairs, chain,
  };
}

function referenceFinalize(prompt) {
  const spec = JSON.parse(line(prompt, 'FINALIZE_JSON'));
  const mcp = scenario.mcp || {};
  const hex = (c) => 'sha256:' + c.repeat(64);
  const names = [];
  let replay = { called: false, outcome: 'not-called', message: '', evidenceDigest: null, advisoryPlanDigest: null, replayResult: null, verificationStatus: null };
  let prepare = { called: false, outcome: 'not-called', message: '', planDigest: null, order: [], expectedFinalTree: null };
  if (spec.replayRequest) {
    names.push('analyze');
    replay = { called: true, outcome: 'ok', message: '', evidenceDigest: hex('a'), advisoryPlanDigest: hex('b'), replayResult: 'equivalent-observed', verificationStatus: 'verified', ...(mcp.analyze || {}) };
    if (spec.prepare && replay.outcome === 'ok' && replay.replayResult === 'equivalent-observed') {
      names.push('prepare');
      prepare = { called: true, outcome: 'ok', message: '', planDigest: hex('c'), order: spec.replayRequest.order, expectedFinalTree: spec.replayRequest.expectedFinalTree, ...(mcp.prepare || {}) };
    }
  }
  const resolved = {
    base: { input: spec.baseInput, ...resolve(prompt, spec.baseInput) },
    sources: spec.sources.map((s) => ({ input: s.input, ...resolve(prompt, s.input) })),
  };
  return { resolved, replay, prepare, toolNamesCalled: names };
}

const reference = { validate: referenceValidate, analyze: referenceAnalyze, baseline: referenceBaseline, finalize: referenceFinalize };

async function agent(prompt, opts) {
  const label = opts && opts.label;
  calls.push({ label, phase: opts && opts.phase, prompt, optionKeys: Object.keys(opts || {}), schemaRequired: opts && opts.schema && opts.schema.required, schemaType: opts && opts.schema && opts.schema.type });
  for (const command of (scenario.before && scenario.before[label]) || []) sh(command);
  if (scenario.responses && Object.prototype.hasOwnProperty.call(scenario.responses, label)) {
    const response = scenario.responses[label];
    if (response && response.$throw) throw new Error(response.$throw);
    return response;
  }
  const result = reference[label](prompt);
  return scenario.patch && scenario.patch[label] ? { ...result, ...scenario.patch[label] } : result;
}

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const source = readFileSync(scenario.script, 'utf8');
if (!/^export const meta =/m.test(source)) throw new Error('script has no leading export const meta');
const body = source.replace(/^export const meta =/m, 'const meta =');
let envelope = null;
let error = null;
try {
  const run = new AsyncFunction('agent', 'phase', 'log', 'args', 'budget', body);
  envelope = await run(agent, (title) => { phases.push(title); }, (message) => { logs.push(String(message)); }, scenario.args, { total: null, spent: () => 0, remaining: () => Infinity });
} catch (caught) {
  error = String(caught && caught.stack || caught);
}
process.stdout.write(JSON.stringify({ envelope, error, calls, logs, phases }));
