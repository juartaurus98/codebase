# Report Footer — Standard Command Output Format

Every command report must end with this standard footer section.

## Status Badge

Choose one based on outcome:
- `✅ Complete` — all steps succeeded, no issues found
- `❌ Failed` — command could not complete due to a blocking error
- `⚠️ Warnings` — completed with non-blocking issues that should be reviewed

## Output Artifacts

List every file created or modified by this command:
```
Output Artifacts:
  {created|updated} {file-path} ({brief description})
  {created|updated} {file-path} ({brief description})
```

If no files were written (e.g., review or analysis commands) → write `Output Artifacts: none (read-only)`.

## Next Command Suggestion

Suggest the logical next command based on workflow phase:

| Current command         | Suggest next                                  |
|-------------------------|-----------------------------------------------|
| /setup-ai-first         | `/define-product` to start your first feature |
| /define-product         | `/generate-prd {product-definition-file}`     |
| /generate-prd           | `/refine-prd {prd-file}` then `/review-context {prd-file}` |
| /refine-prd             | Open Review Board → update PRD → `/review-context {prd-file}` |
| /review-context (PRD)   | `/generate-bdd {prd-file}` if APPROVED; fix PRD if NEEDS_FIX |
| /generate-bdd           | `/review-context {feature-file}` to verify coverage |
| /review-context (BDD)   | `/generate-tech-docs {UC-ID}` if APPROVED; regenerate if NEEDS_FIX |
| /generate-tech-docs     | `/review-tech-docs {tech-design-file}`        |
| /review-tech-docs       | `/generate-code {feature-file}` if APPROVED; fix doc if NEEDS_FIX |
| /generate-code          | First gen → `/review-code {UC-ID}`; re-gen → `/generate-tests {UC-ID}` |
| /generate-tests         | `/run-tests {UC-ID}`                          |
| /run-tests (passing)    | `/review-code {UC-ID}`                        |
| /run-tests (failing)    | `/fix-bug {ticket-id}` or `/debug {error}`    |
| /review-code            | `/smoke-test {UC-ID}` or create PR            |
| /smoke-test             | Create PR and link to ticket                  |
| /validate-traces        | DRIFT/UNTRACKED → `/generate-code {UC-ID}`; GAP → `/generate-tests {UC-ID}`; all OK → create PR |
| /fix-bug                | Create PR and link to ticket                  |
| /debug                  | `/fix-bug {ticket-id}` if fix needed          |

Format the footer as:
```
---
Status : {badge}
{Output Artifacts block}
Next   : {suggested command with example arguments}
```
