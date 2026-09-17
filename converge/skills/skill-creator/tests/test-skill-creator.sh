#!/usr/bin/env bash
# test-skill-creator.sh — offline proof of the skill-creator toolchain hardening:
#   * quick_validate.py runs stdlib-only (no PyYAML) and keeps its contract:
#     kebab-case name <=64, description present <=1024, no angle brackets,
#     allowed frontmatter keys only, exit 0/1, "Skill is valid!" on success
#   * the shared frontmatter parser in scripts/utils.py handles the real
#     sibling shapes (literal | and folded >- block scalars, nested metadata
#     maps, inline lists, quoted scalars)
#   * package_skill.py ships a .skill zip without __pycache__ / .DS_Store
#   * improve_description.py fails closed when the model drops the
#     <new_description> tags (SKILL_CREATOR_CLAUDE_CMD injects a fake CLI)
#
# Self-contained: fixtures live in tests/fixtures/, scratch work in a temp dir,
# no network, no writes outside the temp dir. Ends in a single machine token:
#   SKILL_CREATOR_TESTS=PASS | SKILL_CREATOR_TESTS=FAIL
# Exit 0 all-pass, 1 otherwise.
#
# bash-3.2-safe. No -e (assertions must not abort the run); -uo pipefail kept.
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SELF_DIR/.." && pwd)"
FIX="$SELF_DIR/fixtures"
QV="$SKILL_DIR/scripts/quick_validate.py"

PASS=0; FAIL=0
ok()  { echo "  ok   — $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL — $1"; FAIL=$((FAIL+1)); }
# has "desc" HAYSTACK NEEDLE  — assert substring present
has() { if printf '%s' "$2" | grep -qF -- "$3"; then ok "$1"; else bad "$1 (missing: '$3')"; fi; }
# hasnt "desc" HAYSTACK NEEDLE — assert substring absent
hasnt() { if printf '%s' "$2" | grep -qF -- "$3"; then bad "$1 (unexpected: '$3')"; else ok "$1"; fi; }
# rc_is "desc" GOT WANT
rc_is() { if [[ "$2" == "$3" ]]; then ok "$1"; else bad "$1 (rc=$2, wanted $3)"; fi; }
rc_nonzero() { if [[ "$2" -ne 0 ]]; then ok "$1"; else bad "$1 (expected non-zero exit)"; fi; }

WORK="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/skill-creator-test.$$")"
mkdir -p "$WORK"
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT

echo "=================================================================="
echo "test-skill-creator.sh — offline hardening proof"
echo "=================================================================="

# -----------------------------------------------------------------------------
echo; echo "[A] quick_validate: valid skill"
OUT="$(python3 "$QV" "$FIX/valid-skill" 2>&1)"; RC=$?
rc_is "valid skill exits 0" "$RC" "0"
has "valid skill prints success" "$OUT" "Skill is valid!"

# -----------------------------------------------------------------------------
echo; echo "[B] quick_validate: uppercase name rejected"
OUT="$(python3 "$QV" "$FIX/bad-name-uppercase" 2>&1)"; RC=$?
rc_is "uppercase name exits 1" "$RC" "1"
has "uppercase name explains kebab-case" "$OUT" "kebab-case"

# -----------------------------------------------------------------------------
echo; echo "[C] quick_validate: missing description rejected"
OUT="$(python3 "$QV" "$FIX/missing-description" 2>&1)"; RC=$?
rc_is "missing description exits 1" "$RC" "1"
has "missing description named" "$OUT" "Missing 'description'"

# -----------------------------------------------------------------------------
echo; echo "[D] quick_validate: description >1024 rejected (generated fixture)"
LONG_DIR="$WORK/long-description"; mkdir -p "$LONG_DIR"
python3 - "$LONG_DIR/SKILL.md" <<'PY'
import sys
body = "---\nname: long-description\ndescription: " + ("x" * 1025) + "\n---\n\n# body\n"
open(sys.argv[1], "w").write(body)
PY
OUT="$(python3 "$QV" "$LONG_DIR" 2>&1)"; RC=$?
rc_is "description >1024 exits 1" "$RC" "1"
has "description >1024 says too long" "$OUT" "too long"

# -----------------------------------------------------------------------------
echo; echo "[E] quick_validate: angle brackets in description rejected"
OUT="$(python3 "$QV" "$FIX/angle-brackets" 2>&1)"; RC=$?
rc_is "angle brackets exit 1" "$RC" "1"
has "angle brackets named" "$OUT" "angle brackets"

# -----------------------------------------------------------------------------
echo; echo "[F] stdlib parser: nested metadata block (task-spec shape) + real shapes"
OUT="$(python3 "$QV" "$FIX/nested-metadata" 2>&1)"; RC=$?
rc_is "nested metadata skill exits 0" "$RC" "0"
has "nested metadata skill valid" "$OUT" "Skill is valid!"
PARSER_OUT="$(cd "$SKILL_DIR" && python3 - <<'PY'
from pathlib import Path
from scripts.utils import parse_frontmatter, parse_skill_md, split_frontmatter

# Fixture mirroring ../task-spec/SKILL.md: literal block + nested metadata.
content = Path("tests/fixtures/nested-metadata/SKILL.md").read_text()
fm = parse_frontmatter(split_frontmatter(content))
assert fm["name"] == "nested-metadata", fm
assert fm["metadata"] == {"version": "3.6.0"}, fm["metadata"]
assert fm["description"].startswith("Fixture mirroring"), repr(fm["description"])
assert fm["description"].count("\n") >= 2, "literal block must keep newlines"

# parse_skill_md keeps its (name, description, content) contract.
name, desc, _ = parse_skill_md(Path("tests/fixtures/nested-metadata"))
assert name == "nested-metadata" and "Fixture mirroring" in desc

# Shapes from ../tech-req-to-adrs/SKILL.md: folded >-, int + quoted nested
# scalars; plus an inline list (allowed-tools).
fm2 = parse_frontmatter(
    'name: x\n'
    'description: >-\n'
    '  folded line one\n'
    '  line two\n'
    'metadata:\n'
    '  converge_pass: 2\n'
    '  compatibility: "quoted, with comma"\n'
    'allowed-tools: [Bash, Read]\n'
    'license: MIT'
)
assert fm2["description"] == "folded line one line two", repr(fm2["description"])
assert fm2["metadata"]["converge_pass"] == 2, fm2["metadata"]
assert isinstance(fm2["metadata"]["converge_pass"], int)
assert fm2["metadata"]["compatibility"] == "quoted, with comma"
assert fm2["allowed-tools"] == ["Bash", "Read"], fm2["allowed-tools"]
assert fm2["license"] == "MIT"
print("parser-shape-ok")
PY
)"; RC=$?
rc_is "parser shape assertions run clean" "$RC" "0"
has "parser shape assertions reached" "$PARSER_OUT" "parser-shape-ok"

# -----------------------------------------------------------------------------
echo; echo "[G] package_skill: .skill zip excludes __pycache__ and .DS_Store"
PKG_OUT="$WORK/pkg"; mkdir -p "$PKG_OUT"
OUT="$(cd "$SKILL_DIR" && python3 -m scripts.package_skill "$FIX/package-me" "$PKG_OUT" 2>&1)"; RC=$?
rc_is "package_skill exits 0" "$RC" "0"
SKILL_ZIP="$PKG_OUT/package-me.skill"
if [[ -f "$SKILL_ZIP" ]]; then ok ".skill file created"; else bad ".skill file missing at $SKILL_ZIP"; fi
if [[ -f "$SKILL_ZIP" ]]; then
  NAMES="$(python3 -c "import zipfile, sys; print('\n'.join(zipfile.ZipFile(sys.argv[1]).namelist()))" "$SKILL_ZIP")"
  has "zip contains SKILL.md" "$NAMES" "package-me/SKILL.md"
  has "zip contains bundled script" "$NAMES" "package-me/scripts/helper.sh"
  hasnt "zip excludes __pycache__" "$NAMES" "__pycache__"
  hasnt "zip excludes .DS_Store" "$NAMES" ".DS_Store"
fi

# -----------------------------------------------------------------------------
echo; echo "[H] improve_description: tag-less stdout fails closed"
chmod +x "$FIX"/fake-claude-*.sh 2>/dev/null || true
OUT="$(cd "$SKILL_DIR" && SKILL_CREATOR_CLAUDE_CMD="$FIX/fake-claude-no-tags.sh" \
  python3 -m scripts.improve_description \
  --eval-results "$FIX/eval-results.json" \
  --skill-path "$FIX/valid-skill" \
  --model fake-model 2>&1)"; RC=$?
rc_nonzero "tag-less response exits non-zero" "$RC"
has "tag-less response explains refusal" "$OUT" "<new_description> tags"

# -----------------------------------------------------------------------------
echo; echo "[I] improve_description: tagged stdout still works (happy path)"
OUT="$(cd "$SKILL_DIR" && SKILL_CREATOR_CLAUDE_CMD="$FIX/fake-claude-with-tags.sh" \
  python3 -m scripts.improve_description \
  --eval-results "$FIX/eval-results.json" \
  --skill-path "$FIX/valid-skill" \
  --model fake-model 2>/dev/null)"; RC=$?
rc_is "tagged response exits 0" "$RC" "0"
has "tagged response becomes description" "$OUT" "Use this fixture skill to prove the tag path stays green."

# -----------------------------------------------------------------------------
echo; echo "[J] repo-wide: every sibling frontmatter parses with the stdlib parser"
# The parser's own contract: it must read every real frontmatter in the repo
# without a FrontmatterError. Content verdicts (e.g. a sibling's description
# length) are that skill's gate, not this suite's — the manual 12-skill
# quick_validate loop covers those.
PARSE_SWEEP="$(cd "$SKILL_DIR" && python3 - <<'PY'
from pathlib import Path
from scripts.utils import parse_frontmatter, split_frontmatter
count = 0
for d in sorted(Path("..").iterdir()):
    skill_md = d / "SKILL.md"
    if not d.is_dir() or not skill_md.exists():
        continue
    count += 1
    fm = parse_frontmatter(split_frontmatter(skill_md.read_text()))
    assert isinstance(fm, dict) and fm.get("name"), f"{d}: parser returned garbage"
print(f"parse-sweep-ok {count}")
PY
)"; RC=$?
rc_is "all sibling frontmatters parse without FrontmatterError" "$RC" "0"
COUNT="${PARSE_SWEEP##parse-sweep-ok }"
if [[ "$COUNT" =~ ^[0-9]+$ ]] && [[ "$COUNT" -ge 11 ]]; then ok "parse sweep covered $COUNT skills"; else bad "parse sweep saw '$COUNT' skills (expected >= 11)"; fi

# -----------------------------------------------------------------------------
echo; echo "[K] dependency kill: no PyYAML import left anywhere in scripts/"
if grep -q "import yaml" "$SKILL_DIR"/scripts/*.py; then
  bad "PyYAML import still present in scripts/"
else
  ok "no import yaml anywhere in scripts/"
fi
OUT="$(python3 - "$SKILL_DIR" <<'PY'
import ast, glob, sys
for f in sorted(glob.glob(sys.argv[1] + "/scripts/*.py")):
    ast.parse(open(f).read(), filename=f)
print("ast-clean")
PY
)"; RC=$?
rc_is "all scripts/*.py parse as valid python" "$RC" "0"
has "ast sweep reached" "$OUT" "ast-clean"

# -----------------------------------------------------------------------------
echo
echo "=================================================================="
if [[ "$FAIL" -eq 0 ]]; then
  echo "SKILL_CREATOR_TESTS=PASS ($PASS assertions)"
  exit 0
else
  echo "SKILL_CREATOR_TESTS=FAIL ($FAIL failed / $((PASS+FAIL)) assertions)"
  exit 1
fi
