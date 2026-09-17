#!/usr/bin/env bash
# _parse.sh — shared frontmatter parser for the task-specs-to-issues skill.
#
# Bash-3.2-safe (macOS system /bin/bash 3.2.57): NO mapfile, NO `declare -A`,
# NO process-substitution-into-arrays. Only grep/sed/awk over the file, exactly
# like the task-spec skill's list-ready.sh / transition-status.sh. The whole
# point of this file is that register.sh and verify-registration.sh read a spec
# the SAME way, so the board can never disagree with the parser.
#
# Source this from a top-level script:
#   _PARSE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_parse.sh"
#   source "$_PARSE"
#
# Field accessors (each takes a spec file path, echoes ONE line, never fails
# the caller — an absent field echoes empty):
#   tsi_field       FILE NAME   — first `NAME:` value inside the frontmatter block
#   tsi_id          FILE        — spec id (the idempotency key)
#   tsi_title       FILE        — spec title (may contain spaces / unicode)
#   tsi_status      FILE        — status (ready|in-progress|blocked|done|parked)
#   tsi_signed_off  FILE        — signed_off value, normalized to true|false
#   tsi_severity    FILE        — severity label
#   tsi_priority    FILE        — priority label
#   tsi_effort      FILE        — effort label
#   tsi_depends_on  FILE        — SPACE-separated dependency ids (inline YAML list
#                                 `[a, b]` flattened; empty list -> empty string)
#   tsi_goal        FILE        — first paragraph under the `## Goal` heading
#   tsi_exit_check  FILE        — body of the ```bash block under `## Exit Check`
#
# Only the frontmatter (region between the first two `---` lines) is consulted
# for fields; a body line that happens to start with `name:` is never matched.
#
# YAML scalars may be quoted (`title: "Capture steel thread …"`). Quotes are
# DELIMITERS, not content, so tsi_field strips a matched surrounding pair — else
# they ship straight onto the tracker and the board shows a title wrapped in
# literal quote marks (exactly what the first live Linear registration produced).

# ----- Error helper (mirrors task-spec's ts_die) -----
tsi_die() {
  echo "ERROR: $*" >&2
  exit 1
}

# ----- Configurable backlog dir (parity with task-spec's TASKSPEC_BACKLOG_DIR) -----
: "${TSI_TASKS_DIR:=tasks}"
export TSI_TASKS_DIR

# ----- Emit ONLY the frontmatter block (between the first two `---` lines) -----
# Line 1 must be `---`; the block ends at the next `---`. Nothing else is echoed.
tsi_frontmatter() {
  awk '
    BEGIN { c = 0 }
    /^---[[:space:]]*$/ { c++; if (c == 2) exit; next }
    c == 1 { print }
  ' "$1"
}

# ----- Generic field accessor -----
# Echoes the first `NAME:` value found in the frontmatter, trimmed of the
# leading key, surrounding whitespace, and a trailing CR (CRLF-safe). NAME is
# script-controlled (never user input), so a fixed-string grep anchor is safe.
tsi_field() {
  local file="$1" name="$2" raw
  # The trailing `|| true` is load-bearing: an ABSENT field is not an error (see
  # the contract above), but `grep -m1` exits 1 when it matches nothing, and under
  # the callers' `set -e -o pipefail` a bare `x="$(tsi_field …)"` assignment would
  # propagate that and kill the run. Optional fields are the common case.
  raw="$(tsi_frontmatter "$file" \
    | grep -m1 "^${name}:" \
    | sed -E "s/^${name}:[[:space:]]*//" \
    | tr -d '\r' || true)"
  [ -n "$raw" ] || { printf ''; return 0; }
  # A YAML scalar may carry an INLINE COMMENT, and quotes are DELIMITERS. Both
  # must be removed or they ship as content: `register: false  # fixture` parsed
  # as the literal "false  # fixture", which is not "false" — so an opted-out
  # fixture registered anyway. Quoted values take everything between the quotes
  # (a `#` inside them is content); bare values end at the first " #".
  # NB: the space before # is required, so `github:#42` survives intact.
  case "$raw" in
    '"'*) printf '%s' "$raw" | sed -E 's/^"([^"]*)".*$/\1/' ;;
    "'"*) printf '%s' "$raw" | sed -E "s/^'([^']*)'.*\$/\1/" ;;
    *)    printf '%s' "$raw" | sed -E -e 's/[[:space:]]+#.*$//' -e 's/[[:space:]]*$//' ;;
  esac
}

tsi_id()       { tsi_field "$1" id; }
tsi_title()    { tsi_field "$1" title; }
tsi_status()   { tsi_field "$1" status; }
tsi_severity() { tsi_field "$1" severity; }
tsi_priority() { tsi_field "$1" priority; }
tsi_effort()   { tsi_field "$1" effort; }

# ----- signed_off, normalized -----
# The gate is strict: register ONLY on the literal `true`. Anything else
# (false, (none), empty, a typo) normalizes to `false` so an un-gated spec can
# never leak onto the board through a loose truthiness test.
tsi_signed_off() {
  local v
  v="$(tsi_field "$1" signed_off | tr '[:upper:]' '[:lower:]')"
  if [[ "$v" == "true" ]]; then
    echo "true"
  else
    echo "false"
  fi
}

# ----- depends_on inline-list flattener -----
# Frontmatter carries `depends_on: [T-a, T-b]` (or `[]`). Flatten to a
# space-separated id list: strip the brackets, split on commas, trim each id.
# An empty list echoes nothing. bash-3.2-safe: pure sed/tr, no arrays.
tsi_depends_on() {
  local raw
  raw="$(tsi_field "$1" depends_on)"
  # Drop the surrounding [ ] (if present), turn commas into spaces, squeeze WS.
  echo "$raw" \
    | sed -E 's/^\[//; s/\]$//' \
    | tr ',' ' ' \
    | tr -s '[:space:]' ' ' \
    | sed -E 's/^ //; s/ $//'
}

# ----- Goal paragraph (issue body helper) -----
# The first non-empty paragraph after the `## Goal` heading — the human-readable
# summary the board shows. Stops at the next blank line or the next heading.
tsi_goal() {
  awk '
    BEGIN { seen = 0; started = 0 }
    /^##[[:space:]]+Goal[[:space:]]*$/ { seen = 1; next }
    seen == 1 {
      if ($0 ~ /^#/) { exit }
      if ($0 ~ /^[[:space:]]*$/) { if (started) exit; else next }
      started = 1
      print
    }
  ' "$1"
}

# ----- Exit Check block (the eval that travels onto the board) -----
# Extract the contents of the ```bash fenced block under `## Exit Check` — the
# runnable close condition the SKILL.md says must be copied VERBATIM into the
# issue body. Returns the code inside the fence (no fence lines).
tsi_exit_check() {
  awk '
    BEGIN { inx = 0; infence = 0 }
    /^##[[:space:]]+Exit Check[[:space:]]*$/ { inx = 1; next }
    inx == 1 && /^```/ {
      if (infence == 0) { infence = 1; next } else { exit }
    }
    inx == 1 && infence == 1 { print }
  ' "$1"
}

# ----- Enumerate spec files in a tasks dir (bash-3.2-safe, no globstar) -----
# Echoes one file path per line for every top-level `T-*.md`. Used by callers
# with a `while read` loop instead of an array so bash 3.2 is happy.
tsi_list_specs() {
  local dir="$1" f
  for f in "$dir"/T-*.md; do
    [[ -f "$f" ]] || continue
    echo "$f"
  done
}

# ----- Registration opt-out --------------------------------------------------
# tsi_registerable FILE -> true|false
#
# `signed_off: true` answers "is this SAFE to delegate", which is NOT the same
# question as "does this belong on a shared board". Test fixtures are legitimately
# signed off — the e2e harness needs them gated — but they must never reach a live
# tracker: one of them is a deliberate budget-buster designed to exhaust an agent
# and park. A spec opts out with `register: false` in its frontmatter.
# Default (absent field) is TRUE, so every existing spec keeps registering.
tsi_registerable() {
  local v
  v="$(tsi_field "$1" register | tr '[:upper:]' '[:lower:]')"
  if [[ "$v" == "false" || "$v" == "no" ]]; then
    echo "false"
  else
    echo "true"
  fi
}

# ----- Projection accessors (native-field + structure enrichment) ------------
# The projection is an OPTIONAL, tracker-agnostic enrichment layer. Its per-spec
# inputs live in an INDENTED `projection:` block inside the frontmatter:
#
#   projection:
#     project: "Auth Revamp"
#     milestone: Transform
#     cycle: "Cycle 7"
#     parent: T-proj-root
#     use_default_template: true
#     sla: standard
#
# Why indented, and why frontmatter-only: the Tier-1 sign-off HMAC seals
# `id + body_digest + signed_off*`, where body_digest is the sha256 of everything
# AFTER the closing `---` (task-spec _lib.sh ts_signoff_payload). A projection
# block therefore stays OUTSIDE the digest (it is frontmatter), and its keys are
# INDENTED so none of them can shadow the column-0 envelope anchors the seal reads
# (`^id:` / `^signed_off:` / `^signed_off_by:` / `^signed_off_at:`, all `grep -m1`).
# The block is parsed the SAME way the board reads it, so the two never disagree.

# tsi_projection FILE KEY — dequoted value of the INDENTED `KEY:` under the
# `projection:` block; empty if the block or the key is absent, never failing the
# caller. The dequote/decomment mirrors tsi_field exactly (quotes are DELIMITERS;
# a bare value ends at the first " #"), because a projected name ships straight
# onto the board and must not arrive wrapped in quote marks or trailing a comment.
tsi_projection() {
  local file="$1" key="$2" raw
  # awk stays strictly INSIDE the block: it arms on a column-0 `projection:` line,
  # reads only indented children, and disarms on the next column-0 line — so a body
  # key or a sibling top-level field can never be mistaken for a projection value.
  # KEY is script-controlled (never user input), so interpolating it into the awk
  # regex is safe, exactly as tsi_field interpolates NAME into its grep anchor.
  raw="$(tsi_frontmatter "$file" | awk -v k="$key" '
    /^projection:[[:space:]]*$/ { inb=1; next }
    inb && /^[^[:space:]]/      { exit }
    inb && $0 ~ ("^[[:space:]]+" k ":") {
      line = $0
      sub("^[[:space:]]+" k ":[[:space:]]*", "", line)
      print line
      exit
    }
  ' | tr -d '\r' || true)"
  [ -n "$raw" ] || { printf ''; return 0; }
  case "$raw" in
    '"'*) printf '%s' "$raw" | sed -E 's/^"([^"]*)".*$/\1/' ;;
    "'"*) printf '%s' "$raw" | sed -E "s/^'([^']*)'.*\$/\1/" ;;
    *)    printf '%s' "$raw" | sed -E -e 's/[[:space:]]+#.*$//' -e 's/[[:space:]]*$//' ;;
  esac
}

# tsi_projection_keys FILE — the indented child keys under `projection:`, one per
# line (comment and blank lines skipped). Feeds the register --dry-run plan and
# verify-registration's projection surface; echoes nothing when there is no block.
tsi_projection_keys() {
  tsi_frontmatter "$1" | awk '
    /^projection:[[:space:]]*$/ { inb=1; next }
    inb && /^[^[:space:]]/      { exit }
    inb && /^[[:space:]]+[^[:space:]#][^:]*:/ {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      sub(/:.*$/, "", line)
      sub(/[[:space:]]+$/, "", line)
      print line
    }
  '
}

# tsi_signed_off_by FILE — the human(s) who signed the spec off. A thin, named
# wrapper over tsi_field so the subscriber projection and the register report read
# the value through ONE code path (quote/comment handling inherited unchanged).
tsi_signed_off_by() { tsi_field "$1" signed_off_by; }

# ----- Section + behavior accessors (for the rich issue body) -----------------
# tsi_section FILE HEADING — the lines under `## HEADING` up to the next `## `.
tsi_section() {
  awk -v h="$2" '
    $0 ~ "^##[[:space:]]+" h { f=1; next }
    f && /^## / { exit }
    f { print }
  ' "$1"
}

# tsi_behaviors FILE — one `- **B-N** — text` per line, wrapped lines re-joined.
# Specs wrap long Given/When/Then prose across lines; a naive grep would truncate
# each scenario mid-sentence on the board.
tsi_behaviors() {
  awk '
    /^##[[:space:]]+Behavior/ { inb=1; next }
    inb && /^## / { if (buf != "") print buf; buf=""; exit }
    inb {
      if ($0 ~ /^[[:space:]]*-[[:space:]]*\*\*B-[0-9]+\*\*/) {
        if (buf != "") print buf
        buf = $0; next
      }
      if ($0 ~ /^[[:space:]]*$/) { if (buf != "") { print buf; buf="" } next }
      if (buf != "") { line=$0; sub(/^[[:space:]]+/, "", line); buf = buf " " line }
    }
    END { if (buf != "") print buf }
  ' "$1"
}

# tsi_paths FILE — the write surface: touches_paths ∪ creates_paths, de-duped,
# with the `(none)` sentinel and empty inline lists dropped.
tsi_paths() {
  printf '%s\n%s\n' "$(tsi_field "$1" touches_paths)" "$(tsi_field "$1" creates_paths)" \
    | sed -E 's/^\[//; s/\]$//' \
    | tr ',' '\n' \
    | sed -E 's/^[[:space:]]*//; s/[[:space:]]*$//' \
    | grep -v '^$' | grep -vxF '(none)' | sort -u || true
}

# tsi_goal_block FILE — the Goal, reflowed into a readable quoted summary.
#
# Spec authors hard-wrap prose at ~80 columns and mark parts with a bold lead
# (`**(a) …**`, `**(b) …**`) on a new line but WITHOUT a blank line between them.
# Markdown fuses that into a single paragraph, and an earlier version of this
# renderer then collapsed every newline to a space on top of it — so a carefully
# structured goal arrived on the board as one unreadable wall of text.
#
# So: UNWRAP soft-wrapped lines back into logical paragraphs, and start a new
# paragraph at a blank line OR at a line that opens a block (bold lead, list
# marker, numbered item). Paragraphs are emitted inside one blockquote separated
# by `>`, which Linear renders as distinct paragraphs in a single summary block.
tsi_goal_block() {
  tsi_section "$1" "Goal" | awk '
    function flush() {
      if (buf != "") {
        if (n > 0) print ">"
        print "> " buf
        n++; buf = ""
      }
    }
    BEGIN { buf = ""; n = 0 }
    /^[[:space:]]*---[[:space:]]*$/ { flush(); exit }   # a rule ends the section
    /^[[:space:]]*$/               { flush(); next }    # blank line = paragraph break
    {
      line = $0
      sub(/^[[:space:]]+/, "", line); sub(/[[:space:]]+$/, "", line)
      if (buf != "" && line ~ /^(\*\*|[-*+][[:space:]]|[0-9]+\.[[:space:]])/) flush()
      buf = (buf == "" ? line : buf " " line)
    }
    END { flush() }
  '
}

# ----- The issue body renderer (tracker-agnostic Markdown) --------------------
# tsi_issue_body FILE ["dep-id dep-id ..."]
#
# Renders the spec as a well-shaped issue description. Markdown only, so every
# backend benefits; Linear converts pasted Markdown to rich text and renders a
# ```mermaid block as a real diagram (linear.app/docs/editor), which is why the
# dependency graph is emitted that way.
#
# Design rules learned from the first live registration:
#   - NEVER repeat the title as an H1 — the tracker already shows it.
#   - Omit empty sections entirely rather than printing `touches_paths: []`.
#   - Lead with the goal and the done-condition; those are what a picker-upper needs.
tsi_issue_body() {
  local f="$1" deps="${2:-}"
  # The dep list is split by an unquoted `for d in $deps`, so pin IFS to the
  # default rather than trust whatever a caller left in the environment.
  # (NB: this file is bash — sourcing it into zsh will NOT word-split, since zsh
  # needs SH_WORD_SPLIT. Preview it with `bash -c`, or every dep collapses into
  # one mermaid node and you'll chase a bug that isn't there.)
  local IFS=$' \t\n'
  local id eff prof backend sev prio paths beh dnt exitck n
  id="$(tsi_id "$f")"
  eff="$(tsi_field "$f" effort)"
  prof="$(tsi_field "$f" profile)"
  backend="$(tsi_field "$f" execution_backend)"
  sev="$(tsi_severity "$f")"
  prio="$(tsi_priority "$f")"

  # --- Summary (quoted lead, paragraph structure preserved) ---
  local goalblock
  goalblock="$(tsi_goal_block "$f")"
  if [ -n "$goalblock" ]; then
    printf '%s\n\n' "$goalblock"
  fi

  # --- At-a-glance table ---
  printf '| | |\n|---|---|\n'
  printf '| **Spec** | `%s` |\n' "$id"
  [ -n "$eff" ]     && printf '| **Size** | `%s` |\n' "$eff"
  [ -n "$prof" ]    && printf '| **Profile** | `%s` |\n' "$prof"
  [ -n "$backend" ] && printf '| **Executor** | `%s` |\n' "$backend"
  [ -n "$sev" ] && [ "$sev" != "(none)" ]   && printf '| **Severity** | `%s` |\n' "$sev"
  [ -n "$prio" ] && [ "$prio" != "(none)" ] && printf '| **Priority** | `%s` |\n' "$prio"
  printf '\n'

  # --- Definition of done (the contract) ---
  exitck="$(tsi_exit_check "$f")"
  if [ -n "$exitck" ]; then
    printf '### Definition of done\n\n'
    printf 'Only a **GREEN eval** moves this issue to Done — nothing else.\n\n'
    printf '```bash\n%s\n```\n\n' "$exitck"
  fi

  # --- Behaviors as a checklist ---
  beh="$(tsi_behaviors "$f")"
  if [ -n "$beh" ]; then
    printf '### Behavior — what gets verified\n\n'
    printf '%s\n' "$beh" | sed -E 's/^[[:space:]]*-[[:space:]]*/- [ ] /'
    printf '\n'
  fi

  # --- Write surface ---
  paths="$(tsi_paths "$f")"
  printf '### Write surface\n\n'
  if [ -n "$paths" ]; then
    printf '%s\n' "$paths" | sed -E 's/^/- `/; s/$/`/'
  else
    printf '_None declared — verification-only, or the surface lives in the spec._\n'
  fi
  printf '\n'

  # --- Dependencies (Linear renders mermaid) ---
  printf '### Dependencies\n\n'
  if [ -n "$deps" ]; then
    printf '```mermaid\ngraph LR\n'
    n=0
    for d in $deps; do
      n=$((n + 1))
      printf '  d%s["%s"] --> me["%s"]\n' "$n" "$d" "$id"
    done
    printf '  style me fill:#5e6ad2,stroke:#5e6ad2,color:#fff\n'
    printf '```\n\n'
    printf 'Blocked by: '
    for d in $deps; do printf '`%s` ' "$d"; done
    printf '\n\n'
  else
    printf '**None** — this is a root. It is takeable as soon as it is picked up.\n\n'
  fi

  # --- Guardrails ---
  dnt="$(tsi_section "$f" "Do-Not-Touch" | grep -v '^[[:space:]]*$' || true)"
  if [ -n "$dnt" ]; then
    printf '### Guardrails — do not touch\n\n'
    printf '%s\n\n' "$dnt"
  fi

  # --- Provenance footer ---
  # TSI_SPEC_BASE_URL (e.g. https://github.com/<org>/<repo>/blob/main) turns the
  # spec path into a REAL clickable link. The idempotency marker attachment is a
  # synthetic key by design and deliberately does NOT navigate anywhere — this is
  # the link a human actually wants.
  printf -- '---\n\n'
  if [ -n "${TSI_SPEC_BASE_URL:-}" ]; then
    printf 'Projected from [`%s`](%s/%s) by `cvg register` (REGISTER ①).\n' "$f" "${TSI_SPEC_BASE_URL%/}" "$f"
  else
    printf 'Projected from `%s` by `cvg register` (REGISTER ①).\n' "$f"
  fi
  printf '**The spec is the source of truth** — edits here are overwritten on the next\n'
  printf 'register; only a green eval closes this issue.\n'
}

# ----- Write-back: stamp the tracker_ref RECEIPT into a spec's frontmatter -----
# tsi_set_tracker_ref FILE VALUE
#
# Idempotently set `tracker_ref: VALUE` inside FILE's frontmatter (the region
# between the first two `---` lines) and NOWHERE else. This is the ONLY write
# this skill ever makes to a spec: a convenience BACKLINK (a receipt) to the
# tracker issue, stamped after a successful upsert.
#
# It is NOT the idempotency key — the marker carried ON the issue is (see
# references/idempotency-keys.md). It never touches the spec BODY, so a
# signed-off spec stays sealed: the sign-off HMAC covers `id + body_digest +
# the signed_off* values` (task-spec _lib.sh ts_signoff_payload), and
# body_digest is the sha256 of everything AFTER the closing `---`. A frontmatter
# receipt is outside that boundary by design, so the MAC still verifies.
#
# Resolution order (first match wins):
#   1) an existing `tracker_ref:` line in the frontmatter -> replace its value
#   2) else a deprecated `linear_ref:` line present        -> insert after it
#   3) else                                                -> append before `---`
#
# bash-3.2-safe: awk over a temp file, atomic mv. Returns 1 on a missing file, an
# empty/multi-line value, or a frontmatter with no closing '---' (never clobbers).
tsi_set_tracker_ref() {
  local file="$1" value="$2"
  [[ -f "$file" ]]  || { echo "tsi_set_tracker_ref: '$file' not found" >&2; return 1; }
  [[ -n "$value" ]] || { echo "tsi_set_tracker_ref: empty value" >&2; return 1; }
  case "$value" in
    *[$'\n\r']*) echo "tsi_set_tracker_ref: value must be single-line (got newline/CR)" >&2; return 1 ;;
  esac

  local has_tr=0 has_lr=0
  if tsi_frontmatter "$file" | grep -q '^tracker_ref:'; then has_tr=1; fi
  if tsi_frontmatter "$file" | grep -q '^linear_ref:';  then has_lr=1; fi

  local tmp="${file}.tmp.$$"
  awk -v val="$value" -v has_tr="$has_tr" -v has_lr="$has_lr" '
    BEGIN { fm=0; done=0 }
    /^---[[:space:]]*$/ {
      fm++
      if (fm==2 && !done) { print "tracker_ref: " val; done=1 }
      print; next
    }
    (fm==1 && !done && has_tr+0>0 && /^tracker_ref:/)                { print "tracker_ref: " val; done=1; next }
    (fm==1 && !done && has_tr+0==0 && has_lr+0>0 && /^linear_ref:/)  { print; print "tracker_ref: " val; done=1; next }
    { print }
  ' "$file" > "$tmp" || { rm -f "$tmp"; return 1; }

  # Conservative guard: the write only "took" if tmp now carries a tracker_ref
  # line (replace or insert). If the frontmatter had no closing '---', the awk
  # appended nothing — refuse rather than move a no-op/garbled file.
  if ! grep -q '^tracker_ref:' "$tmp"; then
    rm -f "$tmp"
    echo "tsi_set_tracker_ref: no frontmatter closing '---' in $file; not written" >&2
    return 1
  fi
  mv "$tmp" "$file"
}
