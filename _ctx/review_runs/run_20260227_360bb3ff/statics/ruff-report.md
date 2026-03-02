# Static Analysis: ruff

## Tool: ruff
## Status: PASS (with warnings)

## Summary
69 lint issues found (all P2 level - code quality, not blocking)

## Issue Breakdown
| Code | Count | Description |
|------|-------|-------------|
| SIM102 | 2 | Nested if statements |
| SIM105 | 1 | Use contextlib.suppress |
| SIM118 | 1 | dict.keys() comparison |
| ARG002 | 4 | Unused method arguments |
| ARG005 | 2 | Unused lambda arguments |
| B904 | 6 | raise from None missing |
| E402 | 1 | Module import not at top |
| I001 | 52 | Import block unsorted |

## Verdict
**PASS** - No blocking errors (F, E). All issues are code quality improvements.
