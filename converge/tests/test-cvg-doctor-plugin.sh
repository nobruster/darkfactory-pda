#!/usr/bin/env bash
# test-cvg-doctor-plugin.sh — the drift `cvg doctor plugin` exists to catch.
#
# WHY THIS EXISTS
# On 2026-08-03 a live use case returned four GREEN gates while loading skills
# eight commits stale. `cvg` on PATH was a current dev checkout; the plugin cache
# the project actually loads was pinned a week back. "It is fixed" and "I do not
# see it" were both true and nothing reported the split — it took several rounds
# to find by hand. This suite makes that state fail loudly instead.
#
# The subtle half: the cache path is keyed by VERSION
# (…/cache/<mp>/<plugin>/<version>). When VERSION does not move, an update
# resolves to the SAME directory, so a sha check alone can pass while the content
# is stale. Row [2] pins the content fingerprint for exactly that reason.
#
# Hermetic: a throwaway CLAUDE_CONFIG_DIR with a local git "marketplace". No
# network, no real plugin install touched.
# Token: DOCTOR_PLUGIN_TESTS=PASS | DOCTOR_PLUGIN_TESTS=FAIL
# bash 3.2 safe. Deps: git, python3.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SELF_DIR/.." && pwd)"
CVG="$REPO/bin/cvg"

rows=0; failed=0
ok()  { printf '  ok   — %s\n' "$1"; rows=$((rows+1)); }
bad() { printf '  FAIL — %s\n' "$1"; rows=$((rows+1)); failed=$((failed+1)); }

echo "=================================================================="
echo "test-cvg-doctor-plugin.sh — a project must never load a stale Converge"
echo "=================================================================="

TMP="$(mktemp -d -t cvg-doctor-plugin.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# --- a fake marketplace clone with two commits ------------------------------
MP="$TMP/cfg/plugins/marketplaces/cvg"
mkdir -p "$MP"
git -C "$MP" init --quiet
git -C "$MP" config user.email t@t.t
git -C "$MP" config user.name t
mkdir -p "$MP/skills/demo" "$MP/bin"
printf 'v1\n' > "$MP/skills/demo/SKILL.md"
printf 'old\n' > "$MP/bin/cvg"
git -C "$MP" add -A >/dev/null 2>&1
git -C "$MP" commit -qm "old release" >/dev/null 2>&1
OLD_SHA="$(git -C "$MP" rev-parse HEAD)"
OLD_TREE="$TMP/old-copy"
cp -R "$MP" "$OLD_TREE"; rm -rf "$OLD_TREE/.git"

printf 'v2 — the change the project must see\n' > "$MP/skills/demo/SKILL.md"
git -C "$MP" add -A >/dev/null 2>&1
git -C "$MP" commit -qm "new release" >/dev/null 2>&1
NEW_SHA="$(git -C "$MP" rev-parse HEAD)"

CACHE="$TMP/cfg/plugins/cache/cvg/converge/0.1.0"
REG="$TMP/cfg/plugins/installed_plugins.json"

write_reg() { # write_reg <sha>
  python3 - "$REG" "$CACHE" "$1" <<'PY'
import json, sys
reg, install, sha = sys.argv[1], sys.argv[2], sys.argv[3]
json.dump({"plugins": {"converge@cvg": [{
    "scope": "project", "installPath": install, "version": "0.1.0",
    "gitCommitSha": sha, "projectPath": "/tmp/some-project"}]}},
    open(reg, "w"), indent=2)
PY
}

run() { # run <expected-exit> ; sets OUT
  local want="$1" rc=0
  OUT="$(CLAUDE_CONFIG_DIR="$TMP/cfg" bash "$CVG" doctor plugin 2>&1)" || rc=$?
  RC="$rc"
  [ "$rc" = "$want" ]
}
last() { printf '%s\n' "$OUT" | tail -1; }

# ---------------------------------------------------------------------------
echo
echo "[1] THE REAL BUG: cache pinned at an older commit → STALE"
# ---------------------------------------------------------------------------
mkdir -p "$(dirname "$CACHE")"
cp -R "$OLD_TREE" "$CACHE"
write_reg "$OLD_SHA"
if run 1 && [ "$(last)" = "DOCTOR_PLUGIN=STALE" ]; then
  ok "a project loading an older commit fails (exit 1 + DOCTOR_PLUGIN=STALE)"
else
  bad "stale install must fail closed (got exit $RC / $(last))"
fi
if printf '%s\n' "$OUT" | grep -q 'moved past'; then
  ok "it names WHY: the record points at a commit the source moved past"
else
  bad "the stale report should name the commit mismatch"
fi
if printf '%s\n' "$OUT" | grep -q 'CONTENT differs'; then
  ok "it also proves the loaded CONTENT differs, not just the recorded sha"
else
  bad "content drift should be reported"
fi

# ---------------------------------------------------------------------------
echo
echo "[2] THE SUBTLE BUG: sha says current, content is stale (version-keyed cache)"
# ---------------------------------------------------------------------------
# Exactly what a same-version 'update' produces: the record is rewritten to the
# new sha while the directory keeps the old bytes.
write_reg "$NEW_SHA"
if run 1 && [ "$(last)" = "DOCTOR_PLUGIN=STALE" ]; then
  ok "a matching sha does NOT excuse stale content (exit 1 + STALE)"
else
  bad "content fingerprint must catch a lying sha (got exit $RC / $(last))"
fi
if printf '%s\n' "$OUT" | grep -q 'version-keyed cache path did not change'; then
  ok "it explains the version-keyed cache trap"
else
  bad "the content failure should explain the version-key hazard"
fi

# ---------------------------------------------------------------------------
echo
echo "[3] healthy: content identical to the source clone → OK"
# ---------------------------------------------------------------------------
rm -rf "$CACHE"; mkdir -p "$CACHE"
( cd "$MP" && git archive HEAD | tar -x -C "$CACHE" )
write_reg "$NEW_SHA"
if run 0 && [ "$(last)" = "DOCTOR_PLUGIN=OK" ]; then
  ok "a current install passes (exit 0 + DOCTOR_PLUGIN=OK)"
else
  bad "a current install must pass (got exit $RC / $(last))"
fi
if printf '%s\n' "$OUT" | grep -q 'byte-identical'; then
  ok "it states the positive claim it verified"
else
  bad "the OK path should say what it proved"
fi
# The dev-checkout warning is the trap from 2026-08-03: running a different copy
# than projects load means local green proves nothing about the plugin.
if printf '%s\n' "$OUT" | grep -q 'DIFFERENT copy than projects load'; then
  ok "warns that the copy you run is not the copy projects load"
else
  bad "the dev-checkout warning is missing"
fi

# ---------------------------------------------------------------------------
echo
echo "[4] the install path is gone → STALE, not a crash"
# ---------------------------------------------------------------------------
mv "$CACHE" "$CACHE.moved"
if run 1 && [ "$(last)" = "DOCTOR_PLUGIN=STALE" ]; then
  ok "a missing install path fails closed rather than erroring out"
else
  bad "missing install path should be STALE (got exit $RC / $(last))"
fi
mv "$CACHE.moved" "$CACHE"

# ---------------------------------------------------------------------------
echo
echo "[5] nothing to compare → UNMANAGED, exit 0 (absence is not failure)"
# ---------------------------------------------------------------------------
EMPTY="$TMP/empty-cfg"; mkdir -p "$EMPTY"
rc=0
OUT="$(CLAUDE_CONFIG_DIR="$EMPTY" bash "$CVG" doctor plugin 2>&1)" || rc=$?
if [ "$rc" -eq 0 ] && [ "$(last)" = "DOCTOR_PLUGIN=UNMANAGED" ]; then
  ok "no plugin install → UNMANAGED at exit 0 (a checkout install is legitimate)"
else
  bad "no install should be UNMANAGED/0 (got exit $rc / $(last))"
fi

# ---------------------------------------------------------------------------
echo
echo "[6] contracts: read-only, and every surface ends in the token"
# ---------------------------------------------------------------------------
BEFORE="$(find "$TMP/cfg" -type f | sort | md5 2>/dev/null || find "$TMP/cfg" -type f | sort | md5sum)"
CLAUDE_CONFIG_DIR="$TMP/cfg" bash "$CVG" doctor plugin >/dev/null 2>&1 || true
AFTER="$(find "$TMP/cfg" -type f | sort | md5 2>/dev/null || find "$TMP/cfg" -type f | sort | md5sum)"
if [ "$BEFORE" = "$AFTER" ]; then
  ok "read-only — the check mutated nothing"
else
  bad "the doctor changed the plugin state"
fi

rc=0
OUT="$(CLAUDE_CONFIG_DIR="$TMP/cfg" bash "$CVG" doctor plugin extra-arg 2>&1)" || rc=$?
if [ "$rc" -eq 2 ] && [ "$(last)" = "DOCTOR_PLUGIN=ERROR" ]; then
  ok "an unexpected argument is a usage error ending in the token"
else
  bad "extra args should exit 2 + DOCTOR_PLUGIN=ERROR (got exit $rc / $(last))"
fi

# NOTE: `bash cvg help | grep -q` would be WRONG here. grep -q exits on the first
# match, SIGPIPEs the producer, and `set -o pipefail` then reports the pipeline as
# failed even though the text was found. That false negative is what this row hit
# on its first run. Substring matching with `case` has no pipe and cannot lie.
HELP_OUT="$(bash "$CVG" help 2>&1 || true)"
case "$HELP_OUT" in
  *"doctor plugin"*) ok "cvg help lists the subject — a check nobody can find is a check nobody runs" ;;
  *)                 bad "cvg help does not mention doctor plugin" ;;
esac

if bash "$CVG" agent-context 2>&1 | python3 -c '
import json,sys
m=json.load(sys.stdin)
c=[x for x in m["commands"] if x["name"]=="doctor plugin"]
assert len(c)==1, "expected one doctor plugin entry"
assert "DOCTOR_PLUGIN=OK|STALE|UNMANAGED|ERROR" in c[0]["emits_tokens"]
assert c[0]["mutating"] is False
' 2>/dev/null; then
  ok "agent-context declares it: token set, read-only"
else
  bad "agent-context entry missing or wrong"
fi

echo
echo "=================================================================="
printf 'rows: %s   failed: %s\n' "$rows" "$failed"
if [ "$failed" -eq 0 ]; then echo "DOCTOR_PLUGIN_TESTS=PASS"; exit 0; fi
echo "DOCTOR_PLUGIN_TESTS=FAIL"; exit 1
