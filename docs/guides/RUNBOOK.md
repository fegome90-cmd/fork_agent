# Runbook - Operations Guide

> Operational procedures for fork_agent. Last updated: 2026-02-25

---

## Quick Reference

### Start Services

```bash
# Install dependencies
make install

# Start API server (optional)
uv run fork-api

# Check status
uv run fork doctor status
```

### Stop Services

```bash
# Kill all tmux sessions (CAUTION)
tmux kill-server

# Or kill specific session
tmux kill-session -t <session-name>
```

---

## Deployment Procedures

### Fresh Deployment

```bash
# 1. Clone and setup
git clone <repo-url>
cd tmux_fork

# 2. Install dependencies
make install
make dev

# 3. Configure environment
cp .env.sample .env
# Edit .env with your API keys

# 4. Verify installation
make test-cov

# 5. Run pre-commit checks
make prePR
```

### Update Deployment

```bash
# 1. Pull latest
git pull origin main

# 2. Update dependencies
uv sync --all-extras

# 3. Run tests
make test-cov

# 4. Deploy
tmux new-session -d -s deploy "uv run fork-api"
```

---

## Monitoring and Alerts

### Health Checks

```bash
# Check all services
uv run fork doctor status

# Reconcile sessions
uv run fork doctor reconcile

# View tmux sessions
tmux ls
```

### Log Locations

| Service | Log Path |
|---------|----------|
| API Server | stdout (when running) |
| Agent Traces | `.claude/traces/` |
| Memory DB | `data/memory.db` |
| Workflow State | `.claude/plan-state.json` |

### Metrics to Watch

| Metric | Normal | Alert |
|--------|-------|-------|
| Agent Sessions | < 10 | > 20 |
| Orphan Sessions | 0 | > 5 |
| Circuit Breaker | Closed | Open > 5min |
| Test Coverage | > 95% | < 90% |

---

## Common Issues and Fixes

### Issue: "tmux not found"

**Solution:**
```bash
# Install tmux
# macOS
brew install tmux

# Ubuntu/Debian
sudo apt install tmux
```

### Issue: "Database locked"

**Solution:**
```bash
# Check for existing processes
ps aux | grep python

# Remove lock file
rm -f data/memory.db-journal
```

### Issue: "Hook failed: workspace-init.sh"

**Solution:**
```bash
# Make hook executable
chmod +x .hooks/workspace-init.sh

# Test manually
.hooks/workspace-init.sh
```

### Issue: Tests failing with coverage

**Solution:**
```bash
# Run with verbose output
uv run pytest tests/ -v --cov --cov-report=term-missing

# Check coverage threshold in pyproject.toml
# Minimum: 72%
```

### Issue: Git command blocked

**Solution:**
This is expected! The git-branch-guard.sh blocks dangerous commands. Use safe alternatives:

| Blocked | Use Instead |
|---------|-------------|
| `git checkout` | `git branch` + `git add` |
| `git push` | Request review first |
| `git rebase` | `git merge` |
| `git reset` | `git revert` |

---

## Rollback Procedures

### Quick Rollback (last commit)

```bash
git checkout HEAD~1
make install
make test
```

### Full Rollback (specific version)

```bash
# Find version to rollback to
git log --oneline -20

# Checkout specific commit
git checkout <commit-hash>

# Reinstall
make install
make test-cov
```

### Database Rollback

```bash
# Backup current DB
cp data/memory.db data/memory.db.backup

# Reset (delete observations)
rm data/memory.db
uv run memory save "re-initialized"
```

---

## Backup and Recovery

### Backup

```bash
# Backup database
cp data/memory.db data/memory.db.$(date +%Y%m%d)

# Backup configuration
cp .env .env.backup
```

### Recovery

```bash
# Restore database
cp data/memory.db.backup data/memory.db

# Restore env
cp .env.backup .env
```

---

## Session Checkpoint

At the end of each work session, **always** run:

```bash
# 1. Save human-readable handoff
/fork-checkpoint

# 2. Save machine-readable context
cm-save <session-name>
```

This enables:
- `/fork-resume` - Continue from last handoff
- `cm-load <name>` - Rehydrate full context

---

## Emergency Contacts

| Issue | Action |
|-------|--------|
| All sessions hung | `tmux kill-server` |
| Database corrupted | Restore from backup |
| Tests failing | Check pyproject.toml coverage |
| API down | Check port 8000, restart fork-api |

---

## Reference

- Full Agent System Runbook: [`docs/runbook/agent-system-runbook.md`](runbook/agent-system-runbook.md)
- Subagent Analysis: [`docs/runbook/subagent-stability-analysis.md`](runbook/subagent-stability-analysis.md)
- Contributing: [`docs/CONTRIB.md`](CONTRIB.md)
