# Workflow Rules

> General AI behavior rules for all spec-driven-dev commands.
> Loaded by `steps/context-loader.md` at the start of every command.

---

## Checkpoints

- **Always** show a CHECKPOINT before making significant changes.
- A CHECKPOINT must include: what will be done, which files will be created/modified, estimated scope.
- Wait for explicit "Y" or user confirmation before proceeding.
- Exception: read-only analysis commands (`/review-code`, `/validate-traces`, `/debug`) may skip CHECKPOINT.

## Scope Control

- Work only within the scope explicitly confirmed at CHECKPOINT.
- Do NOT create files outside the directories specified in `project-context.yaml → paths`.
- If new scope is discovered mid-command, STOP and ask: "I found additional scope [{description}]. Should I include it? (Y/N)"

## Code Generation

- Never generate code for files not backed by a `.feature` spec (unless `/fix-bug` or `/debug`).
- Always add `@trace.implements` tags on controller-level methods.
- Never overwrite existing business logic without explicit confirmation.
- Build must pass before committing: run `{conventions.build_command}` and fix errors (max 3 retries).

## File Operations

- Prefer **editing** existing files over replacing them entirely.
- When creating new files, check if a similar file already exists first.
- Never delete files unless explicitly instructed.

## Communication

- Report in the language the user writes in (Vietnamese if user uses Vietnamese, English otherwise).
- Keep reports structured: status, artifacts created, next recommended command.
- If unsure about business intent, ask — do not guess and generate wrong spec.

## Error Handling

- If a tool call fails (file not found, build error, etc.), report the specific error clearly.
- Do NOT silently skip errors or pretend success.
- Suggest a concrete fix, not just "please check the error".
