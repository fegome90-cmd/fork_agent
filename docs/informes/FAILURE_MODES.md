# fork_agent - Failure Modes Analysis

> **Generated:** 2026-02-23 | **Auditor:** Sisyphus
> 
> This document catalogues known failure modes, detection mechanisms, and mitigation strategies.

---

## 1. tmux Runtime Failures

### FM-TM-001: tmux Session Creation Failure

| Property | Value |
|----------|-------|
| **Symptom** | `tmux new-session` returns non-zero, agent spawn fails |
| **Cause** | tmux not installed, insufficient permissions, session name collision |
| **Detection** | TmuxAgent.spawn() checks returncode (L199-203) |
| **Mitigation** | Circuit breaker records failure, agent marked FAILED |
| **Recovery** | Manual: check tmux installation, kill conflicting sessions |
| **Gap** | No automatic retry for session creation |
| **Priority** | P0 |

**Evidence:** `src/application/services/agent/agent_manager.py:184-223`

```python
# Detection code
if result.returncode != 0:
    logger.error(f"Failed to create tmux session: {result.stderr}")
    self._update_status(AgentStatus.FAILED)
    self._record_failure()
    return False
```

### FM-TM-002: tmux Session Timeout

| Property | Value |
|----------|-------|
| **Symptom** | Session not ready after `session_timeout` seconds |
| **Cause** | Slow system, resource contention, tmux bug |
| **Detection** | `_wait_for_session(timeout=10s)` returns False (L206-210) |
| **Mitigation** | Session killed, failure recorded |
| **Recovery** | Automatic: cleanup + retry via circuit breaker |
| **Gap** | No exponential backoff for session creation retries |
| **Priority** | P1 |

### FM-TM-003: tmux Send Timeout

| Property | Value |
|----------|-------|
| **Symptom** | `tmux send-keys` hangs or times out |
| **Cause** | Unresponsive session, dead process |
| **Detection** | subprocess timeout (5s) in TmuxAgent.send_input() (L291) |
| **Mitigation** | Log error, return False |
| **Recovery** | None - caller must handle |
| **Gap** | No automatic session health check |
| **Priority** | P1 |

### FM-TM-004: Orphaned Sessions (Zombies)

| Property | Value |
|----------|-------|
| **Symptom** | tmux sessions persist after agent termination |
| **Cause** | terminate() not called, crash before cleanup |
| **Detection** | Manual: `tmux ls` shows unexpected sessions |
| **Mitigation** | None |
| **Recovery** | Manual: `tmux kill-session -t <name>` |
| **Gap** | No zombie detection/cleanup mechanism |
| **Priority** | P1 |

---

## 2. Hook Execution Failures

### FM-HK-001: Hook Timeout

| Property | Value |
|----------|-------|
| **Symptom** | Hook script hangs, blocks event processing |
| **Cause** | Script bug, external resource unavailable |
| **Detection** | `subprocess.TimeoutExpired` in ShellActionRunner |
| **Mitigation** | Critical hooks: raise HookExecutionError. Non-critical: log warning, continue |
| **Recovery** | Event continues for non-critical hooks |
| **Gap** | RESOLVED - criticality levels implemented |
| **Priority** | P0 (resolved) |

### FM-HK-002: Hook Non-Zero Exit

| Property | Value |
|----------|-------|
| **Symptom** | Hook script returns non-zero exit code |
| **Cause** | Script error, validation failure |
| **Detection** | `result.returncode != 0` |
| **Mitigation** | Critical hooks: raise HookExecutionError. Non-critical: log warning, continue |
| **Recovery** | Depends on hook's `critical` and `on_failure` settings |
| **Gap** | RESOLVED - criticality + on_failure policy implemented |
| **Priority** | P0 (resolved) |

### FM-HK-003: Hook Injection Attack

| Property | Value |
|----------|-------|
| **Symptom** | Malicious code executed via hook |
| **Cause** | Unsanitized input, env var injection |
| **Detection** | Prevention via env filtering (DANGEROUS_ENV_VARS) |
| **Mitigation** | LD_PRELOAD, LD_LIBRARY_PATH, etc. blocked |
| **Recovery** | N/A (prevention) |
| **Gap** | Shell=True in subprocess - command injection still possible |
| **Priority** | P0 |

### FM-HK-004: Hook Criticality Misconfiguration

| Property | Value |
|----------|-------|
| **Symptom** | Non-critical hook causes workflow abort (or vice versa) |
| **Cause** | Wrong `critical` flag in hooks.json |
| **Detection** | Review hooks.json `critical` field |
| **Mitigation** | Default is `critical: true` - explicit opt-in for continue |
| **Recovery** | Edit hooks.json, set appropriate criticality |
| **Gap** | RESOLVED - explicit criticality with good defaults |
| **Priority** | P0 (resolved) |

---

## 3. Database Failures

### FM-DB-001: Database Lock

| Property | Value |
|----------|-------|
| **Symptom** | SQLite returns SQLITE_BUSY |
| **Cause** | Concurrent writes, long transaction |
| **Detection** | `busy_timeout=5000ms` provides automatic retry |
| **Mitigation** | SQLite auto-retries for 5 seconds |
| **Recovery** | Automatic if lock released within 5s |
| **Gap** | No handling for persistent lock (>5s) |
| **Priority** | P1 |

### FM-DB-002: Database Corruption

| Property | Value |
|----------|-------|
| **Symptom** | Malformed JSON in state files, SQLite errors |
| **Cause** | Crash during write, disk failure |
| **Detection** | Parse errors in from_json(), sqlite3.Error |
| **Mitigation** | Exception raised to caller |
| **Recovery** | Manual: restore from backup |
| **Gap** | No backup/restore mechanism |
| **Priority** | P2 |

### FM-DB-003: Disk Full

| Property | Value |
|----------|-------|
| **Symptom** | SQLite write fails, OSError |
| **Cause** | No disk space |
| **Detection** | sqlite3.Error or OSError |
| **Mitigation** | Exception propagated |
| **Recovery** | Manual: free disk space |
| **Gap** | No disk space monitoring |
| **Priority** | P2 |

---

## 4. State Corruption Failures

### FM-ST-001: Missing State File

| Property | Value |
|----------|-------|
| **Symptom** | `PlanState.load()` returns None |
| **Cause** | File deleted, wrong directory |
| **Detection** | `if not path.exists(): return None` (L90-92) |
| **Mitigation** | CLI shows error, exits with code 1 |
| **Recovery** | Rerun previous workflow phase |
| **Gap** | No automatic state recovery |
| **Priority** | P1 |

### FM-ST-002: Malformed State File

| Property | Value |
|----------|-------|
| **Symptom** | JSON parse error in from_json() |
| **Cause** | Corrupted file, manual edit mistake |
| **Detection** | InvalidStateError with specific message |
| **Mitigation** | Fail-closed: raises exception, no silent corruption |
| **Recovery** | Manual: delete file, rerun phase |
| **Gap** | RESOLVED - schema validation + v0→v1 migration implemented |
| **Priority** | P0 (resolved) |

### FM-ST-003: Unknown Schema Version

| Property | Value |
|----------|-------|
| **Symptom** | UnsupportedSchemaError on load |
| **Cause** | State file from future version |
| **Detection** | UnsupportedSchemaError with version info |
| **Mitigation** | Fail-closed: rejects unknown versions |
| **Recovery** | Upgrade fork_agent to support version |
| **Gap** | RESOLVED - fail-closed for future versions |
| **Priority** | P0 (resolved) |

### FM-ST-003: State Drift

| Property | Value |
|----------|-------|
| **Symptom** | State file doesn't match reality |
| **Cause** | External changes, incomplete cleanup |
| **Detection** | None |
| **Mitigation** | None |
| **Recovery** | Manual: delete state files, restart workflow |
| **Gap** | No state validation against reality |
| **Priority** | P2 |

---

## 5. Circuit Breaker Failures

### FM-CB-001: Circuit Stuck OPEN

| Property | Value |
|----------|-------|
| **Symptom** | All operations rejected indefinitely |
| **Cause** | recovery_timeout too long, no success to reset |
| **Detection** | can_execute() always returns False |
| **Mitigation** | After 30s, transitions to HALF_OPEN |
| **Recovery** | Manual: cb.reset() or wait for timeout |
| **Gap** | No alerting when circuit opens |
| **Priority** | P1 |

### FM-CB-002: HALF_OPEN Oscillation

| Property | Value |
|----------|-------|
| **Symptom** | Circuit oscillates between OPEN and HALF_OPEN |
| **Cause** | Underlying issue not resolved |
| **Detection** | Frequent state transitions in logs |
| **Mitigation** | half_open_max_calls limits exposure |
| **Recovery** | Fix underlying cause |
| **Gap** | No escalation after repeated failures |
| **Priority** | P2 |

---

## 6. Message/IPC Failures

### FM-IP-001: Message Not Delivered

| Property | Value |
|----------|-------|
| **Symptom** | Agent doesn't receive message |
| **Cause** | tmux send-keys failure, session dead |
| **Detection** | send_input() returns False (L293) |
| **Mitigation** | Message stored in MessageStore for audit |
| **Recovery** | Manual: check DLQ, resend |
| **Gap** | No automatic message retry |
| **Priority** | P1 |

### FM-IP-002: Message Expiration

| Property | Value |
|----------|-------|
| **Symptom** | Message deleted before delivery |
| **Cause** | TTL expired (24h default) |
| **Detection** | cleanup_expired() removes old messages |
| **Mitigation** | 24-hour TTL provides buffer |
| **Recovery** | N/A - message lost |
| **Gap** | No TTL warning before expiration |
| **Priority** | P3 |

---

## 7. Fork Generation Failures

### FM-FG-001: Invalid Target Agent

| Property | Value |
|----------|-------|
| **Symptom** | Script exits with error |
| **Cause** | Unsupported agent type specified |
| **Detection** | validate_agent() case statement (L28-38) |
| **Mitigation** | Error message, exit 1 |
| **Recovery** | Use supported agent: .claude, .opencode, .kilocode, .gemini |
| **Gap** | None |
| **Priority** | P3 |

### FM-FG-002: Missing Source Files

| Property | Value |
|----------|-------|
| **Symptom** | Incomplete fork, missing commands/skills |
| **Cause** | Source files don't exist |
| **Detection** | `if [[ -f ... ]]` checks in script |
| **Mitigation** | Skips missing files silently |
| **Recovery** | Manual: copy missing files |
| **Gap** | No verification after generation |
| **Priority** | P2 |

---

## 8. Failure Modes Summary Table

| ID | Category | Symptom | Detection | Mitigation | Priority |
|----|----------|---------|-----------|------------|----------|
| FM-TM-001 | tmux | Session creation fails | returncode != 0 | Circuit breaker | P0 |
| FM-TM-002 | tmux | Session timeout | _wait_for_session fails | Cleanup | P1 |
| FM-TM-003 | tmux | Send timeout | subprocess timeout | Log, return False | P1 |
| FM-TM-004 | tmux | Orphaned sessions | Manual (tmux ls) | None | P1 |
| FM-HK-001 | Hooks | Hook timeout | TimeoutExpired | RuntimeError | P1 |
| FM-HK-002 | Hooks | Hook non-zero exit | returncode != 0 | RuntimeError | P2 |
| FM-HK-003 | Hooks | Injection attack | Prevention | Env filtering | P0 |
| FM-DB-001 | Database | DB lock | SQLITE_BUSY | busy_timeout | P1 |
| FM-DB-002 | Database | Corruption | Parse errors | Exception | P2 |
| FM-DB-003 | Database | Disk full | OSError | Exception | P2 |
| FM-ST-001 | State | Missing file | path.exists | CLI error | P1 |
| FM-ST-002 | State | Malformed JSON | JSONDecodeError | Exception | P2 |
| FM-ST-003 | State | State drift | None | None | P2 |
| FM-CB-001 | Circuit | Stuck OPEN | can_execute=False | Timeout reset | P1 |
| FM-CB-002 | Circuit | Oscillation | Log patterns | half_open limit | P2 |
| FM-IP-001 | IPC | Message not delivered | send_input False | MessageStore | P1 |
| FM-IP-002 | IPC | Message expiration | cleanup_expired | 24h TTL | P3 |
| FM-FG-001 | Fork | Invalid agent | validate_agent | Exit 1 | P3 |
| FM-FG-002 | Fork | Missing files | -f checks | Silent skip | P2 |

---

## 9. Gap Analysis Summary

### Detection Gaps (no automatic detection)
- FM-TM-004: Orphaned sessions
- FM-ST-003: State drift
- FM-CB-001: Circuit stuck (no alerting)

### Mitigation Gaps (no automatic mitigation)
- FM-TM-001: No automatic session creation retry
- FM-TM-004: No zombie cleanup
- FM-HK-001: Failed hooks not queued for retry
- FM-DB-002: No backup/restore
- FM-ST-001/002: No automatic state recovery
- FM-IP-001: No automatic message retry

### Recovery Gaps (manual only)
- Most failures require manual intervention
- No automated rollback mechanism
- No health check that triggers auto-recovery

---

*Document generated by failure modes audit - 2026-02-23*
