# Gate — Universal Entry Procedure

Every command must execute this gate before proceeding with its specific logic.

## Step 0 — Sub-Agent Mode Check

Before anything else, check if `$ARGUMENTS` is a JSON payload from an orchestrator:

1. Attempt to parse `$ARGUMENTS` as JSON.
2. If it parses successfully **and** contains `"_agent_mode": true`:
   - **Skip Steps 1, 2, and 3 of this Gate entirely.**
   - Set target file = `payload.target_file`
   - Set loaded context = `payload.context` (do NOT run context-loader.md)
   - Set UC scope = `payload.uc_id` (process only this UC)
   - Set line range = `payload.uc_section` (read only that PRD section)
   - Proceed directly to the command-specific logic.
3. If `$ARGUMENTS` is not JSON or `_agent_mode` is absent → continue to Step 1 (normal mode).

## Step 0-B — Model Check

*Skip this step if `_agent_mode: true` (sub-agent — orchestrator already validated).*

Complex generation and review commands require strong reasoning.
Using a smaller model risks missed edge cases, incomplete spec analysis, and architecture violations.

Display and wait for response:

```
⚙️  MODEL CHECK
──────────────────────────────────────────────────────────────────
  Recommended  : claude-sonnet-4 (or latest sonnet model)
  Why needed   : Spec analysis, architecture review, code generation
                 require deep reasoning. Smaller models miss edge cases.

  To switch in Claude Code:
    • Settings → Model → select "claude-sonnet"
    • or: /model → choose claude-sonnet

  Running on claude-sonnet?
    Y — yes, on claude-sonnet → proceed
    S — skip check (I accept lower quality risk with current model)
──────────────────────────────────────────────────────────────────
```

- "Y" → proceed to Step 1.
- "S" → proceed to Step 1 (user accepts risk, add ⚠️ to final report).
- "N" or anything else → **STOP.** Output: "Please switch to claude-sonnet, then re-run this command."

## Step 1 — Resolve Target File

1. If `$ARGUMENTS` is provided and points to an existing file → use it directly as the target.
2. If `$ARGUMENTS` is a UC-ID, ticket ID, or partial name → search for matching files in the relevant directory.
3. If `$ARGUMENTS` is empty or no match found:
   - List files in the relevant directory for this command (e.g., `specs/prd/**/*.md` for PRD commands, `specs/bdd/**/*.feature` for BDD commands).
   - Present the list to the user and ask: "Which file do you want to work with? (Enter number or filename)"
   - Wait for user selection before continuing.

## Step 2 — Execute Context Loader

Load all project context by following the procedure in `steps/context-loader.md`.
Store all loaded context in memory for use throughout this command session.

## Step 3 — CHECKPOINT

After completing Steps 1 and 2, display a summary and wait for confirmation:

```
CHECKPOINT
-----------
Target     : {resolved file path}
Project    : {project.name from project-context.yaml}
Tech stack : {language} / {framework}
Module     : {module if set, else "not configured"}
Domains    : {comma-separated domain list}

Proceed? (Y/N)
```

Wait for explicit "Y" or "N" from the user before continuing.
- "Y" → proceed to the command-specific steps below.
- "N" → stop and ask what the user wants to change.
