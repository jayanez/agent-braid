// SPDX-License-Identifier: AGPL-3.0-only
// Agent Braid OpenCode entry (SPEC-068, contract: opencode-surface.md).
// Registers exactly three things and nothing else: the plugin MCP server, the six
// packaged skills and two commands. No network, no writes, no child processes, no
// hooks, no event subscriptions. Every registration is idempotent and skipped on
// any problem, because a failure inside a transform disables the whole plugin and
// the host offers no write-free warning channel (T002 rows 01, 10).
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const SERVER = "agent-braid"
const SKILLS = ["analyze", "plan", "evidence", "execute", "recover", "setup"]
const root = dirname(dirname(fileURLToPath(import.meta.url)))

const RECONNECT_TEXT = [
  "Agent Braid reconnect. Do not run any command or tool. Relay these operator steps as they are:",
  "1. Run `opencode reload` in a terminal; it restarts the stdio MCP process of the agent-braid server.",
  "2. Or restart this OpenCode session.",
  "Workspace registry changes take effect only after the server reconnects. This command performs no reload.",
].join("\n")

function attempt(action) {
  try {
    return action()
  } catch {
    return undefined
  }
}

async function guard(action) {
  try {
    return await action()
  } catch {
    return undefined
  }
}

function serverValue() {
  return {
    type: "local",
    command: [`${root}/launch`, "plugin", "serve", "--plugin-root", root],
    codemode: false,
    protocol: "legacy",
  }
}

// The host normalizes stored entries, so compare only the semantic fields.
function sameServer(existing, wanted) {
  return (
    !!existing &&
    existing.type === wanted.type &&
    existing.codemode === wanted.codemode &&
    existing.protocol === wanted.protocol &&
    Array.isArray(existing.command) &&
    existing.command.length === wanted.command.length &&
    wanted.command.every((part, index) => existing.command[index] === part)
  )
}

function readSkill(id) {
  const path = join(root, "skills", id, "SKILL.md")
  const content = readFileSync(path, "utf8")
  const match = /^description: (.+)$/m.exec(content.split("\n---\n")[0])
  return { id, name: id, description: match ? match[1].trim() : id, path, content }
}

function registerServer(editor) {
  const wanted = serverValue()
  const existing = editor.get(SERVER)
  // A foreign entry is never replaced (D13); `plugin doctor` reports it.
  if (existing == null || sameServer(existing, wanted)) editor.set(SERVER, wanted)
}

function registerSkills(editor) {
  for (const id of SKILLS) {
    attempt(() => {
      // A skill ID the editor already has is never removed or updated.
      if (editor.get(id) == null) editor.add(readSkill(id))
    })
  }
}

function registerCommands(ctx, editor, seen) {
  if (seen.has(editor)) return
  seen.add(editor)
  const send = (input, text) =>
    ctx.session.prompt({ ...input.prompt, sessionID: input.sessionID, text, delivery: input.delivery })
  attempt(() =>
    editor.add({
      name: "agent-braid-setup",
      description: "Run the packaged Agent Braid setup skill",
      execute: async (input) => {
        await guard(() => send(input, `Follow this packaged Agent Braid setup skill.\n\n${readSkill("setup").content}`))
      },
    }),
  )
  attempt(() =>
    editor.add({
      name: "agent-braid-reconnect",
      description: "Show the steps to restart the Agent Braid MCP server",
      execute: async (input) => {
        await guard(() => send(input, RECONNECT_TEXT))
      },
    }),
  )
}

export default {
  id: "agent-braid",
  async setup(ctx) {
    const seen = new WeakSet()
    await guard(() => ctx.mcp.transform((editor) => attempt(() => registerServer(editor))))
    await guard(() => ctx.skill.transform((editor) => attempt(() => registerSkills(editor))))
    await guard(() => ctx.command.transform((editor) => attempt(() => registerCommands(ctx, editor, seen))))
  },
}
