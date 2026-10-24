// G0 ad-hoc workflow template. COPY OUTSIDE THE REPOSITORY, hash the copy
// (see RUNBOOK.md) and pass one manifest run entry as `args`:
//   { runId, taskSet: [ { ordinal, title, instructions }, ... 3 or 4 ], testCommand }
// The workflow only creates worktree agents that must commit and returns their
// branch names and head commits. It performs no merge, no push and no test run
// on a merged tree. Agents are asked for their own pre-commit test run only.
export const meta = {
  name: 'g0-designed-overlap-run',
  description: 'G0 run: 3-4 worktree agents on a designed task set, each must commit; no merge',
  phases: [{ title: 'Agents', detail: 'one worktree agent per task, commit required' }],
}

const RESULT_SCHEMA = {
  type: 'object',
  properties: {
    ordinal: { type: 'number' },
    branch: { type: 'string' },
    headCommit: { type: 'string' },
    committed: { type: 'boolean' },
    summary: { type: 'string' },
  },
  required: ['ordinal', 'branch', 'headCommit', 'committed'],
}

const tasks = args && args.taskSet
if (!Array.isArray(tasks) || tasks.length < 3 || tasks.length > 4) {
  throw new Error('taskSet must hold 3 or 4 tasks')
}
if (typeof args.testCommand !== 'string' || !args.testCommand) {
  throw new Error('testCommand is required')
}

phase('Agents')
const results = await parallel(tasks.map(task => () => agent(
  [
    'You work in your own isolated git worktree of the repository.',
    'Task (' + task.title + '):',
    task.instructions,
    '',
    'Rules:',
    '- Implement only this task. Do not coordinate with other agents.',
    '- Run this test command before finishing and fix what you break: ' + args.testCommand,
    '- You MUST commit your work to your worktree branch with git commit. An uncommitted result does not count.',
    '- Do not merge, rebase onto another branch, push, or create pull requests.',
    '- Report your branch name (git rev-parse --abbrev-ref HEAD) and head commit (git rev-parse HEAD).',
  ].join('\n'),
  { label: 'task-' + task.ordinal, phase: 'Agents', isolation: 'worktree', schema: RESULT_SCHEMA },
)))

const done = results.filter(Boolean)
if (done.length !== tasks.length) {
  log('agents returned: ' + done.length + ' of ' + tasks.length + '; the founder records the run as workflow-aborted if any is missing')
}
return {
  runId: args.runId,
  agents: done.sort((a, b) => a.ordinal - b.ordinal),
}
