# Work Orders Summary - Spine-First Release

## Execution Order (Recommended)

### Phase 1: Core Spine (P0 - Must Complete First)

| Order | WO ID | Title | Est. Files | Blockers |
|-------|-------|-------|------------|----------|
| 1 | WO-P0-1 | Verify runner real | 2 | None |
| 2 | WO-P0-2 | ExitGate mínimo | 1 | WO-P0-1 |
| 3 | WO-P0-3 | Phase correctness | 2 | None |

### Phase 2: Data Integrity (P1)

| Order | WO ID | Title | Est. Files | Blockers |
|-------|-------|-------|------------|----------|
| 4 | WO-P1-1 | SSOT explicit | 3 | None |
| 5 | WO-P1-2 | Integration test spine | 1 | WO-P0-1, WO-P0-2 |

### Phase 3: Developer Experience (P2)

| Order | WO ID | Title | Est. Files | Blockers |
|-------|-------|-------|------------|----------|
| 6 | WO-P2-1 | Loop command | 2 | WO-P0-1, WO-P0-2, WO-P0-3, WO-P1-1 |
| 7 | WO-P2-2 | API wired | 3 | WO-P0-1, WO-P0-2 |

---

## Blocking Points

### Before Starting WO-P0-2
- WO-P0-1 must be complete (verify runner produces real test_results)

### Before Starting WO-P1-2
- WO-P0-1 must be complete (verify needs real runner)
- WO-P0-2 must be complete (exit gate needs real results)

### Before Starting WO-P2-1
- All P0 and P1 WOs should be complete
- This is the "crown jewel" - user-facing automation

### Before Starting WO-P2-2
- WO-P0-1 and WO-P0-2 should be complete
- API will call real verify which needs real runner

---

## Quick Start Commands

```bash
# Phase 1: Run P0 WOs
cd /Users/felipe_gonzalez/Developer/tmux_fork

# WO-P0-1: Verify runner
# Edit: src/interfaces/cli/commands/workflow.py
# Add: src/application/services/workflow/verify_runner.py

# After WO-P0-1: Test
memory workflow outline "test"
memory workflow execute
memory workflow verify --tests
cat .claude/verify-state.json

# WO-P0-2: ExitGate
# Edit: src/interfaces/cli/commands/workflow.py (ship handler)

# WO-P0-3: Phase correctness  
# Edit: src/interfaces/cli/commands/workflow.py (verify handler)

# Phase 2: P1 WOs
# WO-P1-1: Document SSOT, add validation
# WO-P1-2: Create tests/integration/test_workflow_spine.py

# Phase 3: P2 WOs
# WO-P2-1: Add loop command
# WO-P2-2: Wire API to services
```

---

## Files Created

```
docs/work-orders/
├── WO-P0-1-verify-runner-real.yaml
├── WO-P0-2-exitgate-minimo.yaml
├── WO-P0-3-phase-correctness.yaml
├── WO-P1-1-ssot-explicit.yaml
├── WO-P1-2-integration-test-spine.yaml
├── WO-P2-1-loop-command.yaml
├── WO-P2-2-api-wired.yaml
└── README.md (this file)
```

---

## Notes

- All WOs follow fail-closed principle: don't assume success, verify evidence
- Each WO includes specific validation commands to verify DoD
- Dependencies are explicit - don't start dependent WOs before prerequisites
- Evidence bundle: each WO specifies what files/logs must exist after completion
