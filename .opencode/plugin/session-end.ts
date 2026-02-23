import type { Plugin } from "@opencode-ai/plugin"
import { writeFile, mkdir } from "fs/promises"
import { join } from "path"
import { homedir } from "os"
import { execFile } from "child_process"
import { promisify } from "util"

const execFileAsync = promisify(execFile)

export const SessionEndHook: Plugin = async ({ client }) => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-")
        const projectDir = process.cwd()
        const projectName = (projectDir.split("/").pop() || "unknown").replace(/[^a-zA-Z0-9-_]/g, "_")

        console.log("[session-end] OpenCode session idle detected")

        const handoffContent = `# Session End - ${timestamp}

## Project
${projectName}

## Timestamp
${timestamp}

## Status
Session ended via OpenCode session.idle event

## Working Directory
${projectDir}`

        try {
          const handoffDir = ".claude/sessions"
          await mkdir(handoffDir, { recursive: true })
          await writeFile(join(handoffDir, `${timestamp}-session-end.md`), handoffContent)
          console.log("[session-end] Handoff saved")

          const cmScript = join(homedir(), ".claude/plugins/context-memory/scripts/cm_save.py")
          try {
            await execFileAsync(
              "python3",
              [cmScript, `fork-${projectName}-${timestamp}`, "--max-ops", "20"],
              { timeout: 5000 }
            )
            console.log("[session-end] cm-save initiated")
          } catch (err) {
            console.error("[session-end] cm-save failed:", err)
          }
        } catch (err) {
          console.error("[session-end] Hook failed:", err)
        }
      }
    }
  }
}
