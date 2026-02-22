#!/bin/bash
# git-branch-guard.sh - PreToolUse hook for git operations

set -euo pipefail

TOOL_INPUT="${TOOL_INPUT:-}"
TOOL_NAME="${TOOL_NAME:-Bash}"

# Only check Bash commands
if [ "$TOOL_NAME" != "Bash" ]; then
    exit 0
fi

# Allowlist of safe git operations
ALLOWED_GIT_COMMANDS="add|commit|status|diff|log|show|blame|branch|fetch"

# Block dangerous operations
DANGEROUS_GIT_COMMANDS="checkout|switch|reset|clean|push|pull|rebase|merge|stash|cherry-pick"

# Check for dangerous commands
if echo "$TOOL_INPUT" | grep -qiE "(git\s+($DANGEROUS_GIT_COMMANDS)|git\s+($DANGEROUS_GIT_COMMANDS)\s)"; then
    echo "{\"error\": \"Git operation blocked by git-branch-guard\", \"allowed\": false, \"reason\": \"Only safe git operations allowed: $ALLOWED_GIT_COMMANDS\"}" >&2
    exit 2
fi

# Check if it's a git command at all
if echo "$TOOL_INPUT" | grep -qiE "git\s+"; then
    # Verify it's in the allowlist
    if ! echo "$TOOL_INPUT" | grep -qiE "git\s+($ALLOWED_GIT_COMMANDS)"; then
        echo "{\"error\": \"Git command not in allowlist\", \"allowed\": false, \"reason\": \"Allowed: $ALLOWED_GIT_COMMANDS\"}" >&2
        exit 2
    fi
fi

# Block dangerous patterns
if echo "$TOOL_INPUT" | grep -qiE "rm\s+(-rf|-r\s+-f)\s+(/|~\.|\.\.)"; then
    echo "{\"error\": \"Dangerous rm pattern blocked\", \"allowed\": false}" >&2
    exit 2
fi

echo '{"allowed": true}'
