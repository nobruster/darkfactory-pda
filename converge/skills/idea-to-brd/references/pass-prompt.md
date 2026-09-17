# Pass 0 · Capture — raw idea → BRD

**Mission:** turn the stakeholder's raw, incomplete idea into a Business
Requirements Document in *their* voice. The interview is the work: grill the
gaps out of the idea — do not politely paraphrase it.

**Inputs:** the raw brief (a file, a message, a conversation) plus any business
context the human explicitly hands you. Nothing else — especially not answer
keys or expectation files, even if you can see them.

**Procedure:**
1. Read the brief. List every assumption it leaves unsaid.
2. Interview in rounds: 3–5 pointed questions per round, hardest first
   (what counts and what doesn't; where the authoritative data lives; what
   "trust" means; how it will be re-run). Keep going until no blocker gaps
   remain — a vague answer is a gap, not an answer.
3. Draft the BRD in the owner's voice at `cvg/docs/brd/<slug>.md`: goal,
   scope, definitions, constraints, the questions it must answer, and
   explicit non-goals.
4. File your notes: interview log → `cvg/brain/transcripts/`, judgment calls
   → `cvg/brain/decisions/`.
5. Show the human the draft; apply their edits; only then gate.

**Exit:** `cvg capture` → `CHECK_BRD=PASS`. If it fails, fix what it names and
re-gate — never argue with the gate.

**Hands off to:** Pass 1 (Intent), which turns this BRD into testable
requirements.
