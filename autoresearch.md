# Autoresearch: Optimize tmux_fork unit test speed

## Objective
Reduce the runtime of the tmux_fork unit test suite (1720 tests, currently ~15.3s). Focus on pytest configuration, fixture optimization, and parallelization strategies that maintain correctness.

## Metrics
- **Primary**: total_seconds (s, lower is better) — wall-clock time for the full unit test suite
- **Secondary**: passed_tests — ensure no tests are skipped or broken

## How to Run
`bash autoresearch.sh` — outputs `METRIC total_seconds=XX.X` and `METRIC passed_tests=NNNN` lines.

## Files in Scope
- `pyproject.toml` — pytest configuration, dependencies
- `tests/conftest.py` — shared fixtures
- `tests/unit/conftest.py` — unit test fixtures
- `pytest.ini` or `setup.cfg` — if they exist, pytest config
- Any `conftest.py` under `tests/`

## Off Limits
- `src/` — production code changes are NOT the goal
- `tests/unit/` test files themselves — do not modify test logic or skip tests
- Any test that changes its assertion behavior

## Constraints
- ALL 1615+ tests must pass (no skips, no failures)
- No new dependencies beyond pytest-xdist and pytest-benchmark (already available or trivial to add)
- Changes must be reversible (configuration-only preferred)
- Do not remove any test files or test functions

## What's Been Tried
(Baseline run — no optimizations yet)
