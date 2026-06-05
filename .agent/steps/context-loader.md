# Context Loader — Load All Project Context

Execute these steps in order. Store everything in memory for the duration of the command session.

**Priority guide (anti-lost-in-middle):**
- Steps 1–2 are PROJECT-CONFIG — loaded first, resolve all paths and metadata.
- Step 3 is CRITICAL — architecture + coding standards, the highest-priority facts for generation.
- Step 4 is SAFETY — data protection rules, enforced silently for the entire session.
- Steps 5–6 are DOMAIN KNOWLEDGE — terminology and entity definitions.
- Step 7 is the WORKING MEMORY RECAP — locks critical facts into the top of working memory.

---

## Step 1 — [PROJECT-CONFIG] Load project-context.yaml

Read `.agent/project-context.yaml`. Extract and store:

**Tech Stack:**
- `tech_stack.language` → active language (e.g., Python 3.10, Python 3.11, Python 3.12)
- `tech_stack.framework` → active framework (e.g., FastAPI, Django, Flask)
- `tech_stack.build_tool` → build tool (e.g., Poetry, pip, pipenv)
- `tech_stack.test_framework` → test framework (e.g., pytest, unittest)
- `tech_stack.database` → database (e.g., PostgreSQL, MySQL, MongoDB, SQLite, Redis)
- `tech_stack.vector_database -> vector_database (e.g., Qdrant, Chromadb)
- `tech_stack.module` → active module profile (e.g., python-fastapi, python-kafka, python-django, context-engineering)

**Conventions:**
- `conventions.build_command` → how to compile/build
- `conventions.test_command` → how to run tests
- `conventions.service_run` → how to start the service
- `conventions.ticket_prefix` → ticket ID prefix (e.g., PROJ, FEAT, UC)

**Domains:**
- `domains` → list of active business domains

**Paths (if present):**
- `paths.specs_dir` → BDD specs root
- `paths.prd_dir` → PRD documents root
- `paths.refinement_dir` → findings/review output dir
- `paths.product_definitions_dir` → product definitions root
- `paths.domain_knowledge_dir` → domain knowledge root
- `paths.business_dictionary` → path to business-dictionary.md
- `paths.core_entities` → path to core-entities.md
- `paths.tech_docs_dir` → technical documentation root
- `paths.trace_dir` → trace state directory

If `paths` section is absent, use these defaults:
- `specs_dir` = `specs/bdd`
- `prd_dir` = `specs/prd`
- `refinement_dir` = `.agent/review`
- `product_definitions_dir` = `specs/product-definition`
- `domain_knowledge_dir` = `specs/domain-knowledge`
- `business_dictionary` = `specs/domain-knowledge/business-dictionary.md`
- `core_entities` = `specs/domain-knowledge/core-entities.md`
- `tech_docs_dir` = `specs/tech-docs`
- `trace_dir` = `.trace`

If `tech_stack.module` is set, also load `.agent/modules/{module}/stack-profile.yaml` if it exists.

---

## Step 2 — [PROJECT-CONFIG] Load module stack profile (conditional)

If `tech_stack.module` is set, read `.agent/modules/{module}/stack-profile.yaml`.
Merge framework-specific conventions (layer patterns, test patterns, naming rules) into the loaded context.
If the file does not exist → skip silently.

---

## Step 3 — [CRITICAL] Load CLAUDE.md

*This is the highest-priority context — it defines HOW to write code and documents for this project.*

Read `CLAUDE.md`. Extract and store:

- **§1 Project Overview** → project name, language, framework, build/test commands, domains
- **§2 Architecture** → layer order (e.g., Controller → Facade → Service → Repository), architectural rules
- **§3 Coding Standards** → naming conventions (classes, methods), response wrapper type, forbidden patterns
- **§5 Error Handling** → exception types, HTTP status code mapping, not-found exception class name
- **§7 Git Conventions** → branch naming pattern, commit message format

If `CLAUDE.md` does not exist → note it as missing and continue with project-context.yaml data only.

---

## Step 4 — [SAFETY] Load Data Protection Rules

Read `.agent/rules/data-protection.md` (or `rules/data-protection.md` from the framework installation).

Store the sensitive file patterns — you must **never** read, write, display, or reference content from files matching those patterns for the entire session.

If neither file exists → apply built-in defaults: never access `.env*`, `*.key`, `*.pem`, `*secret*`, `*password*`, `*credential*`.

---

## Step 5 — [DOMAIN] Load Business Dictionary (conditional)

Check if the business dictionary file exists (use `paths.business_dictionary` resolved in Step 1).

If it exists, read it and extract:
- **Canonical Terms** → complete list of approved terms and their definitions
- **Banned Terms** → complete list of banned terms and their canonical replacements
- **Status / Enum Registry** → allowed enum values per entity

Store the banned terms list for **active enforcement** throughout the command session:
- When generating any text (PRD, BDD, code comments, tech docs), verify no banned terms appear
- Replace banned terms with their canonical equivalents automatically

If the file does not exist → skip silently. Do not warn or block.

---

## Step 6 — [DOMAIN] Load Core Entities (conditional)

Check if the core entities file exists at `paths.core_entities` (resolved in Step 1).
Default path: `specs/domain-knowledge/core-entities.md`.

If it exists, read it and store:
- **Entity catalog** → for each entity: its name, purpose, owner service, key fields (name + type), business invariants, and relationships
- **Field name registry** → canonical field names to use in generated code and documents
- **Relationship map** → how entities relate to each other (1:N, N:N, embedded, etc.)

**How to use this catalog:**
- When generating code: use the field names, types, and relationships defined here — do NOT infer from existing code
- When generating PRD/BDD: reference entity names from this catalog for consistency
- When generating tech-docs: use this catalog as the source-of-truth for entity definitions

If the file does not exist → skip silently.

---

## Step 6.5 — [PLATFORM] Derive active_module and platform_type

Using `tech_stack.module` loaded in Step 1, derive and store two variables for use by all downstream commands:

```
active_module = tech_stack.module   (e.g. "python-fastapi", "python-kafka")
```

| `platform_type` | Modules |
|---|---|
| `backend` | `python-fastapi`, `python-kafka`, `context-engineering` |

If `tech_stack.module` is blank or not recognized → set `platform_type = "unknown"` and flag as ⚠️ in the Step 7 recap.

These two variables (`active_module`, `platform_type`) are the canonical source for all branching logic in commands that need platform-specific behavior (generate-tests, debug, fix-bug, smoke-test).

---

## Step 7 — [RECAP] Working Memory Recap (anti-lost-in-middle)

After loading all context, synthesize and output a compact summary block.
This recap ensures the most critical facts are stated at the END of context loading
(recency effect — freshest in working memory when the task begins).

Output exactly this block:
```
[CTX LOADED]
Stack     : {language} / {framework} / {database}
Platform  : {active_module} ({platform_type})
Layers    : {layer order from CLAUDE.md §2, e.g., Controller → Facade → Service → Repository}
Ticket    : {ticket_prefix}-
Dict      : {loaded — N canonical terms, M banned terms | missing}
Entities  : {loaded — EntityA, EntityB, EntityC | missing}
Status    : {FULL | PARTIAL — missing: CLAUDE.md / business-dict / core-entities | MINIMAL}
```

If any CRITICAL file is missing (CLAUDE.md), flag it clearly so the user can decide whether to proceed.

---

## Context Load Complete

After completing all steps, you have loaded:
- Project identity, tech stack, module conventions
- Architecture rules and layer order  ← **[CRITICAL — hold in working memory]**
- Coding standards and naming conventions  ← **[CRITICAL — hold in working memory]**
- Data protection rules (sensitive file patterns to never access)
- Terminology rules with banned-term list  ← **[DOMAIN — apply to every generated word]**
- Entity catalog (field names, types, invariants)  ← **[DOMAIN — use for code generation]**
- All configured paths

Proceed to the next step of the calling command.
