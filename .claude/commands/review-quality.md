---
description: Review code/diff against project Python production standards
argument-hint: [file path or "staged" for git staged changes]
---

Review the target ($ARGUMENTS, default = currently open file or staged diff)
against the standards in CLAUDE.md.

Output format:

## Summary
One-paragraph verdict: ship / revise / block.

## Findings

For each issue:
- **Severity**: blocker | major | minor | nit
- **Category**: pep8 | solid | dry | kiss | yagni | clean-code | architecture | docs | tests
- **Location**: file:line
- **Problem**: what is wrong
- **Fix**: concrete code suggestion (use a diff block)

## Documentation Impact
- README needs update? (Y/N + what)
- OpenAPI needs update? (Y/N + which endpoints)
- ADR needed? (Y/N + draft title and reason)

## Suggested Next Actions
Numbered list, ordered by priority.

Do NOT auto-apply changes. Wait for user approval.