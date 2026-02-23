# Agent System Runbook

## Overview

This runbook covers deployment, monitoring, and troubleshooting for the fork_agent system with enhanced tmux orchestration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ AgentManager │  │ SessionPool  │  │ HealthMonitor           │ │
│  │ - spawn()    │  │ - acquire()  │  │ - heartbeat()           │ │
│  │ - terminate()│  │ - release()  │  │ - circuit_breaker()     │ │
│  │ - monitor()  │  │ - timeout()  │  │ - graceful_degradation │ │
│  └──────────────┘  └──────────────┘  └─────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                      SESSION LAYER (tmux)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ TmuxAgent    │  │ IPCBridge    │  │ RetryStrategy           │ │
│  │ - spawn      │  │ - pub/sub    │  │ - exponential_backoff   │ │
│  │ - terminate  │  │ - retry      │  │ - dead_letter_queue    │ │
│  │ - send_input │  │ - timeout    │  │                         │ │
│  └──────────────┘  └──────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Deployment

### Prerequisites
- Python 3.11+
- tmux installed
- SQLite3

### Setup

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/unit/ -v

# Start health monitoring
python -c "from src.application.services.agent import agent_manager; m = agent_manager.get_agent_manager(); m.start_health_monitoring()"
```

## Monitoring

### Health Checks

```bash
# Check agent status
tmux ls

# Check process status
ps aux | grep -E "(tmux|python)"

# Check logs
tail -f data/logs/agent.log
```

### Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| agent.status | Health/Unhealthy/Failed | Any FAILED |
| circuit_breaker.state | Closed/Open/Half_Open | OPEN > 5 min |
| ipc.queue.size | Pending messages | > 1000 |
| agent.error_count | Total errors | > 10/min |

## Troubleshooting

### Agent Won't Start

1. Check tmux availability:
```bash
tmux ls
```

2. Check session limits:
```bash
tmux display-message -t all '#{session_name}'
```

3. Verify working directory exists

### Circuit Breaker Open

The circuit breaker opens after 5 consecutive failures. Recovery:
- Automatic after 60 seconds (half-open)
- Manual reset via AgentManager

### IPC Message Delivery Failed

1. Check Dead Letter Queue size
2. Review retry logs
3. Verify network/tmux connectivity

## Emergency Procedures

### Kill All Agents

```bash
tmux kill-server  # DANGER: kills ALL tmux sessions
```

### Force Stop Specific Agent

```python
from src.application.services.agent.agent_manager import get_agent_manager
manager = get_agent_manager()
manager.terminate_agent("agent-name")
```

### Rollback

```bash
git checkout HEAD~1
uv sync --all-extras
uv run pytest tests/unit/
```
