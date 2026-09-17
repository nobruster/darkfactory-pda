# 16 · Pass 1 — Intent · then stop

- Slide: DIG · Show · Converge · the spine, then Hands-On Execute 14–16
- Slice: **F · Spine**
- Who: every seat, through **their** agent, gated by `cvg`
- Next: [`17-research.md`](17-research.md) — then the Night closes. Tomorrow recaps 0–1, Binds, then Structure.

The tech-spec **answers the BRD**. It does not pick a lakehouse. Make it as clear as the brief. If `cvg` is missing, still write the file.

---

## What a good tech-spec looks like tonight

Write `docs/tech-spec-type-01-card-settlement.md` with these headings:

1. **The brief, restated** — one page, no new facts.
2. **Requirements** — keep the lie; refuse a mismatch; Type 01 steel thread; five types exist; Type 06 out of scope.
3. **Truth roles on this tree** — inbound `spec/`, judge `contracts/`, frozen `legacy/` `gen/` `infra/`, observation `evidence/`.
4. **What the second plant must not do** — first write is later, and is not SFTP; do not import Java; do not repair 173.44.
5. **Open questions** — owned, dated, no silent defaults. Stack is not an answer.

---

## Prompt (verbatim)

```text
You are Pass 1 Intent on NorthWind Pay. Human-led. No product code.

Read the Capture BRD at docs/brd-type-01-card-settlement.md.
Draft docs/tech-spec-type-01-card-settlement.md that answers that brief.

Use these headings:
1. The brief, restated
2. Requirements
3. Truth roles on this tree
4. What the second plant must not do
5. Open questions

It must:
- restate the lie and the refusal as requirements
- name inbound vs judge vs frozen plant
- say the first write of the second plant is later, and is not SFTP

It must not:
- pick DuckDB, dbt, a lakehouse, or any stack
- write ADRs
- cut seams
- create modern/
- repair 173.44
- open Type 06
```

Then gate it:

```bash
cvg intent --draft docs/tech-spec-type-01-card-settlement.md --json
```

## Proof

The file exists. The room can restate it with the file closed. `CHECK_TECH_SPEC=PASS` if `cvg` sits. No ADRs presented as signed. No Type `06`. No repair of `173.44`.

## Then stop

Point at tomorrow: Pass 2 Structure → 3 Decompose → 4 Consensus, then the first modern write. An unsigned tech-spec is not a license to code.

## If fail

Return to the failing requirement. Do not invent a stack to go green. Do not run Pass 2–8 tonight.
