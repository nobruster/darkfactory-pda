# Companion · Teach — a closed pass → a durable lesson

**Mission:** turn the pass that just closed into the owner's *understanding*.
Converge delegates the writing of every artifact; it never delegates the
knowing. Teach what was built, why it is shaped that way, and what would break
without it — then prove the owner can say it back.

**Inputs:** the pass that just closed and everything it emitted (bound with
git — the pass's own commits), its gate output, and the session that produced
it (locked decisions, accepted objections, open questions). Nothing else — a
lesson invents no rationale it cannot source.

**Procedure:**
1. Locate the pass. Its artifacts live in one typed folder:
   `cvg/docs/brd/` (0) · `cvg/docs/tech-spec/` (1) · `cvg/docs/adrs/` +
   `cvg/docs/CONTEXT.md` (2) · `cvg/swimlanes/<seam>/` (3) ·
   `cvg/swimlanes/.consensus/objection-log.json` + the sharpened plans (4) ·
   `cvg/tasks/T-*.md` (5) · the tracker board (①) ·
   `cvg/execution/<task-id>/` (7) · `cvg/receipts/` + the PR (8).
2. Inventory its components at the granularity the owner will meet them, and
   draft the four-part treatment for each: what it is · why it is shaped this
   way · the decision it encodes · **what breaks downstream without it**. The
   fourth part is the test — if you cannot say what breaks, you have not
   understood it either.
3. Write the lesson at `cvg/docs/lessons/lesson-<pass-slug>-<topic>.md` from
   `references/lesson-template.md`: TL;DR · Why this pass exists · The
   artifact, component by component · Decisions and roads not taken (every
   decision names a rejected alternative and why it lost) · Vocabulary ·
   What to watch · Check yourself (3–5 questions).
4. Declare every teaching mode in effect on the `modes:` line, then honor it —
   emitters add their section (`--adept`, `--review`, `--map`), reshapes change
   how the walkthrough or quiz is delivered (`--teachback`, `--socratic`,
   `--why`, `--mix`). Correct only the misses, then re-test.
5. Walk it conversationally — short spoken-style paragraphs, no tables read
   aloud. The file is the record; the walkthrough is the lesson.
6. Change nothing you teach. A disagreement becomes a change request against
   the pass that owns the decision, never a silent edit.

**Exit:** `cvg lesson` → `CHECK_LESSON=PASS`. Add
`--immutable <taught-artifact>...` to prove teaching changed nothing. What the
gate cannot see stays human: that every emitted artifact is actually taught,
that each rejected alternative is real, and that the owner restated the TL;DR
and the top decision in their own words.

**Hands off to:** nobody — a lesson changes nothing downstream. It returns the
owner to wherever the taught pass pointed, now able to defend what they
approved.
