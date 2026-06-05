# Context Engineering — Design Templates and Patterns

## System Context Design Template

```markdown
# System Context: {Agent Name}

## Role
You are {role description}. You help {target user} to {primary purpose}.

## Scope
In scope:
- {capability 1}
- {capability 2}

Out of scope (do not attempt):
- {excluded capability 1}
- {excluded capability 2}

## Output Format
Always respond with:
- {format requirement 1, e.g., "structured YAML when producing artifacts"}
- {format requirement 2, e.g., "numbered steps for procedural instructions"}
- {format requirement 3, e.g., "a CHECKPOINT before any destructive action"}

## Constraints
- {constraint 1, e.g., "Never make changes without explicit user confirmation"}
- {constraint 2, e.g., "Always cite source files when referencing code"}

## Tools Available
- {tool name}: {what it does and when to use it}
```

## Context Layering: Persistent vs Ephemeral

```
┌─────────────────────────────────────────────────┐
│  PERSISTENT (system prompt — stable, pre-loaded) │
│  - Role and persona                              │
│  - Output format requirements                    │
│  - Constraint rules                              │
│  - Domain knowledge (project context)            │
└────────────────────┬────────────────────────────┘
                     │ passed once at session start
┌────────────────────▼────────────────────────────┐
│  SESSION (loaded once per task)                  │
│  - Project-context.yaml                          │
│  - CLAUDE.md                                     │
│  - Business dictionary                           │
└────────────────────┬────────────────────────────┘
                     │ loaded on demand
┌────────────────────▼────────────────────────────┐
│  EPHEMERAL (per-turn, discarded after use)       │
│  - Tool results                                  │
│  - File contents read mid-task                   │
│  - User clarification answers                    │
└─────────────────────────────────────────────────┘
```

## Context Handoff Between Agents

When passing work from one agent to another, include a structured handoff payload:

```yaml
# Agent Handoff Payload
handoff_from: "{source agent name}"
handoff_to: "{target agent name}"
task_id: "{unique task identifier}"
status: "partial_complete"  # pending | partial_complete | blocked | ready_for_review

# What was accomplished
completed:
  - "{step 1 done}"
  - "{step 2 done}"

# What the next agent must do
pending:
  - "{step 3 to do}"
  - "{step 4 to do}"

# Decisions made (so next agent doesn't re-litigate)
decisions:
  - decision: "{what was decided}"
    rationale: "{why}"

# Artifacts produced (file paths)
artifacts:
  - path: "{file path}"
    type: "{type: spec | code | test | report}"
    status: "{draft | approved | final}"

# Context the next agent needs immediately
context_snapshot:
  project_name: "{name}"
  domain: "{domain}"
  uc_id: "{UC-ID}"
  tech_stack: "{stack}"
```

## Context Compression Pattern

When conversation history grows large, compress before the next turn:

```
CONTEXT SUMMARY (replaces N previous turns):
Task: {what we are doing}
Progress: {what has been completed so far}
Current state: {where we are now}
Key decisions: {decisions that must not be reversed}
Pending: {what still needs to be done}
Files produced: {list of artifact paths}
```

Compression rules:
1. Keep all decisions and their rationale.
2. Keep all file paths that were created.
3. Drop intermediate reasoning that led to a confirmed decision.
4. Keep any user corrections or explicit preferences.
5. Keep any open questions that are still unresolved.
