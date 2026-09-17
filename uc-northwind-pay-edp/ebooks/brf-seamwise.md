# SEAMWISE — definitive deep-dive presentation architecture

**Target deck:** presentation/seamwise.html<br>
**Quality benchmark:** presentation/task-spec.md<br>
**Canonical product source:** /Users/luanmorenomaciel/GitHub/seamwise<br>
**Current source revision audited:** a49748ee39d04a6ca5ce54c6a22df331ee89ff11 (main, 2026-08-19)<br>
**Frozen release reference:** v0.2.0 at 5a398169c3fefcb65eb1a47c0cb4f967dfdc0515<br>
**Source relationship:** current main is v0.2.0-33-ga49748e and contains Unreleased changes<br>
**Agenda authored:** 2026-08-26<br>
**Product contract:** Python 3.11+, SeamwiseCLIResult/v1, TaskPlan/v1, SeamwiseTaskPlanLineage/v1<br>
**Build method:** one slide at a time; verify claim, hierarchy, overflow, and speaker notes before advancing

This file is the construction source for the complete Seamwise deep-dive deck.
It is intentionally more detailed than the final screen copy. The HTML must
distill one numbered section at a time without weakening the evidence boundary,
human decision points, or product authority split.

The current 13-slide HTML is a concise primer and the signed visual reference.
The 78-slide architecture below expands that primer; it does not authorize
silently replacing its strongest copy, visuals, or brand grammar. Existing
slides should be mapped into the new sequence, reviewed, and then either
preserved, refined, or superseded explicitly.

---

## 1. North star

The audience must leave with one exact model:

> Seamwise compiles one approved initiative and immutable evidence into
> evidence-backed seams, one owning swimlane per seam, observable capability
> legs, a dependency-safe graph, and one human-reviewed TaskPlan. It stops
> before task materialization, dispatch, execution, or acceptance.

The product is not a brainstorming assistant, backlog generator, project
manager, executor, or substitute for Task-Spec. It is a deterministic,
architecture-aware decomposition compiler:

~~~mermaid
flowchart LR
    I["Approved initiative"] --> E["Immutable local evidence"]
    E --> S["Seams"]
    S --> W["One owning swimlane per seam"]
    W --> L["Observable capability legs"]
    L --> G["Dependency-safe task graph"]
    G --> R{"Explicit human review"}
    R --> P["TaskPlan/v1"]
    R --> X["SeamwiseTaskPlanLineage/v1"]
    P --> C["Composition coordinator"]
    X --> C
    C --> T["Independent Task-Spec engine"]

    classDef human fill:#17140c,stroke:#d4af37,color:#eaedf2
    classDef compiler fill:#0d1828,stroke:#2f6bff,color:#eaedf2
    classDef artifact fill:#102019,stroke:#3fb950,color:#eaedf2
    class I,R human
    class E,S,W,L,G compiler
    class P,X,C,T artifact
~~~

The emotional arc is:

1. **Unease** — initiatives are usually cut by org chart, layer, or guesswork.
2. **Recognition** — a real seam is a responsibility boundary with evidence, contracts, ownership, and independent proof.
3. **Structure** — lanes own seams; legs name observable states; the steel thread names the smallest proving path.
4. **Control** — unresolved evidence, ownership, architecture, objection, topology, or path questions close the gate.
5. **Consent** — a named human accepts the exact delivery-plan digest.
6. **Portability** — reviewed topology becomes TaskPlan/v1 plus digest-bound lineage.
7. **Restraint** — Seamwise stops; Task-Spec and the coordinator retain their separate authority.
8. **Honesty** — released, current-main, derived, external, and proposed claims remain visibly different.

---

## 2. Evidence and claim policy

The deck must teach that not every repository surface carries the same
authority or freshness.

| Rank | Surface | Deck use |
|---:|---|---|
| 1 | OPERATING.md and AGENTS.md | Current ownership, lifecycle, invariants, and refusal boundaries |
| 2 | schemas/*.schema.json | Exact authored and emitted machine contracts |
| 3 | src/seamwise/ | Current executable behavior at the audited commit |
| 4 | tests/ and scripts/ | Direct proof of happy paths, attacks, packaging, and interoperability |
| 5 | README.md and CLAUDE.md | Product explanation and operator route; verify against code |
| 6 | CHANGELOG.md and Git tags | Released versus Unreleased behavior |
| 7 | presentation/seamwise.html | Current presentation copy and visual grammar, not product authority |
| 8 | historical memory or removed docs | Routing context only; never current implementation proof |

Use these labels in every slide’s speaker notes:

- **O — Operating:** explicit current ownership or lifecycle rule.
- **S — Schema:** versioned machine contract or authored grammar.
- **I — Implemented:** executable behavior at audited current main.
- **T — Tested:** local test or adversarial fixture directly exercises the claim.
- **R — Released:** frozen v0.2.0 tag or immutable release artifact.
- **C — Current-main:** implemented after v0.2.0; not frozen release evidence.
- **D — Documentary:** explanatory prose or presentation copy.
- **X — External:** behavior owned by Task-Spec, Converge, a host, or another repository.
- **P — Proposed:** roadmap, design, or model-authored material without implemented proof.

### Audit snapshot

The live source audit covered:

- the repository contract, operating hops, README, Claude guide, changelog, package metadata, and release workflows;
- eight published JSON Schemas;
- 22 Python source modules and the six-stage acyclic engine;
- the complete Click command surface and result-envelope behavior;
- five shared Codex/Claude skills and both plugin ecosystems;
- seven pytest modules, the rate-limiting proving fixture, host-plugin proof, and clean-room wheel proof;
- the current 13-slide HTML primer and the 66-slide Task-Spec presentation architecture.

The exact Seamwise <code>make check</code> boundary was rerun locally on
2026-08-26 against current main:

~~~text
113 passed in 33.32s
Required test coverage of 78.0% reached. Total coverage: 79.02%
Host adapters valid: 2 manifests, 2 marketplaces, 5 shared skills
unexpected Mermaid start in README.md: %%{init: ...}%%
make: *** [check] Error 1
~~~

The four README Mermaid blocks now begin with a theme-init directive, while
scripts/validate_docs.py requires the first Mermaid line to be a graph or
sequence declaration. Therefore:

- unit, adversarial, coverage, and host-manifest checks passed in this run;
- the complete release boundary did not pass;
- later build, release-asset, doctor, live host-plugin, and clean-room steps did
  not execute in this invocation because the documentation check failed first;
- the source checkout remained clean after the run;
- this is current-main documentation-validator drift, not proof that the
  v0.2.0 frozen release failed and not permission to claim the remaining gate
  steps passed.

### Claims the deck may make

- Seamwise is an implemented architecture-aware, model-agnostic decomposition compiler.
- It accepts one authored recipe grounded in immutable local evidence.
- It separates current, proposed, derived, and external claims.
- A seam carries responsibility, consumes/produces contracts, evidence, one owner, independent proof, and rejected alternatives.
- Every accepted seam has exactly one owning swimlane with the same owner.
- Capability legs name observable states and proof, not activities.
- A steel thread is the minimum ordered capability path that proves the initiative’s core behavior.
- Task dependencies must prove capability dependencies; sibling position does not imply causality or safe parallelism.
- The delivery plan stops for explicit human review, and its receipt binds the exact reviewed bytes.
- Compile emits exactly TaskPlan/v1 and SeamwiseTaskPlanLineage/v1 in one transaction.
- Status independently rebuilds expected graph, TaskPlan, and lineage projections.
- Successful compilation still reports zero Task-Spec files, no materialization receipt, and dispatch_authorized false.
- Task-Spec remains an independently installed and negotiated product.
- The v0.2.0 release removed the embedded Task Pack and direct Task-Spec behavior.

### Claims the deck must refuse

- That a fuzzy, unapproved idea is valid compiler input.
- That a model-generated seam map is accepted architecture.
- That schema validity proves evidence truth, system correctness, or product delivery.
- That a team, layer, component, or repository is automatically a real seam.
- That two sibling tasks are safe to run concurrently.
- That telemetry or reports create authority.
- That a delivery-plan review is a Task-Spec HMAC seal.
- That TaskPlan compilation materializes, authorizes, executes, or accepts tasks.
- That Seamwise invokes, vendors, imports, or reimplements Task-Spec.
- That Codex or Claude skill installation proves a fresh session can invoke a skill.
- That a local process is a sandbox.
- That current main is identical to the tagged v0.2.0 release.
- That current main passes the complete release gate while the documentation drift remains.
- That removed docs/seamwise.pdf is still the live canonical blueprint.

---

## 3. Visual system for every slide

Retain the exact visual grammar already implemented in
presentation/seamwise.html.

| Semantic role | Color | Use |
|---|---|---|
| Factory Black | #08080A / #111114 | stage, negative space, serious editorial tone |
| Seamwise Blue | #2F6BFF / #6EA2FF | compiler-owned transformations and canonical through-line |
| Contract Cyan | #22D3EE | machine contracts, schemas, envelopes, portable packets |
| Capability Gold | #D4AF37 | proof-bearing capability states and human review |
| Accepted Green | #3FB950 | ready tokens, verified bindings, successful handoff |
| Objection Purple | #A78BFA | review, alternatives, research, and unresolved reasoning |
| Refused Red | #F85149 | tamper, collision, stale review, authority overreach, closed gate |
| Evidence Silver | #B0BEC5 | source metadata, external context, documentary qualifiers |

### Typography and atmosphere

- Instrument Serif is the Roman display face; never substitute a generic bold sans for the headline.
- Newsreader carries explanatory and italic editorial copy.
- DM Sans carries compact body text.
- Fira Code carries commands, tokens, hashes, IDs, schema fields, and source labels.
- Preserve the aurora drift, grid floor, pointer spotlight, reveal motion, progress rail, act capsule, and vertical tracker.
- Respect prefers-reduced-motion and keyboard navigation already present in the HTML.
- Keep the Datum Joint icon/lockup and Seamwise-blue anchor; do not reintroduce discarded brand explorations.

### Reusable components

- **Seam rail:** two system slabs separated by one luminous blue joint.
- **Ownership pool:** one lane header, one owner, writable capability blocks, read-only context.
- **Capability card:** observable state, proof, requires, produces, then task count.
- **Steel-thread rail:** ordered gold legs over a blue lineage thread.
- **Gate:** a clear red or gold stop with one exact required input.
- **Digest joint:** two artifact cards connected by a hash-labeled rail.
- **macOS code window:** traffic-light dots, terse content, no fake shell noise.
- **Result envelope:** token and exit code at top; artifacts, diagnostics, next, and data below.
- **Claim badge:** O/S/I/T/R/C/D/X/P source class in speaker notes and audit slides.
- **Authority trio:** Seamwise, Task-Spec, Converge cards with owns / refuses / handoff.
- **Failure card:** trigger, stable token, exit, diagnostic, repair boundary.

### Density guardrails

- One idea and one primary visual per slide.
- Use three cards by default; four only for a true four-part grammar.
- On-screen prose should explain, not transcribe the schema.
- Cap code at 8–20 visible lines and highlight no more than four fields.
- Cap tables at six rows; split larger matrices.
- Keep IDs readable at 1366×768.
- Never show a real credential, reviewer identity, HMAC, private evidence body, absolute consumer path, or secret-bearing environment value.
- Put exact source paths, qualifiers, and extra examples in speaker notes.
- Build at 1440×900; verify 1920×1080, 1366×768, and 390×844 after every slide.
- At mobile width, stack cards in causal order; do not shrink diagrams into illegibility.

---

## 4. Story map

| Act | Slides | Question answered | Emotional move |
|---|---:|---|---|
| I — The cut | 01–08 | Why does architecture-aware decomposition exist? | ambiguity → category clarity |
| II — Evidence before structure | 09–17 | What must be true before a cut is trusted? | plausibility → grounded intent |
| III — The decomposition grammar | 18–32 | What exactly are seams, lanes, legs, threads, and leaves? | vocabulary → inspectable structure |
| IV — Map, plan, review | 33–42 | How does authored intent cross the human topology barrier? | structure → consent |
| V — Graph and projection | 43–55 | How does reviewed topology become a safe external contract? | consent → portable plan |
| VI — Fail closed | 56–64 | How does the compiler resist drift, tamper, unsafe paths, and authority creep? | portability → trust |
| VII — Product surface | 65–71 | How do humans, agents, hosts, and automation drive the same compiler? | trust → practical adoption |
| VIII — Proof and evolution | 72–78 | What is released, current, tested, broken, and deliberately absent? | adoption → honest confidence |

### Master transition

Every slide must answer one of five questions:

1. **What evidence allows this cut?**
2. **Who owns the resulting boundary?**
3. **What observable state proves progress?**
4. **Which exact gate prevents an unsafe transition?**
5. **Which product owns the next authority?**

If a slide cannot answer one of them, remove it or move it to speaker notes.

---

## 5. Slide-by-slide blueprint

## ACT I — THE CUT

### S01 — SEAMWISE

**Act/HUD:** SEAMWISE · THE DECOMPOSITION COMPILER<br>
**Core line:** “One approved initiative in. One reviewed TaskPlan/v1 and digest-bound lineage out.”<br>
**Visual:** preserve the current title composition, Datum Joint mark, blue seam wordmark, and four verbs: discovers, owns, orders, projects.<br>
**Footer:** v0.2.0 release · current main audited separately · Python 3.11+ · MIT.<br>
**Boundary:** never add “tasks out,” “dispatch,” or “autonomous delivery.”<br>
**Sources:** [D] current HTML S01; [O] OPERATING.md; [I] README.md and cli.py.<br>
**Transition:** “The product exists because most initiatives are cut in the wrong place.”

### S02 — Backlogs cut work. Seamwise cuts responsibility.

**Act/HUD:** THE CATEGORY · DECOMPOSITION BEFORE TASKING<br>
**Core line:** a backlog names work items; Seamwise finds independently provable system boundaries before those work items gain authority.<br>
**Visual:** left, flat backlog cards grouped by feature; right, an initiative cut into seams with contract joints and owners.<br>
**Three distinctions:** scope discovery; architecture-aware ordering; proof-bearing projection.<br>
**Refusal:** Seamwise is not a tracker, project manager, or execution loop.<br>
**Sources:** [O] AGENTS.md, OPERATING.md; [I] README.md.<br>
**Transition:** “But it does not accept every idea as a valid initiative.”

### S03 — The input is an approved initiative, not a raw thought

**Act/HUD:** THE INPUT · AUTHORITY STARTS BEFORE THE COMPILER<br>
**Core line:** the caller must establish that the initiative is worth decomposing; Seamwise does not invent business authority.<br>
**Visual:** raw idea stops outside; approved initiative plus evidence enters.<br>
**Input card:** delivery outcome, success conditions, out-of-scope boundary, claim class, source.<br>
**Boundary:** approval here is initiative authority, not delivery-plan review and not Task-Spec sealing.<br>
**Sources:** [O] README.md, OPERATING.md; [S] recipe.schema.json.<br>
**Transition:** “Once the initiative is real, three products must still stay separate.”

### S04 — Decompose, contract, coordinate

**Act/HUD:** THE STACK · DUPLICATE CAPABILITY IS TOLERABLE; DUPLICATE AUTHORITY IS NOT<br>
**Core line:** “Seamwise decomposes. Task-Spec contracts. Converge coordinates.”<br>
**Visual:** preserve and expand the current three-product cards.

| Product | Owns | Must not own |
|---|---|---|
| Seamwise | seams, lanes, legs, topology, plan review, TaskPlan projection | Task-Spec materialization, dispatch, execution, acceptance |
| Task-Spec | plan validation, leaves, sealing, handoff, eval, acceptance | initiative decomposition |
| Converge | engine negotiation, sequencing, runtime binding, settlement | either engine’s internal authority |

**Sources:** [O] AGENTS.md, OPERATING.md; [I] capabilities command.<br>
**Transition:** “Now examine the two cuts that look efficient but destroy proof.”

### S05 — Two bad cuts: by layer and by org chart

**Act/HUD:** THE ANTI-PATTERN · FAMILIAR IS NOT PROVABLE<br>
**Core line:** “frontend/backend/database” and “team A/team B/team C” may describe placement, not a responsibility boundary.<br>
**Visual:** two brittle cuts with many hidden crossings; a third evidence-backed seam with one explicit contract joint.<br>
**Test:** can the cut state what it consumes, produces, owns, and proves independently?<br>
**Sources:** [D] current HTML S02; [S] recipe seam contract.<br>
**Transition:** “A real seam is a contract-bearing joint.”

### S06 — A seam is a responsibility boundary with proof

**Act/HUD:** THE SEAM · NOT A LINE ON A DIAGRAM<br>
**Core line:** one accepted seam combines responsibility, evidence, consumes, produces, owner, independent proof, decisions, and rejected alternatives.<br>
**Visual:** preserve the current two-slab seam diagram; label every field around the blue joint.<br>
**Red callouts:** shared owner without contract; shared database without boundary; renamed component without independent proof.<br>
**Sources:** [D] current HTML S03; [S] recipe.schema.json; [I] engine/seams.py.<br>
**Transition:** “The compiler applies a concrete readiness test.”

### S07 — Seven checks make the seam earn READY

**Act/HUD:** THE SEAM TEST · EVIDENCE BEFORE ELEGANCE<br>
**Core line:** a plausible architecture story is not enough.

1. cited evidence exists and matches its declared digest;
2. responsibility is nonblank;
3. consumes and produces are explicit;
4. seam and lane owners are nonblank and identical;
5. independent proof is explicit;
6. depended-on decisions are accepted;
7. rejected alternatives explain why other cuts lost.

**Visual:** seven joints lock into one SEAM_MAP=READY token.<br>
**Sources:** [S] recipe schema; [I] engine/recipe.py; [T] test_fail_closed.py.<br>
**Transition:** “Those checks sit inside a longer authority-bounded journey.”

### S08 — One journey, four machine transformations, one human barrier

**Act/HUD:** THE FLOW · THE RED NODE IS A PERSON<br>
**Core line:** init → map → plan → review → compile → status.<br>
**Visual:** preserve current HTML S08; make machine nodes blue/green and review gold/red.<br>
**Key tokens:** WORKSPACE=READY; SEAM_MAP=READY; DELIVERY_PLAN=NEEDS_REVIEW; DELIVERY_PLAN=READY; TASK_GRAPH=READY; STATUS=READY.<br>
**Boundary:** exit 2 can be the intended gate, not a compiler malfunction.<br>
**Sources:** [I] cli.py, workspace.py; [D] current HTML S08.<br>
**Transition:** “Before mapping, the compiler asks what kind of claim every source is making.”

---

## ACT II — EVIDENCE BEFORE STRUCTURE

### S09 — Four claim classes prevent category mistakes

**Act/HUD:** THE CLAIM · CURRENT, PROPOSED, DERIVED, EXTERNAL<br>
**Core line:** source class travels with intent and evidence so presentation does not become proof.<br>
**Visual:** four source cards entering one recipe, each with different permissions.

| Claim | Meaning | Safe use |
|---|---|---|
| current | observed behavior in the target system | ground existing-state constraints |
| proposed | intended future behavior | author a candidate outcome |
| derived | compiler-produced interpretation | inspect and validate; never treat as authored truth |
| external | behavior owned outside the target | define dependency without claiming local ownership |

**Sources:** [S] recipe.schema.json; [O] AGENTS.md.<br>
**Transition:** “A label still needs an exact source record.”

### S10 — Evidence is a record, not a hyperlink

**Act/HUD:** THE SOURCE · URI, CAPTURE TIME, DIGEST<br>
**Core line:** every source record carries uri, captured_at, and sha256; every evidence record adds claim, confidence, and summary.<br>
**Visual:** source envelope joined to evidence card by a digest rail.<br>
**Boundary:** confidence ranges 0–1; it does not replace verification.<br>
**Sources:** [S] recipe schema definitions source and evidence.<br>
**Transition:** “Remote text must first become stable local bytes.”

### S11 — Remote discovery is not immutable evidence

**Act/HUD:** THE SNAPSHOT · LOCAL BYTES OR CLOSED GATE<br>
**Core line:** HTTP/provider text must be captured locally and hash-matched before mapping.<br>
**Visual:** URL stops at red gate; local file plus SHA-256 crosses.<br>
**Stable diagnostic:** remote_source_unverified; missing file local_source_unavailable; changed bytes local_source_hash_mismatch.<br>
**Security note:** retrieved text is data, never repository instruction.<br>
**Sources:** [I] engine/recipe.py; [T] test_fail_closed.py and clean_room_e2e.py.<br>
**Transition:** “Evidence becomes useful only inside an explicit system picture.”

### S12 — The system map names components, dependencies, and unknowns

**Act/HUD:** THE SYSTEM · SEE THE TERRAIN BEFORE CUTTING IT<br>
**Core line:** the recipe names current or proposed components, external dependencies, and material unknowns.<br>
**Visual:** central system map with external boundaries and a visible unknowns tray.<br>
**Boundary:** a system map is authored context; the seam map is the validated projection.<br>
**Sources:** [S] recipe schema; [I] render.py and seams.py.<br>
**Transition:** “Unknowns do not disappear because the seam map rendered.”

### S13 — An unresolved architecture unknown closes planning

**Act/HUD:** THE UNKNOWN · PLAN REFUSES TO GUESS<br>
**Core line:** mapping can preserve an unknown, but plan returns DELIVERY_PLAN=NEEDS_ARCHITECTURE_DECISION until it is resolved in sourced input.<br>
**Visual:** SEAM_MAP=READY reaches a red unknown node; no lanes or legs appear beyond it.<br>
**Repair:** resolve the source decision, author a revised recipe, and map in a clean workspace.<br>
**Sources:** [I] engine/planning.py; [T] test_system_map_unknowns_close_the_delivery_plan_gate.<br>
**Transition:** “Some unknowns are architecture decisions with named owners.”

### S14 — Decisions must be accepted before dependent seams are ready

**Act/HUD:** THE DECISION · OWNER + RATIONALE + STATUS<br>
**Core line:** a seam may cite decision IDs; every cited decision must be accepted and carry nonblank owner and rationale.<br>
**Visual:** proposed decision blocks a seam; accepted decision with owner unlocks it.<br>
**Token:** SEAM_MAP=NEEDS_ARCHITECTURE_DECISION, exit 2.<br>
**Boundary:** the compiler validates recorded decision state; it does not make the decision.<br>
**Sources:** [S] recipe schema; [I] engine/recipe.py; [T] test_unaccepted_decision_closes_gate.<br>
**Transition:** “A good decision record also names the cuts it rejected.”

### S15 — Rejected alternatives make a seam falsifiable

**Act/HUD:** THE ALTERNATIVES · WHY THIS JOINT, NOT THE OBVIOUS ONE<br>
**Core line:** every seam must retain at least one alternative and the reason it lost.<br>
**Visual:** selected blue seam beside two muted rejected cuts with explicit failure reasons.<br>
**Why it matters:** future reviewers can tell whether new evidence invalidates the original cut.<br>
**Sources:** [S] recipe seam definition; [D] current HTML seam narrative.<br>
**Transition:** “Alternatives are architectural; objections are review state.”

### S16 — Objections stay OPEN until an owner rules

**Act/HUD:** THE OBJECTION · MODELS MAY RAISE; OWNERS RESOLVE<br>
**Core line:** OPEN blocks review; FIXED or ACCEPTED requires owner and rationale.<br>
**Visual:** objection state machine.

~~~mermaid
stateDiagram-v2
    [*] --> OPEN
    OPEN --> FIXED: owner + repair + rationale
    OPEN --> ACCEPTED: owner + explicit risk acceptance
    FIXED --> [*]
    ACCEPTED --> [*]
~~~

**Token:** DELIVERY_PLAN=OPEN_OBJECTIONS until none remain OPEN.<br>
**Sources:** [S] recipe and delivery-plan schemas; [I] planning.py; [T] test_open_objection_cannot_be_reviewed.<br>
**Transition:** “All of this authored truth enters through one strict recipe.”

### S17 — The recipe is the authored source; projections are rebuildable

**Act/HUD:** THE AUTHORING CONTRACT · ONE STRICT YAML INPUT<br>
**Core line:** seamwise-recipe.yaml contains intent, system map, evidence, decisions, seams, steel thread, objections, and contentions.<br>
**Visual:** large recipe card fans into derived artifacts; arrows never reverse.<br>
**Strictness:** duplicate YAML keys fail; blank semantic fields fail; ambiguous YAML scalars fail; additional unsupported fields fail through schema validation.<br>
**Boundary:** do not hand-edit a projection to make status green.<br>
**Sources:** [S] recipe schema; [I] io.py strict loader and recipe.py; [T] tests.<br>
**Transition:** “Now read the decomposition grammar from largest boundary to smallest proof.”

---

## ACT III — THE DECOMPOSITION GRAMMAR

### S18 — One grammar lowers altitude without losing lineage

**Act/HUD:** THE GRAMMAR · INTENT → SEAM → LANE → LEG → UNIT<br>
**Core line:** each stage adds one kind of structure: boundary, ownership, observable state, runnable proof, and lineage.<br>
**Visual:** expand current HTML S06 into five stages.

~~~text
Delivery Intent
  └─ seam
      └─ one owning swimlane
          └─ capability leg
              └─ runnable task contract
                  └─ TaskPlan/v1 unit + lineage
~~~

**Sources:** [O] AGENTS.md; [I] engine stages and taskspec_adapter.py.<br>
**Transition:** “The seam is the only architectural cut in the chain.”

### S19 — Seam anatomy

**Act/HUD:** THE SEAM · EIGHT LOAD-BEARING FIELDS<br>
**Core line:** ID/name; description; evidence; responsibility; consumes; produces; owner; independent proof; decision IDs; rejected alternatives; one swimlane.<br>
**Visual:** annotated seam frontmatter with callout pins.<br>
**Presenter rule:** teach semantics, not YAML punctuation.<br>
**Sources:** [S] recipe schema; [I] render_seam.<br>
**Transition:** “The two contract lists make the joint concrete.”

### S20 — Consumes and produces define the joint

**Act/HUD:** THE CONTRACT · INFORMATION CROSSES; OWNERSHIP DOES NOT<br>
**Core line:** seams interact through named inputs and outputs, not invisible shared mutation.<br>
**Visual:** two lanes exchange one versioned artifact across the seam.<br>
**Failure examples:** “uses database,” “calls backend,” and “shares model” are too vague without state semantics.<br>
**Sources:** [S] recipe schema; [D] current HTML S03–S04.<br>
**Transition:** “The same owner must then carry the seam and its lane.”

### S21 — One accepted seam has exactly one owning swimlane

**Act/HUD:** THE OWNERSHIP · NO ORPHANS, NO CO-OWNED ESCAPE HATCH<br>
**Core line:** seam.owner must equal seam.swimlane.owner.<br>
**Visual:** one seam enters one lane; two-owner and ownerless variants terminate red.<br>
**Token:** SEAM_MAP=NEEDS_OWNER_INPUT when ownership is missing or mismatched.<br>
**Sources:** [O] AGENTS.md; [I] recipe.py and planning.py; [T] test_missing_owner_needs_owner_input.<br>
**Transition:** “A lane owns a boundary, not a department.”

### S22 — A swimlane is a write-and-proof jurisdiction

**Act/HUD:** THE SWIMLANE · OWNER, WRITES, READS, CONTRACT CROSSINGS<br>
**Core line:** preserve current HTML pool metaphor: the lane header names the owner; gold blocks show writable capability states; dashed context stays read-only.<br>
**Refusal:** lanes do not become parallel merely because they are drawn side by side.<br>
**Sources:** [D] current HTML S04; [I] render_swimlane and delivery-plan projection.<br>
**Transition:** “Inside the lane, progress is expressed as observable states.”

### S23 — A capability leg is a state, not an activity

**Act/HUD:** THE LEG · SOMETHING TESTABLE BECOMES TRUE<br>
**Core line:** “policy documents are schema-valid” is a leg; “implement policy schema” is an activity.<br>
**Visual:** bad verb cards convert into observable-state cards with proof.<br>
**Required fields:** observable_state, proof, requires, produces, one or more tasks.<br>
**Sources:** [O] AGENTS.md; [S] recipe leg definition; [D] current HTML S05.<br>
**Transition:** “The steel thread selects the smallest sequence that proves the system.”

### S24 — The steel thread is the minimum proving path

**Act/HUD:** THE THREAD · NOT THE WHOLE ROADMAP<br>
**Core line:** ordered leg IDs form the thinnest end-to-end capability chain that proves the initiative’s core outcome.<br>
**Visual:** four gold states over one blue thread; optional legs remain outside without disappearing.<br>
**Example:** schema valid → effective policy resolved → request 101 denied → reason and telemetry agree.<br>
**Sources:** [S] recipe steel_thread; [T] rate-limiting fixture; [I] render_steel_thread.<br>
**Transition:** “Thread order must also exist as task causality.”

### S25 — Capability requirements need one producer

**Act/HUD:** THE CAPABILITY GRAPH · STATE NAMES BECOME CAUSAL OBLIGATIONS<br>
**Core line:** every required state must have exactly one distinct producing leg.<br>
**Visual:** state artifact from producer leg to consumer leg; zero and multiple producer branches fail red.<br>
**Diagnostics:** capability_requirement_unproduced; capability_producer_ambiguous.<br>
**Sources:** [I] graph.py; [T] fail-closed capability tests.<br>
**Transition:** “A state arrow without a task dependency is still fiction.”

### S26 — Root tasks must depend on the producing leg

**Act/HUD:** THE CAUSALITY · LABELS DO NOT CREATE ORDER<br>
**Core line:** each consumer-leg root task needs a transitive dependency on a task in the producer leg.<br>
**Visual:** capability rail above, task DAG below; both must agree.<br>
**Diagnostic:** missing_capability_dependency.<br>
**Boundary:** this rule also applies to capability legs outside the steel thread.<br>
**Sources:** [I] graph.py; [T] required-capability and outside-thread tests.<br>
**Transition:** “At the bottom of the grammar sits one independently provable leaf.”

### S27 — A runnable task owns one coherent done-condition

**Act/HUD:** THE LEAF · FUTURE TASK-SPEC INPUT<br>
**Core line:** goal, done condition, effort, profile, backend, tools, dependencies, paths, behavior, evals, guardrails, rollback, and observability travel together.<br>
**Visual:** one annotated recipe task becomes one TaskPlan unit.<br>
**Boundary:** this is authored task intent, not a materialized or sealed Task-Spec file.<br>
**Sources:** [S] recipe task definition; [I] taskspec_adapter.py.<br>
**Transition:** “Seamwise deliberately fixes the traceability shape.”

### S28 — Exactly two behaviors, in canonical order

**Act/HUD:** THE BEHAVIOR · B-1 AND B-2<br>
**Core line:** every task authors exactly B-1 and B-2, each with given, when, then.<br>
**Visual:** two behavior cards joined to the done-condition.<br>
**Qualifier:** this is the current recipe-v1 constraint, not a universal task-design law.<br>
**Diagnostic:** unsupported_traceability_shape.<br>
**Sources:** [S] recipe schema; [I] recipe.py.<br>
**Transition:** “Three evals must collectively witness both behaviors.”

### S29 — Exactly three evals, no orphan behavior

**Act/HUD:** THE PROOF · EVAL_1, EVAL_2, EVAL_3<br>
**Core line:** every task authors exactly eval_1–eval_3; verifies must cover the full set B-1/B-2.<br>
**Visual:** bipartite witness graph.

~~~mermaid
flowchart LR
    B1["B-1"] --> E1["eval_1"]
    B1 --> E3["eval_3 · terminal in TaskPlan"]
    B2["B-2"] --> E2["eval_2"]
    B2 --> E3
~~~

**Projection detail:** TaskPlan marks only the final eval terminal and assigns expected_duration_sec 10 to each.<br>
**Sources:** [S] recipe schema; [I] recipe.py and taskspec_adapter.py.<br>
**Transition:** “Proof must sit inside a bounded write surface.”

### S30 — Paths are portable, explicit, and contradiction-free

**Act/HUD:** THE WRITE SURFACE · TOUCH, CREATE, PROTECT<br>
**Core line:** touches_paths names existing or ancestor-created paths; creates_paths names absent paths; do_not_touch may not overlap either.<br>
**Visual:** blue write moat and red protected boundary.<br>
**Refusals:** absolute paths, backslashes, dot segments, empty segments, globs, case-only collisions, and symlink escapes.<br>
**Sources:** [I] recipe.py, safety.py, graph.py; [T] path tests.<br>
**Transition:** “Effort also caps how broad that write surface may become.”

### S31 — Effort limits write breadth

**Act/HUD:** THE BUDGET · SIZE MUST MATCH BLAST RADIUS<br>
**Core line:** unique canonical write paths are capped by effort.

| Effort | Maximum write paths |
|---|---:|
| XS | 1 |
| S | 2 |
| M | 3 |
| L | 5 |

**Token:** TASK_GRAPH=UNPROVABLE_NODE when the task exceeds its limit.<br>
**Boundary:** Seamwise recipe v1 supports XS/S/M/L only; composition sizes belong downstream.<br>
**Sources:** [S] recipe schema; [I] graph.py; [T] write-surface budget test.<br>
**Transition:** “Even valid task sizes can still collide.”

### S32 — Contention is explicit ordering, not optimistic parallelism

**Act/HUD:** THE CONTENTION · BETWEEN, RESOLUTION, ORDER<br>
**Core line:** two tasks sharing a resource require an explicit ordered contention or dependency path.<br>
**Visual:** sibling tasks converge on one path; order rail resolves the collision.<br>
**Rule:** contention.between and contention.order must name the same two known tasks.<br>
**Refusal:** sibling position never grants concurrency.<br>
**Sources:** [S] recipe/delivery-plan schemas; [I] graph.py; [T] collision tests.<br>
**Transition:** “With the grammar assembled, mapping can create the first validated projection.”

---

## ACT IV — MAP, PLAN, REVIEW

### S33 — Map validates authored truth before writing projections

**Act/HUD:** THE MAP · RECIPE TO SEAM MAP<br>
**Core line:** <code>map --source</code> loads strict YAML, validates schema and semantics, verifies local evidence and paths, rechecks under lock, then writes one transaction.<br>
**Visual:** validator pipeline with red exits at each stage.<br>
**Token family:** READY; NEEDS_DISCOVERY; NEEDS_OWNER_INPUT; NEEDS_ARCHITECTURE_DECISION; AMBIGUOUS; ERROR.<br>
**Sources:** [I] engine/recipe.py and engine/seams.py; [S] seam-map schema.<br>
**Transition:** “A successful map writes more than one YAML index.”

### S34 — Map emits authored evidence and hash-indexed seam artifacts

**Act/HUD:** THE MAP OUTPUT · CANONICAL INPUTS, DERIVED VIEWS<br>
**Core line:** successful mapping writes:

~~~text
seamwise/
├── intent.md
├── system-map.md
├── evidence.jsonl
├── decisions/*.md
├── seams/*.md
├── seam-map.yaml
└── telemetry/events.jsonl
~~~

**Visual:** repository tree with authored/derived color labels.<br>
**Boundary:** telemetry authorization is always false.<br>
**Sources:** [I] seams.py, render.py, support.py.<br>
**Transition:** “The index is trusted only while every indexed byte still matches.”

### S35 — The seam map is a tamper-evident inventory

**Act/HUD:** THE VERIFY · HASH, ID, PATH, SOURCE, INVENTORY<br>
**Core line:** planning revalidates schema, source recipe digest, intent/system/evidence digests, decision/seam paths, frontmatter IDs, seam lineage, and exact directory inventory.<br>
**Visual:** seam-map index checks every artifact and rejects one extra or changed file.<br>
**Stable failures:** seam_hash_mismatch; seam_inventory_mismatch; seam_source_changed; seam_lineage_mismatch.<br>
**Sources:** [I] verify_seam_map; [T] seam tamper test.<br>
**Transition:** “Only then can plan derive ownership and capability views.”

### S36 — Plan lowers seams into lanes, legs, thread, and review state

**Act/HUD:** THE PLAN · DERIVED TOPOLOGY<br>
**Core line:** <code>plan</code> verifies the seam map, refuses unresolved architecture unknowns, renders one lane per seam, renders every leg, renders the steel thread, and indexes objections/contentions.<br>
**Visual:** seam map fans into lane/leg cards and delivery-plan.yaml.<br>
**Sources:** [I] planning.py and render.py; [S] delivery-plan schema.<br>
**Transition:** “The generated files remain inspectable, but their index is the gate.”

### S37 — Delivery-plan artifacts carry lineage back to the seam

**Act/HUD:** THE PLAN OUTPUT · OWNER AND SOURCE DIGEST TRAVEL DOWN<br>
**Core line:** each lane index names seam_id, owner, path, and SHA-256; each leg index names seam_id, swimlane_id, path, and SHA-256.<br>
**Visual:** lane and leg frontmatter joined back to seam-map digest.<br>
**Inventory rule:** extra, missing, renamed, or changed lane/leg files block verification.<br>
**Sources:** [I] planning.py verify_plan.<br>
**Transition:** “Plan readiness is a state family, not one boolean.”

### S38 — Plan tokens tell the human what remains unresolved

**Act/HUD:** THE PLAN STATE · THE TOKEN IS THE GATE SPEAKING<br>
**Visual:** token ladder.

| Token | Meaning | Exit |
|---|---|---:|
| DELIVERY_PLAN=NEEDS_REVIEW | topology is structurally reviewable | 2 |
| DELIVERY_PLAN=OPEN_OBJECTIONS | one or more objections remain OPEN | 2 |
| DELIVERY_PLAN=NEEDS_OWNER_INPUT | accepted/fixed objection lacks owner or rationale | 2 |
| DELIVERY_PLAN=NEEDS_ARCHITECTURE_DECISION | source or prior-projection decision blocks progress | 2 or 4 |
| DELIVERY_PLAN=READY | exact plan has a current accepted receipt | 0 |
| DELIVERY_PLAN=ERROR | invalid mechanism or projection | 3 or 4 |

**Sources:** [S] schema; [I] constants.py and planning.py.<br>
**Transition:** “NEEDS_REVIEW is the intended stop before human topology authority.”

### S39 — Review is a human topology barrier

**Act/HUD:** THE REVIEW · EXPLICIT ACCEPT, REVIEWER, REASON<br>
**Core line:** the only route to READY is <code>review --accept --reviewer ... --reason ...</code>.<br>
**Visual:** preserve current HTML human node, enlarged as a gold barrier.<br>
**Refusals:** no implicit review; no blank reviewer; no blank reason; no OPEN objection; no changed seam map.<br>
**Boundary:** a model may critique or propose; it cannot accept on an owner’s behalf.<br>
**Sources:** [I] cli.py and accept_plan; [O] skills and AGENTS.md.<br>
**Transition:** “The receipt binds both the draft that was read and the ready plan that results.”

### S40 — The review receipt is a two-digest authority joint

**Act/HUD:** THE RECEIPT · DRAFT SHA + READY PLAN SHA<br>
**Core line:** DeliveryPlanReview/v1 records disposition, reviewer, reason, time, draft_sha256, plan_sha256, and fixture flag.<br>
**Visual:** draft plan → authority record digest → READY plan; receipt binds both sides.<br>
**Detail:** plan.review_authority_sha256 hashes the canonical authority record; receipt.plan_sha256 binds the final ready YAML bytes.<br>
**Sources:** [S] delivery-plan-review schema; [I] accept_plan.<br>
**Transition:** “Any material change makes that authority stale.”

### S41 — Review survives identical reruns and fails on drift

**Act/HUD:** THE STALENESS · SAME BYTES PRESERVE; NEW TOPOLOGY REQUIRES NEW AUTHORITY<br>
**Core line:** an unchanged plan rerun preserves a verified review; changed projections refuse in-place replacement and require explicit archival or a clean workspace.<br>
**Visual:** identical digest loops green; changed digest branches red.<br>
**Stable failures:** review_hash_mismatch; plan_projection_replacement_required; plan_changed.<br>
**Sources:** [I] planning.py; [T] plan-rerun and review-tamper tests.<br>
**Transition:** “Automation can move between safe machine steps, but it cannot cross review.”

### S42 — Prepare automates transformations and still stops at authority

**Act/HUD:** THE PREPARE COMMAND · CONVENIENCE WITHOUT IMPLIED CONSENT<br>
**Core line:** <code>prepare</code> initializes, maps, and plans missing stages, then returns the review command; after review it may compile.<br>
**Visual:** automated blue rail stops at gold review gate.<br>
**Refusal:** supplied source differing from the already mapped recipe returns PREPARE=SOURCE_CHANGED; no silent replacement.<br>
**Sources:** [I] cli.py; [T] test_prepare_stops_at_review_gate and source-changed test.<br>
**Transition:** “After a current review, compile turns the plan into a graph before it emits anything external.”

---

## ACT V — GRAPH AND PROJECTION

### S43 — Compile rebuilds before it projects

**Act/HUD:** THE COMPILE · VERIFY → GRAPH → PROJECT → TRANSACT<br>
**Core line:** compile verifies the reviewed plan, rebuilds task records, derives the graph, validates graph/lineage schemas, rechecks under lock, and writes exactly two artifacts.<br>
**Visual:** five-stage compiler pipeline.<br>
**Boundary:** no Task-Spec binary is invoked.<br>
**Sources:** [I] compilation.py and taskspec_adapter.py; [T] adapter test.<br>
**Transition:** “The graph’s first edge family comes from explicit dependencies.”

### S44 — The DAG has dependency and contention-order edges

**Act/HUD:** THE GRAPH · TWO EDGE KINDS<br>
**Core line:** depends_on expresses causal work; contention_order serializes a shared resource.<br>
**Visual:** graph with solid blue dependency edges and gold contention edges.<br>
**Node fields:** task ID/title, seam, lane, leg, effort, profile, done condition, touch/create paths.<br>
**Sources:** [S] task-graph schema; [I] graph.py.<br>
**Transition:** “Any cycle closes the projection before outputs exist.”

### S45 — Cycles return a stable conflict, not a partial graph

**Act/HUD:** THE CYCLE · TOPOLOGY MUST BE EXECUTABLE<br>
**Core line:** deterministic topological sort reports TASK_GRAPH=CYCLE and the involved IDs.<br>
**Visual:** three-node loop turns red; empty output frame remains on the right.<br>
**Exit:** 4, integrity/topology conflict.<br>
**Sources:** [I] graph.py; [T] test_cycle_has_stable_failure_token.<br>
**Transition:** “Acyclic is necessary, but capability causality must also agree.”

### S46 — The capability graph and task graph must tell one story

**Act/HUD:** THE PROOF CHAIN · STATE ORDER = TASK ORDER<br>
**Core line:** produced/required states, steel-thread order, and transitive task dependencies are cross-validated.<br>
**Visual:** upper capability chain and lower task DAG aligned by vertical lineage rails.<br>
**Failures:** unproduced state; ambiguous producer; steel-thread order mismatch; missing dependency.<br>
**Sources:** [I] graph.py; [T] capability dependency tests.<br>
**Transition:** “Ordering also decides whether shared writes are safe.”

### S47 — Ordered overlap is different from unsafe collision

**Act/HUD:** THE WRITE GRAPH · SHARED PATHS REQUIRE CAUSAL ORDER<br>
**Core line:** exact paths and ancestor/descendant paths count as overlap.<br>
**Visual:** task A writes src/policy; task B writes src/policy/runtime.py. Ordered is gold; unordered is red.<br>
**Boundary:** declared contention alone is not enough if its order is invalid.<br>
**Sources:** [I] graph.py; [T] ancestor-collision test.<br>
**Transition:** “An undeclared unordered overlap yields one stable refusal.”

### S48 — TASK_GRAPH=COLLISION means parallelism is unproved

**Act/HUD:** THE COLLISION · FAIL CLOSED ON SIBLING WRITES<br>
**Core line:** unordered overlapping write surfaces return TASK_GRAPH=COLLISION, exit 4, with path details.<br>
**Visual:** two sibling branches hit the same red file node.<br>
**Repair choices:** add a real dependency; declare and justify contention order; or redesign the write boundary.<br>
**Sources:** [I] graph.py; [T] unordered-collision tests.<br>
**Transition:** “Once the graph is valid, the compiler can identify its longest causal chain.”

### S49 — Critical path is deterministic and inspectable

**Act/HUD:** THE CRITICAL PATH · LONGEST EDGE CHAIN, STABLE TIE BREAK<br>
**Core line:** graph projection computes the longest path over dependency and contention edges and hashes the Mermaid rendering.<br>
**Visual:** full graph muted; critical path glows gold.<br>
**Qualifier:** this is topological length, not time estimation.<br>
**Sources:** [I] graph.py; [S] task-graph schema.<br>
**Transition:** “The graph then becomes a portable TaskPlan without becoming task authority.”

### S50 — TaskPlan/v1 is the external handoff contract

**Act/HUD:** THE TASKPLAN · REVIEWED TOPOLOGY, NOT MATERIALIZED TASKS<br>
**Core line:** one unit per future leaf carries identity, dependencies, write boundary, behavior, evals, safety, rollback, and observability.<br>
**Visual:** preserve and expand current HTML S09 TaskPlan specimen.<br>
**Header:** api_version taskspec.dev/v1; kind TaskPlan; approved true; producer seamwise; producer_version; delivery-plan and review digests.<br>
**Boundary:** approved means human-reviewed topology; dispatch remains false downstream.<br>
**Sources:** [I] taskspec_adapter.py; [X] external Task-Spec TaskPlan contract.<br>
**Transition:** “A separate lineage artifact proves where every unit came from.”

### S51 — Lineage binds every unit back to intent and review

**Act/HUD:** THE LINEAGE · NO ORPHAN UNIT<br>
**Core line:** SeamwiseTaskPlanLineage/v1 binds engine version, intent digest, delivery-plan digest, review digest, canonical TaskPlan digest, and each unit’s seam/lane/leg/source digest.<br>
**Visual:** unit fan-in to one lineage spine.<br>
**Verification:** unit ID sets in TaskPlan and lineage must match exactly.<br>
**Sources:** [S] task-lineage schema; [I] taskspec_adapter.py; [T] lineage tests.<br>
**Transition:** “Both boundary artifacts must appear together.”

### S52 — TaskPlan and lineage commit atomically

**Act/HUD:** THE TRANSACTION · TWO FILES OR NONE<br>
**Core line:** TransactionWriter stages temporary files, honors explicitly requested modes, fsyncs staged content, swaps files, and rolls back on failure under one workspace lock.<br>
**Visual:** two staged files cross one commit gate; partial output route is red.<br>
**Failure:** task_plan_bundle_incomplete.<br>
**Sources:** [I] io.py and compilation.py; [T] deterministic compile and projection tests.<br>
**Transition:** “Atomic write prevents partial state; independent rebuild detects coordinated edits.”

### S53 — Status regenerates the expected projection

**Act/HUD:** THE REBUILD · DO NOT TRUST OUTPUTS BECAUSE THEY AGREE WITH EACH OTHER<br>
**Core line:** status rebuilds the graph, TaskPlan, and lineage from reviewed canonical inputs and compares exact values.<br>
**Visual:** actual bundle and regenerated bundle meet at equality gate.<br>
**Stable failures:** task_plan_projection_mismatch; task_lineage_projection_mismatch.<br>
**Key insight:** editing both output files coherently still fails if they no longer match the reviewed source projection.<br>
**Sources:** [I] workspace.py and verify_task_plan_bundle; [T] coordinated-rebinding test.<br>
**Transition:** “The same lineage is exposed for human and agent inspection.”

### S54 — Inspect traces one unit through the whole chain

**Act/HUD:** THE INSPECT · UNIT → LEG → LANE → SEAM → INTENT<br>
**Core line:** <code>inspect [TASK_ID]</code> returns LINEAGE=READY for all lineage or one exact unit.<br>
**Visual:** selected TaskPlan unit highlights its ancestry.<br>
**Failure:** unknown_task or lineage_missing; no invented fallback.<br>
**Sources:** [I] compilation.py and cli.py.<br>
**Transition:** “At this point Seamwise has finished its job.”

### S55 — The boundary is an intentional stop

**Act/HUD:** THE HANDOFF · PROJECT AND NEVER DISPATCH<br>
**Core line:** final status instructs the caller to pass task-plan.json and task-plan-lineage.json to the composition coordinator.<br>
**Visual:** Seamwise blue region ends; Task-Spec/Converge begin beyond a thick contract boundary.<br>
**Machine flags:** task_specs 0; materialization_receipt false; dispatch_authorized false.<br>
**Refusal:** no task-spec console script, embedded Task Pack, tasks command, signing key, seal, handoff, execute, or accept command.<br>
**Sources:** [O] AGENTS.md/OPERATING.md; [I] capabilities, status, package layout; [T] distribution test.<br>
**Transition:** “That stop is reinforced by filesystem, locking, and tamper defenses.”

---

## ACT VI — FAIL CLOSED

### S56 — Managed paths are a security boundary

**Act/HUD:** THE FILESYSTEM · NEVER FOLLOW AN UNOWNED ESCAPE<br>
**Core line:** workspace and install targets reject symlinked roots, unsafe ancestors, regular files in directory slots, traversal, case ambiguity, and writes outside owned locations.<br>
**Visual:** project root with allowed blue tree and red symlink escape.<br>
**Sources:** [I] safety.py, io.py, installer.py; [T] fail-closed and installer tests.<br>
**Transition:** “Safe paths still need safe concurrency.”

### S57 — The workspace lock lives outside Git state

**Act/HUD:** THE LOCK · RUNTIME COORDINATION IS NOT A TRACKED ARTIFACT<br>
**Core line:** a canonical workspace identity maps to a private lock path; unsafe state/lock ancestors are refused.<br>
**Visual:** two compiler processes contend on one external lock; repository files remain untouched until the winner commits.<br>
**Boundary:** dry-run does not acquire a mutating lock or write artifacts.<br>
**Sources:** [I] io.py; [T] workspace-lock tests.<br>
**Transition:** “Inside the lock, byte-level determinism makes drift visible.”

### S58 — Canonical bytes make reruns comparable

**Act/HUD:** THE DETERMINISM · SORTED JSON, STABLE YAML, SHA-256<br>
**Core line:** canonical JSON uses sorted compact encoding; compiled outputs are byte-identical across unchanged reruns.<br>
**Visual:** two runs produce the same digest and exact file bytes.<br>
**Qualifier:** timestamps occur in review and telemetry; compilation projections remain deterministic from current inputs.<br>
**Sources:** [I] io.py, taskspec_adapter.py; [T] deterministic compile test.<br>
**Transition:** “The attack matrix shows where each digest closes the gate.”

### S59 — Tamper at any layer invalidates downstream state

**Act/HUD:** THE TAMPER MATRIX · CHANGE THE SOURCE, LOSE THE AUTHORITY<br>
**Visual:** five-row matrix.

| Tamper | Detected by | Result |
|---|---|---|
| evidence bytes | declared SHA verification | map refuses |
| seam/decision artifact | seam-map indexed digest | plan refuses |
| delivery plan | review plan digest | compile refuses |
| TaskPlan only | regenerated projection | status blocks |
| TaskPlan and lineage together | canonical rebuild from reviewed inputs | status blocks |

**Sources:** [T] fail-closed, authority/state, and adapter tests.<br>
**Transition:** “Observation records the journey but never repairs it.”

### S60 — Telemetry observes; it does not authorize

**Act/HUD:** THE TELEMETRY · EVERY EVENT SAYS AUTHORIZATION FALSE<br>
**Core line:** stage events record time, event, token, attributes, and authorization false.<br>
**Visual:** event stream beside an authority gate it cannot cross.<br>
**Failure behavior:** malformed prior telemetry is discarded and marked prior_telemetry_invalid in the next event; it does not become canonical state.<br>
**Sources:** [I] engine/support.py; [O] AGENTS.md.<br>
**Transition:** “Reports follow the same derived-only rule.”

### S61 — Reports explain verified state and create no authority

**Act/HUD:** THE REPORT · DERIVED HTML OR JSON<br>
**Core line:** report snapshots verified state and artifacts into reports/seamwise-report.html or .json.<br>
**Visual:** verified snapshot → read-only report; no arrow back into the compiler.<br>
**Gate:** any workspace integrity issue returns REPORT=BLOCKED.<br>
**Sources:** [I] reporting.py; [T] clean-room journey.<br>
**Transition:** “Agent-context is also bounded because chat surfaces are not trusted storage.”

### S62 — Agent context is portable, bounded, and incomplete by design

**Act/HUD:** THE PACKET · 64 KB PER ARTIFACT, 512 KB TOTAL<br>
**Core line:** agent-context omits absolute local paths, includes verified state and bounded artifacts, hashes omitted values, and names the exact next command.<br>
**Visual:** large artifact becomes hash + bytes + omission reason inside a fixed packet frame.<br>
**Boundary:** packet output can guide proposals; it cannot prove local execution or review.<br>
**Sources:** [I] reporting.py; [T] packet-limit tests.<br>
**Transition:** “Preview behavior must obey the same no-write promise.”

### S63 — Dry-run validates and previews without writes

**Act/HUD:** THE DRY RUN · SAME BOUNDARIES, ZERO FILESYSTEM EFFECT<br>
**Core line:** global <code>--dry-run</code> preserves tokens and diagnostics while writers retain touched previews only in memory.<br>
**Visual:** compiler pipeline produces ghost artifacts; filesystem remains unchanged.<br>
**Proof:** mapping dry-run and installer dry-run tests assert no target state.<br>
**Sources:** [I] Writer/TransactionWriter and CLI; [T] dry-run tests.<br>
**Transition:** “The final security boundary is what Seamwise never receives.”

### S64 — Seamwise never receives downstream authority

**Act/HUD:** THE SECRET BOUNDARY · NO TASK-SPEC KEYS OR CREDENTIALS<br>
**Core line:** Task-Spec is not a runtime dependency; Seamwise requires no Task-Spec signing key, provider credential, executor token, or acceptance authority.<br>
**Visual:** secret-bearing Task-Spec/coordinator zone outside Seamwise process boundary.<br>
**Qualifier:** release clean-room validation may call an independently installed Task-Spec CLI after Seamwise exits; that is test composition, not a Seamwise runtime import.<br>
**Sources:** [O] AGENTS.md/OPERATING.md; [I] pyproject and clean_room_e2e.py; [T] no-embedded-engine test.<br>
**Transition:** “This narrow core is exposed through one CLI and one machine envelope.”

---

## ACT VII — PRODUCT SURFACE

### S65 — One binary, commands grouped by authority

**Act/HUD:** THE CLI · AUTHOR, INSPECT, HOST<br>
**Visual:** three horizontal command lanes.

| Surface | Commands |
|---|---|
| author and compile | init; recipe schema; map; plan; review; compile; prepare |
| inspect and explain | capabilities; status; next; inspect; graph; report; agent-context |
| host lifecycle | install; uninstall; doctor |

**Global controls:** --workspace; --json; --dry-run; --version.<br>
**Machine negotiation:** <code>capabilities</code> returns SeamwiseCapabilities/v1 with engine version, supported contracts/commands, materializes_tasks false, and dispatch_authority false.<br>
**Boundary:** inspect help before using options not shown in the deck.<br>
**Sources:** [I] cli.py and README.<br>
**Transition:** “Automation never parses human terminal prose.”

### S66 — Every JSON command emits exactly one result envelope

**Act/HUD:** THE ENVELOPE · SeamwiseCLIResult/v1<br>
**Core line:** contract, engine_version, schema_version, command, ok, token, exit_code, workspace, artifacts, diagnostics, next, optional data.<br>
**Visual:** preserve current HTML S11 envelope specimen.<br>
**Failure behavior:** Click usage errors and internal exceptions are wrapped in the same contract.<br>
**Boundary:** absolute workspace appears in the CLI envelope; portable agent-context intentionally omits it.<br>
**Sources:** [S] result-envelope schema; [I] result.py and cli.py; [T] exact-one-envelope tests.<br>
**Transition:** “Token and exit code together communicate the gate.”

### S67 — Exit codes separate human input from invalidity and conflict

**Act/HUD:** THE EXITS · THE NUMBER IS PART OF THE CONTRACT<br>
**Visual:** six large numbered cards.

| Exit | Meaning |
|---:|---|
| 0 | operation succeeded or reached its intended ready boundary |
| 2 | evidence, ownership, decision, or review input is required |
| 3 | command or authored contract is invalid |
| 4 | integrity, concurrency, filesystem, or topology conflict |
| 5 | required host runtime is unavailable |
| 10 | internal mechanism failure |

**Sources:** [S] result-envelope schema; [I] constants.py and CLI.<br>
**Transition:** “Host installation uses receipts so removal cannot delete unowned work.”

### S68 — Skill installation is receipt-owned and rollback-safe

**Act/HUD:** THE INSTALLER · CODEX, CLAUDE, OR BOTH<br>
**Core line:** project/user installs stage five shared skills, inventory every byte, write a private receipt, support deterministic reinstall, and refuse modified or unowned destinations.<br>
**Visual:** shared skill source fans into .agents/skills and .claude/skills; receipt spine remains private.<br>
**Failure tokens:** INSTALL=BLOCKED; INSTALL=ROLLED_BACK; UNINSTALL=BLOCKED; UNINSTALL=ROLLED_BACK.<br>
**Sources:** [I] installer.py; [S] install-receipt schema; [T] installer tests.<br>
**Transition:** “Doctor verifies runtime and host state instead of trusting manifests.”

### S69 — Doctor separates core health from host health

**Act/HUD:** THE DOCTOR · CORE, CODEX, CLAUDE, ALL<br>
**Core line:** core checks platform, Python, package version, the result-envelope schema, and Git; a selected host additionally requires its executable and verified installed receipt/tree, with a bounded live probe only when explicitly requested.<br>
**Visual:** layered health rings; missing host returns exit 5 without corrupting core state.<br>
**Platform boundary:** native Windows is unsupported; use a supported POSIX environment.<br>
**Sources:** [I] doctor.py; [T] doctor and host-plugin tests.<br>
**Transition:** “The five skills do not recreate the compiler—they drive these same commands.”

### S70 — Five skills, one CLI, no model-owned compiler

**Act/HUD:** THE SKILLS · ONE BOUNDARY PER SKILL<br>
**Visual:** preserve current HTML S12 skill sheet.

| Skill | Responsibility | Stop condition |
|---|---|---|
| seamwise | orchestrate one confirmed pass at a time | exact next safe action |
| to-seam-map | ground and validate seams | SEAM_MAP=READY or named gap |
| to-delivery-plan | lanes, legs, thread, objections, review | DELIVERY_PLAN=READY |
| to-task-graph | dependency-safe graph and critical path | TASK_GRAPH=READY |
| to-task-specs | project TaskPlan plus lineage | dispatch_authorized false, then stop |

**Boundary:** each skill treats model output as proposed until CLI validation.<br>
**Sources:** [I/D] skills/*/SKILL.md and host manifests.<br>
**Transition:** “The conversation itself follows a five-pass authoring contract.”

### S71 — Chat asks one question, one pass, one confirmation

**Act/HUD:** THE CHAT · PROPOSE, SHOW, WAIT<br>
**Core line:** delivery intent → evidence/system → seams/ownership → capability/proof → task contracts.<br>
**Visual:** five pass cards with a confirmation gate between each.<br>
**Rules:** exactly one concise unanswered question; show the complete pass; wait for confirmation; run only the current transformation; never auto-review.<br>
**Boundary:** start a new host session after skill installation; install/list success is not fresh-session invocation proof.<br>
**Sources:** [I] reporting._recipe_authoring_guide; [D] skills; [T] agent-context tests.<br>
**Transition:** “Now test what the repository can actually prove.”

---

## ACT VIII — PROOF AND EVOLUTION

### S72 — The test suite attacks authority, not only happy paths

**Act/HUD:** THE TESTS · POSITIVE, ADVERSARIAL, TAMPER, COLLISION, FAILURE ROUTE<br>
**Visual:** six proof corridors.

1. contracts and exact CLI envelopes;
2. authority, review, status, context, and state;
3. evidence, path, topology, and projection fail-closed behavior;
4. complete rate-limiting journey;
5. host installer and doctor;
6. external TaskPlan boundary.

**Current local proof:** 113 tests passed; 79.02% total branch-aware coverage exceeded 78% floor.<br>
**Boundary:** passing tests do not erase the later documentation-gate failure.<br>
**Sources:** [T] tests and local 2026-08-26 run.<br>
**Transition:** “The strongest integration proof installs the wheel in a clean room.”

### S73 — Clean-room proof crosses the external boundary without merging authority

**Act/HUD:** THE CLEAN ROOM · WHEEL → WORKSPACE → TASKPLAN VALIDATION<br>
**Core line:** the isolated fixture is designed to prove schema source, evidence tamper refusal, complete compile, exact two-artifact output, independent Task-Spec 3.8.0 plan validation, report, skill install/reinstall/uninstall, and no tasks directory.<br>
**Visual:** temporary environment with Seamwise and independently located Task-Spec binaries.<br>
**Pinned external:** Task-Spec 3.8.0 at commit 0e6180cfc3009bd4ef9cf7ab050b463e10d4af91.<br>
**Current-run qualifier:** this step exists in make check but did not execute after the README docs failure on 2026-08-26.<br>
**Sources:** [I/T] clean_room_e2e.py and release workflow.<br>
**Transition:** “The release boundary sequences that proof with packaging and host checks.”

### S74 — Make check is the release boundary

**Act/HUD:** THE RELEASE GATE · ORDER MATTERS<br>
**Core line:** shellcheck → locked sync → format → lint → strict mypy → tests/coverage → host manifests → docs → build → release assets → doctor → live host plugins → clean room → Git whitespace.<br>
**Visual:** long gate rail; current failure stops at docs.<br>
**Release workflow:** tags matching VERSION verify on Ubuntu and macOS, build checksummed assets and SeamwiseReleaseManifest/v1, then publish an immutable GitHub release.<br>
**Boundary:** later steps are not assumed when an earlier step fails.<br>
**Sources:** [I] release-check.sh, release-assets.py, workflows.<br>
**Transition:** “Frozen v0.2.0 and current main answer different questions.”

### S75 — Released, current-main, documentary, and removed

**Act/HUD:** THE STATUS · DO NOT FLATTEN TIME<br>
**Visual:** four status columns.

| Label | Meaning | Seamwise example |
|---|---|---|
| released | frozen at v0.2.0 | external Task-Spec boundary, two-artifact compile |
| current-main | 33 commits beyond tag | engine split, branch coverage, guides, brand assets, README diagrams |
| documentary | explanatory and checked against code | README, CLAUDE.md, current HTML primer |
| removed/historical | recoverable from Git, not current authority | docs/seamwise.pdf, old docs tree, embedded Task Pack |

**Sources:** [R/C] Git tag/log and CHANGELOG.md.<br>
**Transition:** “Current main has strong local proof and one explicit open drift.”

### S76 — Current main is not release-ready today

**Act/HUD:** THE GAP · DOCUMENTATION VALIDATOR DRIFT<br>
**Core line:** current make check fails because README Mermaid theme directives precede the graph declaration expected by validate_docs.py.<br>
**Visual:** green proof rail through tests/coverage/host manifests, red stop at docs, gray unexecuted later gates.<br>
**Exact boundary:** no claim that build, doctor, live host-plugin, clean-room, or whitespace steps passed in this invocation.<br>
**Repair options outside this deck task:** allow Mermaid init directives in the validator or remove/move those directives; rerun the complete gate.<br>
**Sources:** [C/T] local command output; scripts/validate_docs.py; README.md.<br>
**Transition:** “The largest historical change explains why the present boundary is so narrow.”

### S77 — v0.2 removed the embedded engine and restored product boundaries

**Act/HUD:** THE MIGRATION · FROM BUNDLED TASK PACK TO EXTERNAL CONTRACT<br>
**Core line:** v0.1 embedded Task-Spec behavior; v0.2 emits reviewed TaskPlan plus lineage and stops.<br>
**Visual:** before/after boundary diagram.

| Removed | Replacement |
|---|---|
| bundled Task Pack | independently installed Task-Spec |
| task-spec console script | Seamwise capabilities + external negotiation |
| seamwise tasks emit/validate/preflight/seal | external Task-Spec CLI |
| direct Task-Spec skill installation | five Seamwise-only host skills |
| compile materializes tasks | compile writes two reviewed boundary artifacts |

**Sources:** [R] CHANGELOG 0.2.0; [O] README migration; [T] distribution test.<br>
**Transition:** “The close is the boundary, not the feature count.”

### S78 — Cut along real seams. Project—and stop.

**Act/HUD:** CLOSE · THE INVARIANT<br>
**Core line:** preserve the current closing rhythm:

> SEAMWISE decomposes.<br>
> Task-Spec contracts.<br>
> Converge coordinates.

**Visual:** reprise the blue seam, gold capability chain, green TaskPlan frame, and hard stop before dispatch.<br>
**Five takeaways:** ground; cut; own; prove; review; project; stop.<br>
**Reviewer route:**

~~~bash
seamwise --version
seamwise --json capabilities
seamwise --workspace /path/to/project --json status
make check
~~~

**Final qualifier:** at the audited current commit, the first three product
surfaces are inspectable, tests and coverage pass, and the full release gate
still stops at current README Mermaid validation drift.<br>
**End line:** “A good decomposition does not create more tasks. It creates the right proof-bearing boundaries before any task receives authority.”

---

## 6. Construction-ready visual library

Use these Mermaid sources as layout references. Rebuild with native HTML/CSS
when Mermaid cannot preserve the existing Seamwise visual system.

### A. Complete authority chain

~~~mermaid
flowchart LR
    H["Human-approved initiative"] --> R["Authored recipe"]
    R --> M["map"]
    M --> S["Seam map"]
    S --> P["plan"]
    P --> D["Delivery plan"]
    D --> V{"Human review"}
    V --> C["compile"]
    C --> TP["TaskPlan/v1"]
    C --> LI["Lineage/v1"]
    TP --> X["External coordinator"]
    LI --> X
    X --> TS["Task-Spec"]
~~~

### B. Claim and evidence boundary

~~~mermaid
flowchart TB
    C["claim class"] --> E["evidence record"]
    U["local URI/path"] --> E
    T["captured_at"] --> E
    H["SHA-256"] --> E
    E --> R["recipe"]
    R --> M["validated seam map"]
    M -. "does not prove" .-> W["real-world implementation"]
~~~

### C. Seam anatomy

~~~mermaid
flowchart LR
    A["consumes"] --> J["SEAM\nresponsibility\nowner\nevidence"]
    J --> B["produces"]
    P["independent proof"] --> J
    D["accepted decisions"] --> J
    X["rejected alternatives"] --> J
    J --> L["one owning swimlane"]
~~~

### D. Grammar and lineage

~~~mermaid
flowchart TB
    I["Delivery Intent"] --> S["Seam"]
    S --> W["Owning swimlane"]
    W --> L["Capability leg"]
    L --> T["Runnable task contract"]
    T --> U["TaskPlan unit"]
    U --> X["Lineage entry"]
~~~

### E. Capability/task dual graph

~~~mermaid
flowchart TB
    CA["Capability A produced"] --> CB["Capability B requires A"]
    TA["Task A"] --> TB["Task B"]
    CA -. "owned by" .-> TA
    CB -. "owned by" .-> TB
~~~

### F. Review digest joint

~~~mermaid
flowchart LR
    D["Draft delivery plan"] -->|"draft_sha256"| A["Human authority record"]
    A -->|"review_authority_sha256"| P["READY delivery plan"]
    P -->|"plan_sha256"| R["DeliveryPlanReview/v1"]
~~~

### G. Projection rebuild

~~~mermaid
flowchart TB
    R["Reviewed canonical inputs"] --> G["Rebuild graph"]
    G --> EP["Expected TaskPlan"]
    G --> EL["Expected lineage"]
    AP["Actual TaskPlan"] --> EQ{"Exact equality"}
    AL["Actual lineage"] --> EQ
    EP --> EQ
    EL --> EQ
    EQ -->|"match"| OK["STATUS=READY"]
    EQ -->|"drift"| B["STATUS=BLOCKED"]
~~~

### H. Product boundary

~~~mermaid
flowchart LR
    SW["Seamwise\nreviewed topology"] --> TP["TaskPlan/v1 + lineage"]
    TP --> CV["Coordinator\nnegotiation + sequence"]
    CV --> TS["Task-Spec\nmaterialize + authorize + accept"]
    TS --> EX["Executor / TaskMesh"]
~~~

### I. Failure funnel

~~~mermaid
flowchart TB
    A["Authored recipe"] --> E{"Evidence?"}
    E -->|missing| E2["exit 2"]
    E -->|valid| O{"Owner/decision?"}
    O -->|missing| O2["exit 2"]
    O -->|valid| G{"Graph/path integrity?"}
    G -->|invalid| G4["exit 3 or 4"]
    G -->|valid| H{"Human review?"}
    H -->|missing| H2["exit 2"]
    H -->|current| R["READY"]
~~~

### J. Release gate

~~~mermaid
flowchart LR
    L["lint/typecheck"] --> T["tests + coverage"]
    T --> H["host manifests"]
    H --> D["docs"]
    D --> B["build/assets"]
    B --> DR["doctor"]
    DR --> HP["host plugin E2E"]
    HP --> C["clean room"]
    C --> G["Git checks"]
    D -. "current-main stop" .-> F["Mermaid init drift"]
~~~

---

## 7. Comparison table bank

Use each table on at most one slide.

### Prompt decomposition vs Seamwise

| Prompt-only decomposition | Seamwise decomposition |
|---|---|
| evidence can disappear into chat | evidence source, capture time, and digest are explicit |
| ownership is inferred | seam and lane name the same owner |
| steps are activities | legs are observable capability states |
| order follows prose | graph proves dependencies and contentions |
| review is a conversational “looks good” | receipt binds exact plan bytes |
| output may become tasks immediately | output stops at TaskPlan plus lineage |

### Seam vs component

| Component | Seam |
|---|---|
| names a structural unit | names a responsibility boundary |
| may share authority | has one owner |
| may lack an external contract | states consumes and produces |
| testing may require the whole system | carries independent proof |
| existence can be incidental | rejected alternatives justify the cut |

### Swimlane vs team

| Team | Swimlane |
|---|---|
| organizational identity | delivery jurisdiction for one seam |
| can own many unrelated concerns | owns one accepted boundary |
| may read and write broadly | write/proof scope is explicit |
| membership can change | owner identity is part of reviewed topology |

### Capability leg vs task

| Capability leg | Task |
|---|---|
| observable system state | bounded change unit |
| states requires/produces | states depends_on |
| proved by one or more tasks | carries behavior/evals |
| architecture-level progress | future Task-Spec leaf input |

### Review vs Task-Spec seal

| Seamwise review | Task-Spec seal |
|---|---|
| accepts topology | authorizes one task revision |
| binds delivery-plan bytes | binds TaskRevision under Task-Spec policy |
| before TaskPlan projection | after task materialization and PRE |
| no dispatch authority | may make a leaf dispatch-eligible |

### Seamwise vs Task-Spec vs Converge

| Dimension | Seamwise | Task-Spec | Converge |
|---|---|---|---|
| primary object | reviewed decomposition | atomic task contract/receipts | composed lifecycle |
| topology | owns seams/lanes/legs | consumes approved TaskPlan | sequences engines |
| materialization | never | owns | invokes external engine |
| authorization | never | owns | coordinates, does not replace |
| execution | never | reference/runtime surfaces | factory loop/binding |
| acceptance | never | owns | settles using engine results |

### Schema validity vs readiness

| State | What it proves | What it does not prove |
|---|---|---|
| recipe schema valid | shape and bounded vocabulary | evidence truth |
| SEAM_MAP=READY | evidence/ownership/decision seam checks | human topology acceptance |
| DELIVERY_PLAN=READY | current human review receipt | runnable implementation |
| TASK_GRAPH=READY | graph/path/projection validity | task authorization |
| STATUS=READY | current bundle matches reviewed inputs | delivery complete |

### Exit codes

| Exit | Category | Typical human response |
|---:|---|---|
| 0 | ready/success | inspect artifacts and continue |
| 2 | input/authority needed | supply evidence, owner, decision, or review |
| 3 | invalid authored/command contract | correct syntax or schema |
| 4 | conflict/integrity/topology | investigate; do not overwrite |
| 5 | unavailable host | install or enable the required runtime |
| 10 | mechanism failure | capture diagnostics and stop |

### Released vs current main

| Surface | v0.2.0 release | Current main audit |
|---|---|---|
| two-artifact boundary | released | retained |
| engine package split | not frozen in tag | Unreleased |
| branch coverage floor | not frozen in tag | 78%, locally reached 79.02% |
| brand/README diagrams | earlier surface | current-main additions |
| complete local gate on 2026-08-26 | not re-proved here | fails at README Mermaid docs validation |

---

## 8. Code specimen bank

Never show a complete real consumer recipe. Use focused, sanitized fragments
based on the repository fixture.

### Everyday path

~~~bash
seamwise --workspace "/path/to/project" init
seamwise --workspace "/path/to/project" recipe schema
seamwise --workspace "/path/to/project" map --source seamwise-recipe.yaml
seamwise --workspace "/path/to/project" plan
seamwise --workspace "/path/to/project" review \
  --accept --reviewer "human-name" --reason "Topology accepted."
seamwise --workspace "/path/to/project" compile
seamwise --workspace "/path/to/project" status
~~~

### Source record

~~~yaml
source:
  uri: evidence/blueprint.md
  captured_at: "2026-08-02T00:00:00Z"
  sha256: f40ed16c2898b8363dfce1c19e7c3fd539d52810d52b21faeaf59323117af445
~~~

### Seam specimen

~~~yaml
id: SEAM-POLICY-CONTRACT
responsibility: Define and validate versioned policy data.
consumes: [authored organization policy]
produces: [validated policy document]
owner: platform-contracts
independent_proof: Invalid limits fail schema validation.
rejected_alternatives:
  - alternative: Treat the API handler as the boundary
    reason: It would mix contract, resolution, and enforcement.
~~~

### Capability leg specimen

~~~yaml
id: LEG-EFFECTIVE-POLICY-RESOLVED
observable_state: Every organization has one effective policy
proof: Precedence tests return one decision with provenance.
requires: [validated policy document]
produces: [effective policy decision]
~~~

### Traceability specimen

~~~yaml
behavior:
  - id: B-1
    given: a valid organization override
    when: effective policy is resolved
    then: the override and provenance are returned
  - id: B-2
    given: no organization override
    when: effective policy is resolved
    then: the validated default is returned
~~~

### Review receipt shape

~~~json
{
  "schema_version": 1,
  "disposition": "accepted",
  "reviewer": "human-name",
  "reason": "The boundaries and proof chain are acceptable.",
  "reviewed_at": "2026-08-26T00:00:00Z",
  "draft_sha256": "…",
  "plan_sha256": "…",
  "fixture": false
}
~~~

### TaskPlan header

~~~json
{
  "api_version": "taskspec.dev/v1",
  "kind": "TaskPlan",
  "approved": true,
  "metadata": {
    "producer": "seamwise",
    "producer_version": "0.2.0",
    "delivery_plan_sha256": "…",
    "delivery_plan_review_sha256": "…"
  }
}
~~~

### Lineage unit

~~~json
{
  "T-20260802-effective-policy": {
    "unit_id": "T-20260802-effective-policy",
    "intent": "DI-RATE-LIMIT",
    "seam": "SEAM-POLICY-RESOLUTION",
    "swimlane": "LANE-POLICY-RESOLUTION",
    "leg": "LEG-EFFECTIVE-POLICY-RESOLVED",
    "source_sha256": "…"
  }
}
~~~

### Result envelope

~~~json
{
  "contract": "SeamwiseCLIResult/v1",
  "command": "status",
  "ok": true,
  "token": "STATUS=READY",
  "exit_code": 0,
  "artifacts": [],
  "diagnostics": [],
  "next": ["Pass task-plan.json and lineage to the coordinator."],
  "data": {
    "task_specs": 0,
    "materialization_receipt": false,
    "dispatch_authorized": false
  }
}
~~~

### Stable failure family

~~~text
MAP:       SEAM_MAP=NEEDS_DISCOVERY · NEEDS_OWNER_INPUT · AMBIGUOUS
PLAN:      DELIVERY_PLAN=OPEN_OBJECTIONS · NEEDS_REVIEW
GRAPH:     TASK_GRAPH=CYCLE · COLLISION · UNPROVABLE_NODE
STATUS:    STATUS=BLOCKED
HOST:      INSTALL=BLOCKED · DOCTOR=BLOCKED
MECHANISM: CLI=ERROR · exit 10
~~~

---

## 9. Presenter route and timing

The 78-slide architecture is a deep-dive library. Select a route; never rush
all 78 into a keynote slot.

| Route | Slides | Time | Audience outcome |
|---|---:|---:|---|
| Executive category | 01–08, 18, 24, 39–40, 50–55, 75–78 | 25–30 min | understands the product, review barrier, handoff, and status honesty |
| Architecture practitioner | 01–55, 59, 64, 72, 75–78 | 90–110 min | can reason from evidence through reviewed TaskPlan |
| Operator and host | 01–08, 33–42, 52–71, 72–76, 78 | 70–90 min | can operate gates, inspect failure, and install hosts safely |
| Security/reviewer | 01–08, 09–17, 30–32, 39–41, 45–64, 72–76, 78 | 75–90 min | understands authority, tamper, filesystem, and proof limits |
| Full deep dive | 01–78 plus demos | 3–3.5 hours | understands complete grammar, runtime boundary, and evidence posture |

### Demo placement

Use four bounded disposable-workspace demos:

1. **After S17:** inspect recipe schema and show one immutable local evidence record.
2. **After S42:** run init → map → plan and stop at DELIVERY_PLAN=NEEDS_REVIEW.
3. **After S55:** accept a fixture plan, compile, inspect one unit, and show dispatch_authorized false.
4. **After S76:** run make check in the Seamwise source checkout and show the exact current docs drift.

Never use a live customer repository, private evidence body, production
credential, or real reviewer identity in the deck.

### Audience checks

- After S08: “Which step is a human authority transition?”
- After S17: “Which bytes are authored and which are derived?”
- After S23: “Is this phrase an observable state or an activity?”
- After S32: “What evidence would make these siblings safe to overlap?”
- After S40: “What exact bytes did the reviewer accept?”
- After S53: “Why does coordinated output tampering still fail?”
- After S55: “Which product may create task authority next?”
- After S67: “Why can exit 2 be a successful stop?”
- After S76: “Which gate steps remain unproved in this run?”

---

## 10. Build order

1. Snapshot the current 13-slide HTML visually and structurally before edits.
2. Map every current slide to its new slide number and record preserve/refine/supersede.
3. Preserve the signed visual grammar, title treatment, seam diagrams, authority trio, first journey, TaskPlan specimen, CLI envelope, skill sheet, and closing invariant.
4. Build S01 only; validate brand, version qualifier, keyboard behavior, and mobile overflow.
5. Continue one slide at a time through each act.
6. After each slide, verify copy against its named source and add source labels to speaker notes.
7. After each act, review causal transitions, repeated definitions, and token consistency.
8. Use fixture-derived code only; sanitize hashes, reviewer identity, and paths.
9. Re-run the source audit before publishing any “current” claim.
10. Re-run the full Seamwise release gate before changing S76 to green.
11. Perform automated HTML, anchor, asset, accessibility, reduced-motion, and overflow checks.
12. Perform visual QA at 1440×900, 1920×1080, 1366×768, and 390×844.
13. Run the executive, practitioner, operator, and reviewer routes aloud.
14. Remove any slide that cannot state its evidence basis, boundary, and transition.

### Current-slide migration map

| Existing HTML slide | New architecture home | Default action |
|---|---:|---|
| Title | S01 | preserve with current-main qualifier |
| Why seams | S05 | preserve visual, tighten evidence language |
| How a seam works | S06–S07 | split anatomy from readiness checks |
| How swimlanes work | S21–S22 | preserve pool visual |
| How legs work | S23–S24 | split leg from steel thread |
| Pass by pass | S18 | preserve and expand lineage |
| Three products | S04 and S55 | reuse category and stop boundary |
| First journey | S08 and S33–S42 | preserve overview; expand mechanics |
| Inside TaskPlan | S50–S51 | preserve specimen; separate lineage |
| Fail closed | S52–S64 | preserve summary; expand attacks |
| CLI surface | S65–S67 | preserve envelope; split commands/exits |
| Five skills | S70–S71 | preserve sheet; add conversation contract |
| Close | S78 | preserve invariant and remove duplicated wordmark line if still present |

### Per-slide acceptance checklist

- [ ] One idea and one primary visual.
- [ ] Headline states the causal point, not only the topic.
- [ ] Description beneath the headline is readable without speaker notes.
- [ ] Seam, lane, leg, task, review, and seal terms are not conflated.
- [ ] Current/released/proposed/external status is explicit.
- [ ] Token spelling and exit code match source.
- [ ] No output success is overstated as implementation or delivery.
- [ ] No downstream authority is assigned to Seamwise.
- [ ] Code and identifiers come from schemas or sanitized fixture evidence.
- [ ] No real credential, private evidence, absolute consumer path, or reviewer identity appears.
- [ ] Cards are left-aligned and vertically centered.
- [ ] Connectors use the signed luminous-line grammar.
- [ ] Code uses the signed macOS window component.
- [ ] Source labels and paths exist in speaker notes.
- [ ] Transition makes the next slide inevitable.
- [ ] No clipping at all four target viewports.
- [ ] Keyboard navigation and reduced motion still work.
- [ ] Slide works without the agenda visible.

---

## 11. Failure and repair matrix

Use this as a speaker-note and troubleshooting source. Do not crowd it onto one
slide.

| Stage | Trigger | Token / exit | Honest repair |
|---|---|---|---|
| init | unsafe managed path | WORKSPACE=BLOCKED / 4 | remove unsafe file/symlink or choose a safe workspace |
| init | existing starter documents | WORKSPACE=EXISTS / 4 | inspect; use force only for the two documented starters |
| map | no evidence | SEAM_MAP=NEEDS_DISCOVERY / 2 | capture and cite immutable local evidence |
| map | remote-only evidence | NEEDS_DISCOVERY / 2 | create a local hash-matched snapshot |
| map | evidence hash drift | conflict / 4 | recapture intentionally and author a revised recipe |
| map | owner absent/mismatch | NEEDS_OWNER_INPUT / 2 | name one owner consistently |
| map | decision proposed | NEEDS_ARCHITECTURE_DECISION / 2 | obtain owner decision and rationale |
| map | duplicate IDs/blank semantics | AMBIGUOUS or ERROR / 3 | correct the authored contract |
| map | path invalid or contradictory | AMBIGUOUS / 3 or 4 | use canonical bounded paths |
| plan | open system unknown | NEEDS_ARCHITECTURE_DECISION / 2 | resolve in sourced input and remap cleanly |
| plan | OPEN objection | OPEN_OBJECTIONS / 2 | owner fixes or explicitly accepts with rationale |
| plan | prior projection would change | NEEDS_ARCHITECTURE_DECISION / 4 | archive explicitly or use a clean workspace |
| review | missing --accept | NEEDS_REVIEW / 2 | obtain explicit human acceptance |
| review | plan changed | NEEDS_REVIEW / 4 | regenerate and review exact new bytes |
| compile | review stale/missing | TASK_GRAPH=BLOCKED / 2 or 4 | review the current plan |
| compile | cycle | TASK_GRAPH=CYCLE / 4 | correct dependency or contention order |
| compile | capability causality missing | UNPROVABLE_NODE / 4 | add real producer/dependency structure |
| compile | write overlap unordered | TASK_GRAPH=COLLISION / 4 | order, declare contention, or redesign boundaries |
| status | projection changed | STATUS=BLOCKED / 4 | restore/recompile from reviewed inputs; never hand-edit green |
| install | destination unowned/modified | INSTALL=BLOCKED / 4 | preserve user files; select a clean owned target |
| install | staged transaction fails | INSTALL=ROLLED_BACK / 4 | inspect mechanism; retry only after cause is fixed |
| doctor | required host unavailable | DOCTOR=BLOCKED / 5 | install/enable the named host and rerun |
| any | internal exception | CLI=ERROR / 10 | preserve diagnostics and stop |

---

## 12. Canonical source index

### Ownership and lifecycle

- /Users/luanmorenomaciel/GitHub/seamwise/OPERATING.md
- /Users/luanmorenomaciel/GitHub/seamwise/AGENTS.md
- /Users/luanmorenomaciel/GitHub/seamwise/README.md
- /Users/luanmorenomaciel/GitHub/seamwise/CLAUDE.md
- /Users/luanmorenomaciel/GitHub/seamwise/CHANGELOG.md

### Machine contracts

- schemas/recipe.schema.json
- schemas/seam-map.schema.json
- schemas/delivery-plan.schema.json
- schemas/delivery-plan-review.schema.json
- schemas/task-graph.schema.json
- schemas/task-lineage.schema.json
- schemas/result-envelope.schema.json
- schemas/install-receipt.schema.json

### CLI and state

- src/seamwise/cli.py
- src/seamwise/constants.py
- src/seamwise/result.py
- src/seamwise/workspace.py
- src/seamwise/reporting.py
- src/seamwise/doctor.py
- src/seamwise/installer.py

### Compiler stages

- src/seamwise/engine/support.py
- src/seamwise/engine/recipe.py
- src/seamwise/engine/seams.py
- src/seamwise/engine/planning.py
- src/seamwise/engine/graph.py
- src/seamwise/engine/compilation.py
- src/seamwise/taskspec_adapter.py

### Filesystem and integrity

- src/seamwise/io.py
- src/seamwise/safety.py
- src/seamwise/contracts.py
- src/seamwise/render.py

### Host skills

- skills/seamwise/SKILL.md
- skills/to-seam-map/SKILL.md
- skills/to-delivery-plan/SKILL.md
- skills/to-task-graph/SKILL.md
- skills/to-task-specs/SKILL.md
- .codex-plugin/plugin.json
- .claude-plugin/plugin.json
- .agents/plugins/marketplace.json
- .claude-plugin/marketplace.json

### Release and packaging

- pyproject.toml
- VERSION
- Makefile
- scripts/release-check.sh
- scripts/release-assets.py
- scripts/validate_docs.py
- scripts/validate_host_adapters.py
- scripts/host_plugin_e2e.py
- scripts/clean_room_e2e.py
- .github/workflows/ci.yml
- .github/workflows/release.yml

### Tests carrying the hardest claims

- tests/test_fail_closed.py
- tests/test_authority_and_state.py
- tests/test_contracts_cli.py
- tests/test_e2e_rate_limiting.py
- tests/test_taskspec_adapter.py
- tests/test_installer.py
- tests/test_doctor.py
- tests/fixtures/rate-limiting-recipe.yaml
- tests/fixtures/blueprint.md

### Presentation references

- presentation/seamwise.html
- presentation/task-spec.md
- assets/seamwise-icon.svg

---

## 13. Editorial and terminology rules

- Write **SEAMWISE** for display headlines and **Seamwise** in prose and code context.
- Say **approved initiative** for the input; do not call raw ideation compiler-ready.
- Say **seam** only for an evidence-backed responsibility boundary.
- Say **owning swimlane** for the one lane attached to a seam.
- Say **capability leg** for an observable state plus proof.
- Say **steel thread** for the smallest ordered proving path, not the whole delivery plan.
- Say **task contract** or **future leaf input** inside the recipe; do not say a Task-Spec file exists.
- Say **human review** for delivery-plan topology acceptance.
- Say **Task-Spec seal** only for downstream Task-Spec authorization; never call Seamwise review a seal.
- Say **TaskPlan/v1 plus digest-bound lineage** for compile output.
- Say **projects** or **emits**; never say materializes.
- Say **composition coordinator** at the handoff boundary; name Converge only when that exact composition is in scope.
- Say **dispatch_authorized false** as a contract invariant, not a missing feature toggle.
- Say **derived report** and **derived graph**; neither is canonical authority.
- Say **current-main** for behavior after v0.2.0 and **released** only for frozen tag evidence.
- Say **local proof** for the 2026-08-26 test result; do not turn it into hosted or production proof.
- State that the full current-main release gate fails at documentation validation until repaired and rerun.
- Do not cite removed docs/seamwise.pdf as current authority.
- Do not imply the old v0.1 embedded Task Pack remains supported.
- Never present telemetry, model output, chat packets, reports, or slide copy as approval.
- Never imply that a valid graph proves semantic correctness, product success, or implementation completion.
- The final promise is better architecture authority before task authority—not guaranteed delivery.

---

## 14. Publication gate for the finished deck

The deck is publishable only when all conditions below are directly verified:

- [ ] Every slide maps to exactly one section in this file.
- [ ] Every current claim was refreshed against the live Seamwise checkout.
- [ ] v0.2.0 release claims and current-main claims are visually distinct.
- [ ] The current make check result is rerun and S76 matches the observed result.
- [ ] If the Mermaid drift is repaired, all later release-gate steps are observed before the deck says green.
- [ ] Every token, exit code, field, path, and command matches source.
- [ ] The 13-slide baseline was migrated intentionally, not overwritten wholesale.
- [ ] All local assets and links resolve.
- [ ] Every slide passes the four viewport checks.
- [ ] No text clips, overflows, or falls below the viewport.
- [ ] Keyboard, Home/End, Page Up/Down, tracker, and progress behaviors work.
- [ ] Reduced-motion mode avoids nonessential animation.
- [ ] Contrast and focus states remain accessible.
- [ ] Speaker notes carry evidence labels and exact paths.
- [ ] Code specimens contain no secrets or private source bodies.
- [ ] The executive and full routes both tell a coherent story.
- [ ] The final slide ends at the external boundary and does not imply dispatch.

The closing standard is simple:

> Every cut must name its evidence. Every seam must name its owner. Every leg
> must name an observable state. Every edge must name its causality. Every
> review must bind exact bytes. Every handoff must stop at the authority it
> actually owns.
