# 12 · Second Brain — NotebookLM (the whole drop)

- Slide: DIG · Show · Second Brain, then Hands-On Execute 12
- Slice: **D · Brain**
- Who: every seat, their **own** notebook. Google account. Not the coding workspace.
- Pack: [`brain/notebooklm/northwind-pay-brain.zip`](../../brain/notebooklm/northwind-pay-brain.zip)
- Next: [`13-ontolayer.md`](13-ontolayer.md)

The brain is **NorthWind Pay**, all five live types, the whole week. Type `01` is the steel thread we run tonight — not the only thing in the drop. Days 2–5 keep asking **this** notebook. Do not rebuild it tomorrow.

Everyone builds their own. One empty notebook. The zip is the handout — **unzip it**, then upload the nine Markdown files. NotebookLM does not ingest a `.zip` as a source.

`spec/` stays on disk. This notebook is the **human** brain. Capture still reads the repo.

Rebuild whenever inbound changes:

```bash
bash brain/notebooklm/build.sh
```

---

## From an empty notebook — do this in order

### 1. Open a blank notebook

1. Go to [https://notebooklm.google.com](https://notebooklm.google.com)
2. Sign in with Google
3. **New notebook**
4. Rename it: `NorthWind Pay · estate`

You should see an empty notebook: no sources, no chat yet.

### 2. Unpack the zip (do not upload the zip)

From the repo root:

```bash
unzip -l brain/notebooklm/northwind-pay-brain.zip
unzip -o brain/notebooklm/northwind-pay-brain.zip -d /tmp/nw-brain
```

You want these nine files, nothing else:

```text
00-how-this-notebook-thinks.md
01-estate.md
02-five-types.md
03-type-01-inbound.md
04-type-02-inbound.md
05-type-03-inbound.md
06-type-04-inbound.md
07-type-05-inbound.md
08-the-lie.md
```

If someone uploads the `.zip` itself, it will fail. That is expected. Unzip, then upload the `.md` files.

### 3. Inject the sources

1. In the notebook, **Add sources**
2. **Upload**
3. Select **all nine** `.md` files in one go
4. Wait until the source list shows **9** and each is ready

Do not add `contracts/`. Do not add `legacy/`. Do not add a `.dat`.

### 4. Ask these, verbatim, in order

Paste one question. Wait. Then the next. Write the lie (Q5) on the table card.

**Q1 — who asked, what is out of scope**

```text
Who is Helena Dias, what did she ask the modernization team to do, and what is out of scope for this drop?
```

**Q2 — the five types**

```text
Name the five live file types in this drop. What is Type 01, 02, 03, 04, and 05 in one line each? What is Type 06?
```

**Q3 — done means**

```text
What does “done” mean for an accepted batch, for a refusal, and for a source lie?
```

**Q4 — Type 01 physically (tonight’s steel thread)**

```text
What is Type 01 physically? Encoding, record shapes, overpunch. Cite the layout.
```

**Q5 — the lie (this is the retrieval)**

```text
On the source lie: what does the Type 01 trailer declare, what do the detail rows add to, and what must the new plant not do? Does Marina say the same shape exists on PIX, slips, TED, and fees? Cite her.
```

**Q6 — two procs**

```text
There are two insert procs with two dates for Type 01. Which one does Rafael say to use, and what is wrong with the other?
```

**Q7 — what is not in these sources**

```text
What is not in these sources? If you need Java, contracts/, Type 06, or modern/ to answer a question, say you do not have it.
```

---

## Proof

- Nine sources ready in **their** notebook, not a shared one.
- Q2 names `01`–`05` and says Type `06` is not here.
- Q5 cites Marina: **173.44** vs **173.45**, keep the lie, same shape on the other types.
- Q7 does **not** invent Java or `contracts/`.
- No file in the git repo was written.

## If fail

| What happened | What you do |
|---|---|
| No Google account | Pair with a neighbour. They still keep `spec/` on disk. Do not stop the night. |
| Upload rejects the `.zip` | Expected. Unzip. Upload the nine `.md` files. |
| Someone uploaded `legacy/` or `contracts/` | Delete those sources. Re-add only the nine packs. |
| Notebook invents a parser / “fixes” 173.44 | Point at Q5 and `00-how-this-notebook-thinks.md`. |
| Daily chat cap | They already have Q5. Continue. Capture still reads `spec/`. |

Do not ask it to write code. Do not walk Type `05` rounding as a parser tonight — the inbound is in the notebook for Day 4, not for a Day 1 parser.
