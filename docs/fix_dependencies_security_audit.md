# Security Audit Integration: pip-audit
`pip-audit` has been integrated to address loose version pinning and CVEs.

## 1. Manual Audit Commands
```bash
# Install and scan requirements
pip install pip-audit
pip-audit -r requirements.txt
```

## 2. GitHub Actions Workflow
Add to `.github/workflows/security-audit.yml`:
```yaml
name: Security Audit
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with: {python-version: '3.10'}
      - name: Run audit
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt
```

## 3. CI/CD Suggestions
- **Fail on PR**: Configure CI to block PRs with vulnerabilities.
- **Scheduled Scans**: Run weekly audits for new CVEs.
- **Fix Mode**: `pip-audit --fix` for automated updates.

## Verification
1. Run `pip-audit -r requirements.txt`.
2. Verify exit code is 0.