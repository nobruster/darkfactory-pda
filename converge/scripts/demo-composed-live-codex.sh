#!/usr/bin/env bash
# Authenticated live release-candidate proof. Curated evidence is written once.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="$ROOT/evidence/releases/v0.2.0/live-codex"

COMPOSE_DEMO_AGENT=codex \
COMPOSE_DEMO_EVIDENCE_DIR="$EVIDENCE" \
COMPOSE_DEMO_REQUIRE_ENGINE_PROVENANCE=1 \
PRESERVE_COMPOSE_DEMO=0 \
  bash "$ROOT/scripts/demo-composed.sh"

printf 'LIVE_CODEX_EVIDENCE=%s\n' "$EVIDENCE"
