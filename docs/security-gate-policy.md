# Security Gate Policy

## Overview
The security gate establishes baseline security scanning for all code changes. It runs in parallel with existing CI jobs and provides early detection of vulnerabilities and security issues.

## Tools

### 1. pip-audit
- **Purpose**: Python dependency vulnerability scanning
- **Runs on**: All commits affecting `backend/requirements.txt` or Python code
- **Fail Thresholds**:
  - **Critical severity**: BLOCK merge (exit code 1)
  - **High severity**: BLOCK merge (exit code 1)
  - **Medium/Low severity**: WARN only (continue-on-error)

### 2. Bandit
- **Purpose**: Python SAST (Static Application Security Testing)
- **Configuration**: `backend/pyproject.toml`
- **Fail Thresholds**:
  - **High severity**: BLOCK merge (issues in security-critical paths: auth, crypto, data access)
  - **Medium severity**: WARN only
  - **Low severity**: Informational only
- **Output**: JSON report uploaded as CI artifact

### 3. Secret Scan
- **Purpose**: Detect accidental secret commits
- **Scope**: Git history for newly added lines
- **Patterns**: `api_key`, `secret`, `password`, `token` (case-insensitive)
- **Action**: WARN on match, manual review required

## Enforcement Timeline

### Phase 1: Baseline (Days 1-30)
- **Status**: `continue-on-error: true` in CI
- **Action**: Collect metrics, tune thresholds, establish baseline
- **Developer Impact**: Warnings only, no blocked merges
- **Goal**: Identify false positives, document waivers

### Phase 2: Enforcement (Day 31+)
- **Status**: Remove `continue-on-error` for pip-audit and bandit high-severity
- **Action**: Block merges on critical/high vulnerabilities
- **Developer Impact**: Must fix or request waiver before merge
- **Goal**: Zero critical/high vulnerabilities in main branch

## Waiver Process

### When to Request a Waiver
- False positive confirmed by security review
- Vulnerability not exploitable in current context
- Fix requires breaking API change (defer to next major release)
- Dependency update blocked by compatibility

### How to Request
1. Document finding in PR description:
   - Tool output (pip-audit/bandit ID)
   - Rationale for waiver
   - Mitigation steps (if applicable)
   - Timeline for fix (if deferred)
2. Tag security reviewer: `@security-team` or relevant maintainer
3. Reviewer must explicitly approve with comment: `WAIVER APPROVED: [reason]`
4. Add waiver to `docs/governance/security-waivers.md`

### Waiver Approval Authority
- **pip-audit critical/high**: Requires 2 approvals (1 from security team)
- **bandit high**: Requires 1 approval from security team or senior engineer
- **Secret scan**: Manual verification that it's not a real secret

## Metrics

Track weekly:
- **Scan coverage**: % of commits scanned
- **Mean time to fix**: From detection to merge of fix
- **Waiver rate**: % of findings waived vs. fixed
- **False positive rate**: % of findings marked false positive

Report monthly in governance review.

## Escalation

If security gate blocks critical hotfix:
1. Notify on-call engineer
2. Create security incident ticket
3. Merge with `security-override` label (requires VP Engineering approval)
4. Remediation PR must follow within 24 hours

## References
- pip-audit docs: https://pypi.org/project/pip-audit/
- Bandit docs: https://bandit.readthedocs.io/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
