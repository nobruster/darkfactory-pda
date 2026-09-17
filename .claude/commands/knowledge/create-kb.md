---
name: create-kb
description: |
  Create a complete Knowledge Base domain from scratch using the kb-architect agent
  with MCP validation, or audit existing KB health.
---

# Create Knowledge Base Command

> Create a complete KB section from scratch with MCP validation.

## Usage

```bash
/create-kb <DOMAIN>
/create-kb --audit
```

**Examples**: `/create-kb redis`, `/create-kb pandas`, `/create-kb authentication`

## What Happens

1. **Validates prerequisites** — checks `.claude/kb/_templates/` exist
2. **Checks for conflicts** — if domain already exists, asks before overwriting
3. **Invokes kb-architect agent** — executes full workflow:
   - Researches domain via MCP (Context7 + Exa)
   - Creates `index.md`, `quick-reference.md`
   - Creates `concepts/` with atomic definition files
   - Creates `patterns/` with reusable code patterns
   - Validates against KB templates
4. **Reports completion** — shows quality score and files created

## Options

| Command | Action |
|---------|--------|
| `/create-kb <domain>` | Create new KB domain from scratch |
| `/create-kb --audit` | Audit all existing KB domains for health, completeness, and template compliance |

### Audit Mode

When run with `--audit`, the kb-architect will:
- Scan all directories under `.claude/kb/`
- Check each domain for required files (`index.md`, `quick-reference.md`)
- Verify concepts and patterns follow templates
- Report a health score per domain
- Suggest improvements for low-scoring domains

## Output Format

```text
KB CREATION: <domain>
============================
Status: COMPLETE
Files created: N
Quality score: X/10

Created:
  .claude/kb/<domain>/index.md
  .claude/kb/<domain>/quick-reference.md
  .claude/kb/<domain>/concepts/<concept-1>.md
  .claude/kb/<domain>/concepts/<concept-2>.md
  .claude/kb/<domain>/patterns/<pattern-1>.md
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Domain already exists | Ask user: overwrite, merge, or cancel |
| Templates missing | Error with: "Run from repo root. Check .claude/kb/_templates/ exists" |
| MCP unavailable | Proceed with KB-only mode, note in output |
| kb-architect agent fails | Report error, suggest manual creation using templates |

## See Also

- **Agent**: `.claude/agents/exploration/kb-architect.md`
- **Example KB**: `.claude/kb/pydantic/` (well-structured reference)
- **Templates**: `.claude/kb/_templates/`
