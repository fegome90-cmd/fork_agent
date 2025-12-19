# Agent Checkout System - Usage Guide

## Overview

The Agent Checkout System provides automatic logging and monitoring for fork agents, eliminating the need to manually supervise Zellij sessions.

## Quick Start

### 1. Launch Agents with Checkout

```bash
# Clear previous log
> .claude/logs/agent_checkout.log

# Launch agent with automatic checkout
.claude/scripts/fork_agent_with_checkout.sh \
  "C1" \
  "Security Fix" \
  "docs/fix_security.md" \
  "gemini -y -m gemini-3-flash-preview 'Fix security vulnerability'"
```

### 2. Monitor Agents (in another terminal)

```bash
# Real-time monitoring
.claude/scripts/monitor_agents.sh

# Or check status anytime
tail -20 .claude/logs/agent_checkout.log

# Generate summary
python3 .claude/scripts/generate_agent_summary.py
```

## Integration with Zellij

### Launch Multiple Agents with Checkout

```bash
# Create Zellij session
zellij --session my_agents

# Launch Agent 1
zellij --session my_agents action new-pane -- \
  .claude/scripts/fork_agent_with_checkout.sh \
  "C1" "Security Fix" "docs/fix_security.md" \
  "gemini -y 'Fix security'"

# Launch Agent 2
zellij --session my_agents action new-pane -- \
  .claude/scripts/fork_agent_with_checkout.sh \
  "C2" "Dependency Pinning" "docs/fix_deps.md" \
  "gemini -y 'Pin dependencies'"

# Monitor in another terminal
.claude/scripts/monitor_agents.sh .claude/logs/agent_checkout.log 2
```

## Checkout Log Format

```yaml
---
timestamp: "2025-12-18T23:45:00-03:00"
agent_id: "C1"
agent_name: "Security Fix"
status: "SUCCESS"
duration_seconds: 45
files_modified:
  - "fork_terminal.py"
report_path: "docs/fix_security.md"
summary: "Applied shlex.quote() sanitization"
errors: []
```

## Scripts Reference

### monitor_agents.sh

**Purpose**: Watch checkout log in real-time  
**Usage**: `./monitor_agents.sh [LOG_FILE] [EXPECTED_AGENTS]`  
**Example**: `./monitor_agents.sh .claude/logs/agent_checkout.log 5`

### generate_agent_summary.py

**Purpose**: Generate human-readable summary  
**Usage**: `python3 generate_agent_summary.py [LOG_FILE]`  
**Example**: `python3 generate_agent_summary.py .claude/logs/agent_checkout.log`

### fork_agent_with_checkout.sh

**Purpose**: Wrap agent command with checkout  
**Usage**: `./fork_agent_with_checkout.sh <ID> <NAME> <REPORT> <COMMAND>`  
**Example**: See Quick Start above

## Benefits

✅ **No Manual Monitoring**: Agents report automatically  
✅ **Asynchronous**: Check status anytime  
✅ **Audit Trail**: Complete execution history  
✅ **Easy Integration**: Simple wrapper script  
✅ **Scalable**: Works with any number of agents

## Example Workflow

```bash
# Terminal 1: Launch agents
cd /Users/felipe_gonzalez/Developer/fork_agent-main
> .claude/logs/agent_checkout.log

for i in 1 2 3; do
  zellij --session agents action new-pane -- \
    .claude/scripts/fork_agent_with_checkout.sh \
    "C${i}" "Agent ${i}" "docs/agent${i}.md" \
    "gemini -y 'Task ${i}'"
done

# Terminal 2: Monitor
cd /Users/felipe_gonzalez/Developer/fork_agent-main
.claude/scripts/monitor_agents.sh .claude/logs/agent_checkout.log 3

# Later: Check results
python3 .claude/scripts/generate_agent_summary.py
```

## Troubleshooting

**Q: Agents not checking out?**  
A: Ensure wrapper script is executable: `chmod +x .claude/scripts/*.sh`

**Q: Can't find log file?**  
A: Check path: `.claude/logs/agent_checkout.log` (relative to project root)

**Q: Monitor script not showing updates?**  
A: Ensure log file exists: `touch .claude/logs/agent_checkout.log`
