# Conventional Commit Debt

## Status

53 of 279 commits in `main` do not follow [Conventional Commits](https://www.conventionalcommits.org/) format.

## Source

All 53 non-conforming commits are from autoresearch experiment baselines and optimization sessions. These are historical artifacts that were committed directly to `main` before the project adopted conventional commit enforcement.

Typical patterns:

- `Baseline: 8.44s for 2025 unit tests...`
- `Re-baseline after temp dir cleanup: 8.13s...`
- `Health check test: set interval=0...`
- `Circuit breaker time.sleep removal: 17.76s...`

## Policy

**Forward-only enforcement.** New commits MUST follow conventional format. The CI `Conventional Commits` check enforces this for all PRs.

## Decision NOT to rewrite

`git filter-branch --msg-filter` could bulk-fix these, but:

1. **Shared repo risk** — force-push to `main` breaks all clones and forks
2. **Review integrity** — rewriting commit hashes invalidates PR references and review threads
3. **Low ROI** — the non-conforming messages are still descriptive and useful for archaeology
4. **Diminishing returns** — autoresearch commits are experiment baselines, not production changes

If a future cleanup is desired, create a `chore: normalize historical commit messages` issue and execute during a low-activity period with team coordination.

## Stats

| Metric                | Value                             |
| --------------------- | --------------------------------- |
| Total commits         | 279                               |
| Conventional          | 226 (81%)                         |
| Non-conventional      | 53 (19%)                          |
| Source                | Autoresearch experiments          |
| Enforcement           | CI check on all PRs (PR #38+)     |
| Last non-conventional | `90cc6cfa5` (rewritten in PR #40) |
