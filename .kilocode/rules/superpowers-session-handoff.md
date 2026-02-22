# Session Handoff Rule

## Purpose
Check for pending session handoffs when starting a new session and inject them into context.

## Trigger
This rule triggers automatically when a new session starts.

## Actions

### Step 1: Check for Handoff Files
1. Look for `.kilocode/sessions/handoff.md` in the current workspace
2. If file exists, read its contents

### Step 2: Inject Handoff into Context
If handoff file exists:
1. Parse the markdown content
2. Extract:
   - Session status (IN PROGRESS / COMPLETED / BLOCKED)
   - What was accomplished
   - What needs to be done next
   - Files modified
   - Commands to continue

3. Add handoff summary to the conversation context with:
   - "📋 **Session Handoff Detected:** Previous session was [status]"
   - Key accomplishments
   - Next steps
   - Important files/commands

### Step 3: Archive Old Handoff
After successfully loading handoff:
1. Rename `.kilocode/sessions/handoff.md` to include timestamp
2. Format: `.kilocode/sessions/handoff_YYYYMMDD_HHMMSS.md`

## Example Handoff Format

```markdown
# Session Handoff - [Task Name]

**Date:** 2026-02-22
**Session:** [Brief description]

## Status: IN PROGRESS|BLOCKED|COMPLETED

### What was accomplished:
- Item 1
- Item 2

### What needs to be done next:
1. Next step 1
2. Next step 2

### Files modified:
- `src/file1.py`
- `src/file2.py`

### Commands to continue:
```bash
command to run
```
```

## Notes
- This rule runs silently in the background
- Does not interrupt user flow unless there are critical blockers mentioned
- If status is BLOCKED, present the blockers prominently
