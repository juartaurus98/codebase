# Sub-Agent Orchestration Pattern

Used by heavy commands when the target exceeds the complexity threshold.
The main session becomes a **lightweight orchestrator** — it only coordinates.
Each unit of work runs in its own sub-agent with a fresh context window.

---

## Complexity Thresholds

| Signal | Threshold | Action |
|--------|-----------|--------|
| UC count in PRD | > 3 UCs | spawn 1 agent per UC |
| PRD length | > 300 lines | spawn agents regardless of UC count |

If **either** threshold is exceeded → switch to orchestration mode.

---

## Orchestrator Steps (main session)

### Step A — Build slim context

Extract only what sub-agents need — do NOT pass full CLAUDE.md or full business-dictionary:

```json
{
  "project_name": "{project.name}",
  "tech_stack": {
    "language":       "{tech_stack.language}",
    "framework":      "{tech_stack.framework}",
    "build_tool":     "{tech_stack.build_tool}",
    "test_framework": "{tech_stack.test_framework}",
    "database":       "{tech_stack.database}",
    "module":         "{tech_stack.module}"
  },
  "conventions": {
    "build_command":  "{conventions.build_command}",
    "commit_format":  "{conventions.commit_format}"
  },
  "paths": {
    "specs_dir":     "{paths.specs_dir}",
    "prd_dir":       "{paths.prd_dir}",
    "trace_dir":     "{paths.trace_dir}",
    "tech_docs_dir": "{paths.tech_docs_dir}"
  },
  "architecture_summary": "<3-5 bullet points: layer order + key rules only>",
  "domains": ["{domain1}", "{domain2}"],
  "banned_terms": ["{term1}", "{term2}"]
}
```

### Step B — Extract UC list

Scan the target PRD for `#### {TICKET-ID}-UC{N}:` headings.
Build list: `[ { uc_id, uc_name, line_start, line_end } ]`

### Step C — Announce plan

```
High complexity detected — {N} UCs / {L} lines in {prd_file}
Spawning {N} sub-agents (1 per UC)...
  Agent 1 → {TICKET-ID}-UC1: {UC name}
  Agent 2 → {TICKET-ID}-UC2: {UC name}
  ...
```

### Step D — Spawn one sub-agent per UC

Build payload and invoke Agent tool for each UC:

```json
{
  "_agent_mode": true,
  "command":      "generate-bdd",
  "uc_id":        "{TICKET-ID}-UC{N}",
  "target_file":  "{absolute path to PRD or feature file}",
  "uc_section":   { "line_start": {N}, "line_end": {N} },
  "context":      { "<slim context from Step A>" }
}
```

> **Command scope**: Only `/generate-bdd` initiates orchestration mode. `/generate-code` and `/generate-tests` can run as sub-agents (they respect `_agent_mode: true` from Gate Step 0), but they do not spawn further sub-agents — their scope is already a single UC.

Serialize this JSON and pass as `$ARGUMENTS` when invoking the sub-agent command.

### Step E — Collect and merge results

Each sub-agent returns:
```json
{
  "uc_id":         "{TICKET-ID}-UC{N}",
  "files_created": ["path/to/file1", "path/to/file2"],
  "status":        "success | error",
  "errors":        []
}
```

Merge into a single report (follow report-footer.md format).
If any sub-agent errors → list them clearly and suggest re-run for that UC only.

---

## Sub-Agent Entry Point (called commands)

When `gate.md Step 0` detects `_agent_mode: true`:

1. Parse full payload from `$ARGUMENTS`
2. **Skip context-loader.md** — use `payload.context` directly
3. **Scope to `payload.uc_id` only** — do not process other UCs in the file
4. Read only the PRD section between `payload.uc_section.line_start` and `line_end`
5. Execute the command's normal logic for this single UC
6. Return structured result JSON (Step E format above)

---

## Context Window Savings

| Mode | What loads per session |
|------|------------------------|
| Single session (≤ 3 UC) | Full context + full PRD + all UCs |
| Orchestrator | Slim context + UC headings only |
| Each sub-agent | Slim context + **1 UC section only** |

The larger the PRD, the bigger the saving per sub-agent.
