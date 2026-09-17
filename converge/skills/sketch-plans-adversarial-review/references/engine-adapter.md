# Engine adapter — how `cvg review` dispatches a headless adversary

The CLI is a **referee, never a player**: it holds no model credentials and never
calls an LLM API. It shells out to the engine's own headless CLI (which
authenticates itself), captures a schema-validated artifact, and gates it. This is
the reusable dispatch layer (Milestone 3.1) — Pass 4 is the first pass that needs
it; Pass 5/8 reuse it.

## Interface — `adapters/engines/<engine>.sh`

One driver per engine behind a stable contract.

- **Inputs:** `$1` framed prompt file (the attack-playbook) · `$2` workdir (a
  read-only checkout / throwaway worktree of `swimlanes/`) · env `CVG_ADVERSARY_MODEL`,
  `CVG_TIMEOUT_SECS`, `CVG_OUT` (artifact path).
- **Behavior:** map to the real invocation (below), **always read-only**, request
  **schema-validated JSON**, **wrap in `timeout`**, write raw → `$CVG_OUT.raw` and
  the parsed objection-log → `$CVG_OUT`.
- **Never trust the engine exit code alone** (Codex `exec` exits 0 even on failure).
  Success = timeout didn't fire **AND** the artifact parses against
  `objection-log.schema.json` **AND** `verdict ∈ {PASS,REVISE}`. Else emit an
  `ERROR` verdict — **fail-closed, never a pass**.
- **Normalized adapter exit codes:** `0` valid artifact · `20` engine
  unavailable → SKIP · `21` timed out · `22` produced-but-malformed → ERROR ·
  `75` retryable (429/5xx) — propagate Kimi's 75, map Codex/Claude transient here.

## Headless invocation cheatsheet (real flags)

Flags below are what the live CLIs on this box actually accept (verified against
`kimi 0.28.1` / `codex exec` / `claude -p`), not what the vendors' blog posts show —
the first real dispatch corrected several guesses.

| Engine | family | headless command (read-only) | exit-code / behavior gotcha |
|---|---|---|---|
| **codex** | openai | `codex exec --sandbox read-only - < prompt` (prompt on stdin) | **exits 0 even on failure** → gate the artifact, not `$?`. Observed **blocking at 0% CPU** headless (model round-trip / approval it can't get) → the wall-clock cap is what saves you. |
| **kimi** | moonshot | `kimi --output-format text -p "$(cat prompt)"` — flag is **`-p/--prompt`, NOT `--print`**; **cannot combine `-p` with `--auto`** (prompt mode is already non-interactive). `text` beats `stream-json` for a single judgment (the JSON object is emitted inline in prose, not nested in event envelopes). | clean codes: `0` ok · `1` permanent · `75` retry. Full multi-file attacks can exceed a 280s cap → scope per-swimlane or raise the cap. |
| **claude** | anthropic | `claude -p "$(cat prompt)" --output-format json --tools Read,Grep --disallowedTools "Edit,Write"` | `stream-json` can **hang** with no TTY → **mandatory cap** |

`claude` is the **fallback only** (same family as the author → weak independence);
default to a cross-family engine (`codex` or `kimi`).

**The cap is mandatory and dependency-free.** `timeout(1)`/`gtimeout` are GNU
coreutils and macOS ships neither, so the adapter uses them when present and
otherwise a **pure-bash watchdog** (background the engine; a sibling sleeper
`TERM`/`KILL`s it past the cap, leaving a marker → normalize to exit `124` →
`REVIEW=TIMEOUT`). Proven live: kimi outran a 280s cap → clean `TIMEOUT`, no
objection-log written — the referee never fabricates a consensus.

**Parse tolerantly.** A real engine wraps the judgment JSON in reasoning prose (and
kimi prepends `• …` bullets + a `To resume this session:` trailer). Scan every `{`
with a `raw_decode` pass and take the richest judgment object — never a greedy
`{.*}` match (it swallows the whole span and fails to parse).

## Provenance stamp (every run — makes the gate un-spoofable)

The adapter stamps the objection-log with: `adversary.{engine_id,model,family,
engine_version,sandbox_mode}`, `prompt_sha256`, `inputs[]` (each plan path +
`sha256` of the bytes it read), `started_at`/`ended_at`, `raw_exit_code`,
`adapter_exit_code`, `timed_out`. The gate re-hashes the live plans and requires a
match — so a plan edited after review, or an adversary that never saw the real
plans, fails.

## `cvg doctor`

Before Pass 4 can dispatch: a per-engine PASS/SKIP table — binary on PATH,
`auth/login status` OK, `--version` captured, a hello-world card round-trips
read-only. Gate requires **≥ 2 engines PASS**, at least one **cross-family**.

## Security

The adversary receives **only** the sealed plan artifacts + the versioned rubric +
the cited grounding pack (spec/ADRs) — **never** the author's authoring transcript
(fresh context defeats sycophancy) — and runs in a **read-only** sandbox / no-write
worktree so it cannot mutate the checkout.
