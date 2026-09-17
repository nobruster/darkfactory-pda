---
name: meeting
description: |
  Fetch meeting data from Krisp MCP and generate structured notes using
  the meeting-analyst agent. Extracts backlog items to tasks/ folder.
---

# /meeting Command

> Fetch meeting data from Krisp MCP, analyze with meeting-analyst, and extract backlog tasks.

## Usage

```bash
/meeting                        # List recent meetings, pick one
/meeting "sprint review"        # Search by text query
/meeting <32-char-hex-id>       # Fetch specific meeting by document ID
/meeting --action-items         # List open action items only
```

---

## How It Works

```text
KRISP MCP ──> /meeting command ──> meeting-analyst agent ──> outputs
                                         |
                            ┌────────────┴────────────┐
                            v                         v
                   notes/MEETING_*.md          tasks/TASK_*.md
                   (10-section analysis)       (backlog items)
```

---

## Execution Instructions

When this command is invoked, follow these steps precisely:

### Step 1: Resolve Input

Parse the user's argument to determine the fetch strategy:

| Input | Strategy |
|-------|----------|
| No argument | Call Krisp MCP `search_meetings` with no query to get recent meetings. Present a numbered list and let the user pick. |
| Text in quotes | Call Krisp MCP `search_meetings` with the text as query. If single result, proceed. If multiple, present list. |
| 32-char hex string | This is a document ID. Call `get_document` to fetch the full transcript, and `search_meetings` with the ID for metadata. |
| `--action-items` | Call Krisp MCP `get_action_items` with `completed=false`. Format as a checklist and optionally generate TASK files. Skip meeting-analyst. |

**Important:** Document IDs in Krisp are 32-character lowercase hex strings (UUID without dashes).

### Step 2: Fetch Meeting Data

Once a meeting is selected:

1. Call `search_meetings` to get metadata (title, date, duration, attendees, summary, key points, action items)
2. Call `get_document` with the meeting's document ID to get the full transcript (if available)
3. Call `get_current_datetime` to get the current date for file naming

Compose all fetched data into a single raw meeting data block.

### Step 3: Invoke Meeting-Analyst

Launch the `meeting-analyst` agent to process the raw data:

```
Agent(
  subagent_type: "meeting-analyst",
  prompt: """
    Analyze the following meeting data using your 10-section extraction framework.

    MEETING DATA:
    {raw meeting data from Step 2}

    Apply ALL 10 sections:
    1. Key Decisions
    2. Action Items (with owners and dates)
    3. Requirements (FR/NFR with IDs)
    4. Blockers & Risks
    5. Architecture & Technical Decisions
    6. Open Questions
    7. Next Steps & Timeline
    8. Implicit Signals & Sentiment
    9. Stakeholders & Roles
    10. Metrics & Success Criteria

    Output in the Single Meeting Analysis template format.
    Mark sections as N/A if no relevant content found.
  """
)
```

### Step 4: Save Meeting Notes

Write the meeting-analyst output to:

```
notes/MEETING_{YYYY-MM-DD}_{slug}.md
```

Where `{slug}` is derived from the meeting title (lowercase, hyphens, no special chars).

Use this header format:

```markdown
# MEETING: {Title} — Analysis

> **Date:** {date} | **Duration:** {duration} | **Attendees:** {count}
> **Source:** Krisp MCP | **Meeting ID:** {id}
> **Analyzed:** {current timestamp}

{meeting-analyst output here}
```

### Step 5: Extract Backlog Items

Parse the meeting-analyst output and identify engineering-actionable items:

- **Action items** that involve coding, infrastructure, or technical work
- **Requirements** (FR/NFR) that need implementation
- **Architecture decisions** that require code changes
- **Blockers** that need technical resolution

For each actionable cluster (group related items), create a TASK file:

```
tasks/TASK_{YYYY-MM-DD}_{slug}.md
```

### TASK File Template

```markdown
# TASK: {SLUG}

> Extracted from: notes/MEETING_{date}_{meeting-slug}.md
> Created: {timestamp}
> Status: PENDING_VALIDATION

## Summary

{1-2 sentence description of what needs to be done}

## Source Context

- **Meeting:** {meeting title}
- **Date:** {meeting date}
- **Section:** {which section of meeting notes this came from}

## Requirements

- FR-1: {specific, testable requirement}
- FR-2: {specific, testable requirement}

## Suggested Priority

{RISKY | CORE | POLISH} — {reasoning based on urgency, dependencies, risk}

## Suggested Agents

| Component | Agent | Reasoning |
|-----------|-------|-----------|
| {component} | @{agent-name} | {why this agent fits} |

## Dependencies

- {dependency on other tasks, external systems, or decisions}

## Raw Quotes

> {relevant quotes from the meeting transcript that support this task}
```

**Rules for TASK extraction:**

- Only extract items that require engineering work (skip pure business/process items)
- Group related items into a single TASK (e.g., "add auth endpoint" + "write auth tests" = one TASK)
- Include raw quotes for traceability back to the meeting
- Set Status to `PENDING_VALIDATION` (the overnight orchestrator handles promotion)
- If no engineering-actionable items found, skip TASK creation and inform the user

### Step 6: Report to User

After all files are written, present a summary:

```text
MEETING PROCESSED
=================
Notes: notes/MEETING_{date}_{slug}.md
  - {count} decisions
  - {count} action items
  - {count} requirements

Tasks extracted: {count}
  - tasks/TASK_{date}_{slug-1}.md — {summary}
  - tasks/TASK_{date}_{slug-2}.md — {summary}

All tasks have Status: PENDING_VALIDATION
```

---

## Krisp MCP Tools Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `search_meetings` | Search by text or meeting ID | Returns metadata, summaries, key points, action items |
| `get_document` | Fetch full transcript by 32-char hex ID | Returns complete meeting document |
| `get_action_items` | List action items | Filter by completion status, assignee |
| `get_current_datetime` | Get current date/time | Use instead of guessing dates |

---

## Error Handling

| Error | Recovery |
|-------|----------|
| Krisp MCP not connected | Tell user to run `/mcp` and add Krisp (URL: `https://mcp.krisp.ai/mcp`) |
| OAuth expired | Tell user to reconnect Krisp MCP via `/mcp` |
| No meetings found | Inform user, suggest broader search terms |
| Meeting has no transcript | Proceed with metadata/summary only, note in output |
| No actionable items found | Write notes file, skip TASK creation, inform user |

---

## Examples

### Example 1: Search and Analyze

```text
User: /meeting "sprint review"

→ Searching Krisp for "sprint review"...
→ Found: "Sprint Review — March 25" (45 min, 6 attendees)
→ Fetching transcript...
→ Invoking meeting-analyst...

MEETING PROCESSED
=================
Notes: notes/MEETING_2026-03-25_sprint-review.md
  - 3 decisions
  - 7 action items
  - 4 requirements

Tasks extracted: 2
  - tasks/TASK_2026-03-25_add-redis-cache.md — Implement Redis caching layer for API
  - tasks/TASK_2026-03-25_fix-auth-timeout.md — Fix authentication timeout bug
```

### Example 2: Browse Recent

```text
User: /meeting

→ Fetching recent meetings from Krisp...

Recent Meetings:
1. Sprint Review — March 25 (45 min)
2. Architecture Discussion — March 24 (60 min)
3. 1:1 with Tech Lead — March 23 (30 min)

Which meeting? (enter number or ID)
```

### Example 3: Action Items Only

```text
User: /meeting --action-items

→ Fetching open action items from Krisp...

Open Action Items:
- [ ] @alice: Migrate to new auth provider (Due: March 28)
- [ ] @bob: Write load test scripts (Due: March 27)
- [ ] @charlie: Review PR #456 (Due: March 26)

Generate TASK files for these? (y/n)
```

---

## See Also

| Resource | Path |
|----------|------|
| Meeting Analyst Agent | `.claude/agents/communication/meeting-analyst.md` |
| TASK files consumed by | Plan 2: Overnight Orchestrator (future) |
| Krisp MCP docs | `https://help.krisp.ai/hc/en-us/articles/25396920405148-Krisp-MCP` |
