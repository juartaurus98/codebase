# /setup-ai-first — Initialize Spec-Driven Dev in a Project

Walk the user through a one-time setup that creates all required directories, installs CLAUDE.md, and verifies the environment.

## Gate
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

This setup command runs on Claude Haiku 4.5 — fast and sufficient for directory scaffolding and config file creation.

Display and wait for response:

```
⚙️  MODEL CHECK
──────────────────────────────────────────────────────────────────
  Recommended  : claude-haiku-4-5 (Claude Haiku 4.5)
  Why needed   : Setup scaffolding and config generation — fast
                 and cost-effective; no deep reasoning required.

  To switch in Claude Code:
    • Settings → Model → select "claude-haiku-4-5"
    • or: /model → choose claude-haiku-4-5

  Running on claude-haiku-4-5?
    Y — yes, on claude-haiku-4-5 → proceed
    S — skip check (I'll use whichever model is active)
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


*Note: For this command — **skip Gate Steps 1, 2, and 3** (there is no input file and no project context yet). Only run Step 0-B (model check). The project root is the **current working directory**. Proceed directly to the Precondition Check below.*

---

## Precondition Check

Check if already set up:
- If `CLAUDE.md` **and** `.agent/project-context.yaml` both exist → ask: "This project is already initialized. Re-run setup to regenerate config files? (Y/N)"
  - N → stop
  - Y → continue (existing files will be preserved — each step will offer merge/skip)
- If only `specs/` exists or only partial setup detected → continue normally (safe to re-run)

## Step 1 — Create Directory Structure

Create these directories (skip if they exist):

```
{project-root}/
├── specs/
│   ├── product-definition/
│   ├── prd/
│   ├── bdd/
│   ├── tech-docs/            ← technical design documents
│   └── domain-knowledge/     ← business dictionary & domain context
├── .trace/
└── .agent/
    └── review/
```

## Step 2 — Create CLAUDE.md

Check if `CLAUDE.md` exists:
- Yes → ask "Merge template or skip?"
- No → create from the template below

After creating, instruct: "Open CLAUDE.md and fill in the `{{PLACEHOLDER}}` values with your project information. Python defaults are already pre-filled as comments — adjust if needed."

### CLAUDE.md Template

```
# §1. Project Overview
Project: {{PROJECT_NAME}}
Language: Python (3.11+)
Framework: {{FRAMEWORK}}  # e.g., FastAPI, Django, Flask
Build: {{BUILD_COMMAND}}  # e.g., poetry install
Test: {{TEST_COMMAND}}    # e.g., pytest or poetry run pytest
Domains: {{COMMA_SEPARATED_DOMAINS}}

# §2. Architecture
layers: "{{LAYER_STACK}}"
# Python example: Router → Service → Repository → Database
# Or: API Endpoint → Domain Service → Infrastructure/Repository
rules:
  - "Router endpoints must not contain business logic"
  - "Services own transaction boundaries and domain logic"
  - "Repositories abstract data access (Protocol-based)"
  - "Dependencies injected via FastAPI Depends or constructor"

# §3. Coding Standards
naming:
  classes: "PascalCase"  # e.g., EventService, OrderRepository
  methods: "snake_case"  # e.g., create_order(), get_by_id()
  modules: "snake_case"  # e.g., event_service.py, db.py
response_wrapper: "BaseResponse[T]"  # Pydantic generic wrapper
forbidden:
  - "Magic numbers — use named constants"
  - "Debug print statements"
  - "Mutable default arguments in function signatures"

# §4. Traceability
# Every router/endpoint method must be tagged:
# @trace.implements={UC-ID}-{SC-ID}
# @trace.source=specs/bdd/{domain}/{UC-ID}.feature  ← adjust if specs_dir differs in .agent/project-context.yaml
# Tests must be tagged:
# @trace.verifies={UC-ID}

# §5. Error Handling
not_found: "ResourceNotFoundError"  # Custom domain exception
http_codes: { get: 200, create: 201, not_found: 404, validation: 422 }

# §6. Build & Test
build_command: "poetry install"  # or: pip install -r requirements.txt
test_command: "poetry run pytest" # or: pytest
run_command: "poetry run uvicorn app.main:app --reload --port 8000"  # FastAPI example

# §7. Git Conventions
branch_feature: "feature/{{TICKET_PREFIX}}-{N}-{slug}"
commit_feature: "feat({{TICKET_PREFIX}}-{N}): {description}"
```

## Step 3 — Create project-context.yaml

Create `.agent/project-context.yaml` using `.agent/templates/project-context.yaml` as the source template.

Copy the template and instruct: "Open `.agent/project-context.yaml` and fill in all `{{PLACEHOLDER}}` values. For Python projects, use examples like:
  - language: Python 3.11
  - framework: FastAPI (or Django, Flask)
  - build_tool: Poetry (or pip, pdm)
  - test_framework: pytest
  - module: python-fastapi (or python-kafka, python-django)
The `paths` section is pre-configured with sensible defaults — adjust if your project uses different directory names."

## Step 4 — Create business-dictionary.md

Create `specs/domain-knowledge/business-dictionary.md` if it does not exist:

```markdown
# Business Dictionary — {{PROJECT_NAME}}

> Canonical terminology for this project. All PRDs, BDD specs, and code must follow these terms.
> Managed by: PO / SA team.

## Canonical Terms

| Canonical Term | Description / Context |
|----------------|----------------------|
| {Term}         | {Short description, usage scope} |

## Banned Terms

| ❌ Do NOT use | ✅ Use instead    | Reason |
|---------------|-------------------|--------|
| {banned}      | {canonical}       | {why}  |

## Status / Enum Registry

| Entity | Field   | Allowed Values (e.g.)     |
|--------|---------|--------------------|
| {Entity} | status | {value1, value2} |
```

Instruct: "Open `specs/domain-knowledge/business-dictionary.md` and add your project terminology. This file will be read by all commands to enforce consistent naming."

## Step 5 — Create core-entities.md

Create `specs/domain-knowledge/core-entities.md` if it does not exist:

```markdown
# Core Entities — {{PROJECT_NAME}}

> Machine-readable entity glossary for AI-assisted development.
> Loaded by all commands so AI knows your domain model without reading source code.
> Managed by: Tech Lead / Architect.
>
> HOW TO USE:
> - Add one `## Entity: {Name}` section per domain entity (aggregate root, value object, etc.)
> - Keep field descriptions concise — this is a REFERENCE, not API docs
> - Update this file whenever you add/rename fields or change business invariants

---

## Entity: {EntityName}

**Purpose**: {1-2 sentences — what this entity represents and why it exists in the domain}
**Domain**: {domain}
**Storage**: {e.g., `orders` table in PostgreSQL | `orders` collection in MongoDB}
**Owner service**: {service/module that owns this entity}

| Field        | Type    | Nullable | Description                         |
|--------------|---------|----------|-------------------------------------|
| id           | UUID    | No       | Primary key                         |
| {field_name} | {type}  | Yes/No   | {short description}                 |
| status       | Enum    | No       | See Status Registry in business-dictionary.md |

**Business invariants:**
- {Rule 1: e.g., "status can only transition: PENDING → ACTIVE → CLOSED"}
- {Rule 2: e.g., "total must equal sum of line items"}

**Relationships:**
- `{EntityA}` 1:N `{EntityB}` — {one sentence description}
- `{EntityA}` N:N `{EntityC}` via `{junction_table}` — {description}

---

## Entity: {AnotherEntity}

*(Add more entities following the same pattern above)*
```

Instruct: "Open `specs/domain-knowledge/core-entities.md` and define your key domain entities. Start with aggregate roots. This file is loaded by every AI command — good definitions here save significant back-and-forth during code generation."

## Step 6 — Install VS Code Extension (Recommended)

Recommend the user install the **Spec Driven Dev** VS Code extension — it provides Review Board + Living Documentation panels that integrate with this workflow.

```bash
code --install-extension edupia-team.spec-driven-dev-team
```

Or: VS Code → `Ctrl+Shift+P` → **"Extensions: Install from Marketplace"** → search **Spec Driven Dev**.

**What it does:**
- 📋 **Review Board** — visual UI to review findings from `/refine-prd`, `/review-context`, `/review-tech-docs`
- 📊 **Living Documentation** — traceability dashboard driven by `.trace/*.tsv`

## Step 7 — Verify

- [ ] `specs/` exists
- [ ] `specs/bdd/` exists
- [ ] `specs/tech-docs/` exists
- [ ] `specs/domain-knowledge/` exists
- [ ] `.trace/` exists
- [ ] `.agent/project-context.yaml` exists
- [ ] `CLAUDE.md` exists
- [ ] `specs/domain-knowledge/business-dictionary.md` exists
- [ ] `specs/domain-knowledge/core-entities.md` exists

## Output

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


```
/setup-ai-first Complete ✅
Next:
  1. Fill CLAUDE.md (replace {{PLACEHOLDER}} values)
  2. Fill .agent/project-context.yaml
  3. Fill specs/domain-knowledge/business-dictionary.md  ← terminology rules
  4. Fill specs/domain-knowledge/core-entities.md        ← entity glossary for code gen
  5. git add and commit those 4 files
  6. Install VS Code extension (if not yet installed):
     code --install-extension edupia-team.spec-driven-dev-team
  7. /define-product to start your first feature
```
