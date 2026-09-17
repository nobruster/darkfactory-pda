# The Brief-Spec design theory

Brief-Spec is a presentation contract for human–agent work. Its purpose is not to
make agents think alike or to turn every response into the same prose. Its
purpose is to make the handoff predictable enough that the reader can find the
outcome, required action, evidence, and uncertainty without reconstructing a new
information hierarchy on every turn.

This document explains the theory behind that choice, the boundary between
research and product inference, and the reasons Brief-Spec is deliberately not a
second brain.

## The problem is re-parsing, not only reading

The reading cost of an agent response is not determined by word count alone.
Readers also spend attention discovering:

- what kind of response they received,
- where the terminal result is located,
- whether a recommendation is completed work or planned work,
- which claim is tied to which test or artifact,
- what requires human action,
- and which caveats change the decision.

When several agents use different structures, that discovery cost repeats. A
well-written response can therefore remain operationally expensive.

Brief-Spec's theory of change is:

```text
stable schema
  → faster recognition of information roles
  → less structural search and mental integration
  → more attention available for judgment
```

This is a design hypothesis informed by cognitive science and usability
research. It is not a claim that the complete Brief-Spec interaction has already
been validated in a controlled human-subject study.

## 1. Schema consistency: keep the slots stable

In cognitive-load theory, schemas are organized structures that let several
related elements be treated as a meaningful unit. Sweller argued that
domain-specific schemas are central to the difference between expert and novice
problem solving, and that processing demands can compete with schema
acquisition.[^sweller]

Brief-Spec applies that principle conservatively. It does not claim that seven
Markdown headings automatically create a cognitive schema. It keeps the
information roles and their order stable:

```text
Status → Outcome → Human action → Proof → Gaps → Next → Open
```

After repeated exposure, the user no longer needs to search for where a
particular agent placed the caveat or next action. The position itself becomes
a cue.

W3C cognitive-accessibility guidance similarly recommends clear hierarchy,
logical sections, descriptive headings, and consistent positioning. It notes
that a standard layout can help users rely on recognition and learned
patterns.[^w3c-structure]

### Product consequence

The field order is part of the contract, not a writing suggestion. The
validator rejects missing or reordered fields. Agents remain free to provide
their normal explanation before the bounded brief.

## 2. Progressive disclosure: importance before completeness

A system can preserve detail without presenting every detail at the same level.
Progressive disclosure initially exposes the most frequently needed material
and keeps secondary material available on request.[^progressive-disclosure]

Brief-Spec uses three layers:

1. **Immediate orientation** — status, outcome, and human action.
2. **Decision support** — proof, gaps, next actions, and open questions.
3. **Authoritative detail** — repository files, commands, tests, logs, URLs, and
   artifacts referenced by the brief.

The layers are not levels of truth. The brief does not become authoritative
because it is easier to read. Each layer remains connected to the one beneath
it.

Chandler and Sweller's experiments on split-source instructional material
showed that requiring people to mentally integrate mutually referring sources
can impose additional cognitive load. Integrated material helped when those
sources could not be understood independently; redundant explanation could
also be harmful.[^chandler-sweller]

Brief-Spec uses that finding as a design direction:

- place a claim and its compact proof reference together,
- avoid copying an entire log into the handoff,
- and avoid commentary that repeats information without changing the decision.

It does not imply that all detail should be collapsed into one card.

## 3. Recognition over recall: make roles and states visible

Recognition has more contextual cues than free recall. In interface design,
visible options, stable labels, and recent history can help users retrieve what
they need without generating it from memory.[^recognition-recall]

Brief-Spec turns several recall questions into recognition tasks:

| Recall-heavy question | Brief-Spec cue |
| --- | --- |
| “Was this finished or merely proposed?” | `DONE`, `REVIEW`, `DECIDE`, `BLOCKED`, or `FAILED` |
| “Did the agent need something from me?” | `Human action` in a fixed position |
| “Where was the test evidence?” | `Proof` immediately after the result |
| “What did we decide before the interruption?” | `Decisions` in an Orient checkpoint |
| “Was that caveat resolved?” | Explicit `Gaps` and `Open` fields |

The five status words are deliberately concrete:

- `DONE` — the requested outcome is achieved and directly verified.
- `REVIEW` — the implementation is ready for human inspection.
- `DECIDE` — a meaningful choice is required before proceeding.
- `BLOCKED` — an external condition prevents progress toward the active
  objective.
- `FAILED` — the attempted route did not achieve the objective.

The labels do not determine truth. The evidence contract and validator constrain
how they may be used.

## 4. Working-memory load: externalize the handoff

Working memory is limited. Cowan's review argues that the focus of attention is
often limited to roughly four chunks under controlled conditions, while also
emphasizing that chunk size and task conditions matter.[^cowan]

Brief-Spec does **not** convert “four” into a universal interface budget. It uses
the broader constraint:

- do not require the reader to retain a result from paragraph one while
  searching paragraph twelve for its caveat,
- keep active obligations small and labeled,
- distinguish completed work from planned work,
- and externalize proof locations instead of asking the reader to remember
  them.

The list limits in the Outcome Brief—five proof references, three next actions,
and three open items—are product constraints for scanability, not claims of
psychological constants. When more material exists, the brief links to it.

## 5. Safe-boundary checkpoints: eligibility is not delivery

An automatic recap can itself become an interruption. Brief-Spec therefore
separates two decisions:

1. **Eligibility** — has the session become long or dense enough that a
   checkpoint could help?
2. **Delivery** — has the host reached a boundary where a checkpoint will not
   interrupt active work?

Eligibility can come from elapsed time, turn count, assistant volume, tool-call
count, a user request, or pre-compaction. Cooldown and minimum-turn rules
suppress repetition.

Delivery occurs through available lifecycle boundaries. Brief-Spec does not
inject a timer-driven message in the middle of a tool call.

This boundary policy is grounded in interruption research:

- Altmann and Trafton's memory-for-goals model describes suspended-goal
  retrieval in terms of activation, interference, and associative
  cues.[^altmann-trafton]
- Monk, Boehm-Davis, and Trafton found that interruption timing affected task
  resumption and that the middle of a task was more costly than a task
  boundary.[^monk]
- Bailey and Konstan measured interruption effects on completion time, errors,
  annoyance, and anxiety, and compared interruptions delivered during versus
  between task execution.[^bailey-konstan]
- Czerwinski, Horvitz, and Wilhite's field study documented the difficulty
  information workers experience when interleaving complex tasks and recovering
  from interruptions.[^czerwinski]

These studies did not test Brief-Spec or modern coding-agent conversations.
Brief-Spec treats their results as a strong reason to prefer boundaries and
retrieval cues over arbitrary timed interruption.

## 6. One state, three checkpoint renderings

`session-checkpoint` does not create three different histories. It renders the
same bounded state for different human needs.

### Orient

Optimized for operational re-entry:

- where the work stands,
- what completed,
- what was decided,
- what proves it,
- and the next useful move.

### Teach

Optimized for mental-model formation:

- the core idea,
- why it matters,
- what changed,
- one concrete example,
- watch-outs,
- and the next move.

Teach mode is not permission to invent an analogy that obscures the actual
implementation. It remains attached to proof.

### Spoken Brief

Optimized for sequential listening:

- short sentences,
- audible transitions,
- expanded abbreviations when helpful,
- no tables or code fences in the script,
- and dense paths moved to a screen-only proof field.

Speech is not a visual card read verbatim. W3C's Speech Synthesis Markup
Language standard exists because speech rendering has modality-specific needs
such as pronunciation, phrasing, emphasis, and timing.[^ssml] Brief-Spec v0.1
produces speech-oriented text; it does not itself synthesize audio or claim a
measured listening-speed improvement.

## 7. Evidence preservation: compression must not erase epistemic state

Short summaries often collapse important boundaries:

- implemented versus planned,
- local versus published,
- a process exit code versus a user-visible outcome,
- structural validation versus live service behavior,
- direct observation versus a report from another system.

Brief-Spec requires inspectable proof and explicit gaps so that compression does
not silently upgrade a claim.

The evidence schema distinguishes:

- **kind** — file, command, test, commit, URL, pull request, issue, artifact, or
  observation;
- **locator** — where the evidence can be inspected;
- **basis** — direct, derived, or reported;
- **result** — pass, fail, or informational;
- **revision** and **observation time** when relevant.

The model is informed by provenance practice, including the W3C PROV family,
which defines portable concepts for representing the origins and transformations
of information across heterogeneous systems.[^prov]

Brief-Spec does not currently claim full PROV compliance. Its narrower invariant
is:

> A presentation artifact must not become more authoritative than the evidence
> it represents.

## 8. Outcome validation: formatting is not proof

The validator enforces structural and semantic consistency:

- required fields exist and stay in order,
- status belongs to the fixed vocabulary,
- proof is non-empty,
- terminal statuses satisfy their action and gap rules,
- and list sizes remain bounded.

It cannot determine whether a referenced test actually ran or whether a human
should trust the implementation. Validation proves that the handoff satisfies
the Brief-Spec contract, not that the underlying work is correct.

That distinction is why the preferred wording is “contract validation,” not
“truth validation.”

## 9. Repair once, then fail open

When policy is `enforce` or `auto`, a stop hook may request one corrective pass
if a required outcome or checkpoint is missing. The next stop is allowed even
if the response remains invalid.

This rule protects both sides of the interaction:

- the user gets one opportunity for a consistently shaped handoff,
- the host cannot be trapped in an infinite formatting loop.

Other hook errors fail open. Brief-Spec records a diagnostic and returns an empty
decision. A presentation layer should not make the underlying engineering tool
unusable because its own state is corrupt or a host payload changes.

## 10. Privacy and bounded operational state

Brief-Spec needs limited state to count turns, apply cooldowns, deduplicate
events, and prevent repeated repair. It stores:

- timestamps,
- counters,
- pending checkpoint reasons,
- the selected mode,
- repair state,
- and recent event hashes.

It does not store raw prompts, tool results, or complete transcripts in session
state. If a stop event provides a transcript path, Brief-Spec reads only the
bounded tail needed to locate the last assistant message, rejects symlinks, and
does not copy the transcript into its state.

Files are written atomically with private permissions. The hook input is bounded
to 1 MiB. Project-scoped Copilot integration uses a self-contained zipapp and
does not send job content to a Brief-Spec service.

These are implementation invariants, not a promise that host platforms
themselves retain no data.

## 11. Why Brief-Spec is not a second brain

A second brain is responsible for durable knowledge capture, retrieval,
relationships, and maintenance over time. Brief-Spec is responsible for the
shape of a current human handoff.

| Responsibility | Brief-Spec | Knowledge system |
| --- | --- | --- |
| Stable end-of-task presentation | Yes | Optional |
| Safe-boundary session orientation | Yes | Optional |
| Validate the brief's structure | Yes | Optional |
| Preserve proof locators | Yes | Yes |
| Canonical project truth | No | Sometimes |
| Long-term semantic retrieval | No | Yes |
| Automatic transcript ingestion | No | Sometimes |
| Knowledge lifecycle and forgetting | No | Yes |
| Decision approval | No | No; remains human |

The intended flow is:

```text
authoritative work
  → bounded Brief-Spec view
  → human judgment
  → optional explicit promotion into a knowledge system
```

Automatic ingestion would blur a critical boundary. A concise rendering may
omit context by design; treating it as canonical memory would turn a
presentation choice into a knowledge claim.

The optional Project Chronicle does not remove this boundary. It records only explicitly enabled,
bounded material events and labels its ledger as an observation history. Its relation index is
derived, its reports cite source event IDs, and any durable lesson leaves Brief-Spec only as a
human-approved proposal. Raw conversations and automatic knowledge promotion remain excluded.

## 12. What would falsify the design

Brief-Spec should be evaluated as a tool, not protected as an ideology. Useful
product tests include:

- time to identify the true outcome,
- time to identify required human action,
- accuracy when distinguishing completed from planned work,
- success resuming a session after an interruption,
- ability to locate supporting evidence,
- perceived effort,
- checkpoint dismissal or annoyance rate,
- and false confidence caused by compression.

The design would need revision if stable cards make people inspect evidence
less often, if automatic checkpoints create more disruption than they prevent,
if the fixed vocabulary cannot express important engineering states, or if the
contract adds enough boilerplate to obscure the underlying answer.

Threshold defaults should therefore remain configurable, and automated
checkpoints should be compared with manual invocation in real workflows.

## Design principles in one page

1. **Standardize information roles, not reasoning style.**
2. **Lead with outcome and human action.**
3. **Keep proof adjacent and inspectable.**
4. **State gaps instead of smoothing them away.**
5. **Use time as eligibility, never as permission to interrupt.**
6. **Render visual, teaching, and spoken forms from the same bounded state.**
7. **Validate the contract without claiming to validate truth.**
8. **Attempt one repair, then allow the host to finish.**
9. **Store operational counters, not another copy of the conversation.**
10. **Keep authoritative work outside the presentation layer.**

## References

[^sweller]: John Sweller, “Cognitive Load During Problem Solving: Effects on
    Learning,” *Cognitive Science* 12(2), 1988.
    [DOI](https://doi.org/10.1207/s15516709cog1202_4)

[^chandler-sweller]: Paul Chandler and John Sweller, “Cognitive Load Theory and
    the Format of Instruction,” *Cognition and Instruction* 8(4), 1991.
    [DOI](https://doi.org/10.1207/s1532690xci0804_2)

[^cowan]: Nelson Cowan, “The Magical Number 4 in Short-Term Memory: A
    Reconsideration of Mental Storage Capacity,” *Behavioral and Brain
    Sciences* 24(1), 2001.
    [PubMed](https://pubmed.ncbi.nlm.nih.gov/11515286/)

[^recognition-recall]: Raluca Budiu, “Memory Recognition and Recall in User
    Interfaces,” Nielsen Norman Group, updated 2024.
    [Article](https://www.nngroup.com/articles/recognition-and-recall/)

[^progressive-disclosure]: Jakob Nielsen, “Progressive Disclosure,” Nielsen
    Norman Group, 2006.
    [Article](https://www.nngroup.com/articles/progressive-disclosure/)

[^w3c-structure]: W3C Web Accessibility Initiative, “Use a Clear and
    Understandable Page Structure,” *Making Content Usable for People with
    Cognitive and Learning Disabilities*.
    [Design pattern](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o2p03-page-structure/)

[^altmann-trafton]: Erik M. Altmann and J. Gregory Trafton, “Memory for Goals:
    An Activation-Based Model,” *Cognitive Science* 26(1), 2002.
    [DOI](https://doi.org/10.1207/s15516709cog2601_2)

[^monk]: Christopher A. Monk, Deborah A. Boehm-Davis, and J. Gregory Trafton,
    “Recovering From Interruptions: Implications for Driver Distraction
    Research,” *Human Factors* 46(4), 2004.
    [DOI](https://doi.org/10.1518/hfes.46.4.650.56816)

[^bailey-konstan]: Brian P. Bailey and Joseph A. Konstan, “On the Need for
    Attention-Aware Systems: Measuring Effects of Interruption on Task
    Performance, Error Rate, and Affective State,” *Computers in Human
    Behavior* 22(4), 2006.
    [DOI](https://doi.org/10.1016/j.chb.2005.12.009)

[^czerwinski]: Mary Czerwinski, Eric Horvitz, and Susan Wilhite, “A Diary Study
    of Task Switching and Interruptions,” *CHI 2004*.
    [Microsoft Research paper](https://www.microsoft.com/en-us/research/publication/a-diary-study-of-task-switching-and-interruptions/)

[^prov]: W3C, “PROV-O: The PROV Ontology,” Recommendation, 2013.
    [Specification](https://www.w3.org/TR/prov-o/)

[^ssml]: W3C, “Speech Synthesis Markup Language (SSML) Version 1.1,”
    Recommendation, 2010.
    [Specification](https://www.w3.org/TR/speech-synthesis11/)
