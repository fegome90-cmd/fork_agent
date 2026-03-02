# Bug Hunter Skill

> Systematic bug detection and fixing methodology for fork_agent

**Version:** 1.0.0  
**Status:** Active  
**Domain:** Testing, Debugging, Quality Assurance

## Purpose

Provide a disciplined framework for detecting, documenting, and fixing bugs in the fork_agent codebase using evidence-based verification.

## Prerequisites

- Python 3.11+
- pytest installed
- Access to codebase with tests

## Workflow

### Phase 1: Detection

1. **Identify the bug symptom**
   - Document exact error message
   - Note file, line number, function name
   - Capture stack trace

2. **Check for silent failures**
   ```bash
   rg "except Exception:\s*pass" src/ -S
   ```
   - Any hits are bugs that silently swallow errors

3. **Check for empty catch blocks**
   ```bash
   rg "except.*:\s*\n\s*pass" src/ -S
   ```

### Phase 2: Verification

1. **Create bughunt test**
   ```python
   pytest.mark.bughunt
   
   def test_<bug_description>(mock_promise_repo):
       # Test that catches the bug
       pass
   ```

2. **Run bughunt tests**
   ```bash
   pytest -m bughunt --junitxml=artifacts/junit-bughunt.xml -v
   ```

3. **Verify test fails BEFORE fix**
   - Confirm test detects the bug
   - Document expected vs actual behavior

### Phase 3: Fix

1. **Apply minimal fix**
   - Fix the specific bug only
   - Do NOT refactor while fixing
   - Preserve existing behavior for non-bug cases

2. **Verify test passes AFTER fix**
   ```bash
   pytest -m bughunt -v
   ```

3. **Check for regressions**
   ```bash
   pytest tests/ -v --tb=short
   ```

### Phase 4: Evidence

1. **Generate patch**
   ```bash
   git diff > _ctx/evidence/patches/WO-XXX.patch
   ```

2. **Generate test evidence**
   ```bash
   pytest -m bughunt --junitxml=artifacts/junit-bughunt.xml
   ```

3. **Commit with evidence**
   ```bash
   git add -A
   git commit -m "WO-XXX: <description>"
   ```

## Anti-Patterns (DO NOT)

- ❌ `except Exception: pass` - silently swallows errors
- ❌ `except:` without specific exception type
- ❌ Empty catch blocks
- ❌ Fixing multiple bugs in one commit
- ❌ Refactoring while fixing bugs
- ❌ Deleting failing tests to "pass"

## Test Markers

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.bughunt` | Bug detection tests |
| `@pytest.mark.integration` | Integration tests |
| `@pytest.mark.unit` | Unit tests |

## Evidence Requirements

Each WO must include:

1. **Patch file** - `_ctx/evidence/patches/WO-XXX.patch`
2. **JUnit XML** - `artifacts/junit-bughunt.xml`
3. **Commit** - With descriptive message

## Example Bug Fix Flow

```python
# BEFORE (bug)
try:
    do_something()
except Exception:
    pass  # SILENT FAILURE!

# AFTER (fixed)
try:
    do_something()
except Exception as e:
    logger.error(f"Failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

## Integration with CI/CD

Run bughunt tests in CI:

```yaml
- name: Bug Hunt Tests
  run: |
    pytest -m bughunt --junitxml=artifacts/junit-bughunt.xml -v
  
- name: Upload Evidence
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: bughunt-evidence
    path: artifacts/
```

## Maintenance

- Review bughunt markers quarterly
- Update anti-patterns as new patterns emerge
- Keep test evidence for traceability
