#!/usr/bin/env bash
# Create the two environments the plant needs. Safe to re-run.
#   modern/scripts/bootstrap.sh
# It does not produce evidence/, modern/landing/ or the lakehouse — those are
# artifacts of actually running the nights, and they are gitignored on purpose.
set -euo pipefail
cd "$(dirname "$0")/../.."

make_env() {
  local dir=$1 req=$2 name=$3
  if [ ! -x "$dir/bin/python" ]; then
    echo "▸ creating $name"
    python3 -m venv "$dir"
  else
    echo "▸ $name exists"
  fi
  "$dir/bin/pip" install --quiet --upgrade pip
  "$dir/bin/pip" install --quiet -r "$req"
  echo "  ✓ $name ready"
}

make_env modern/.venv modern/requirements.txt "plant env (modern/.venv)"
make_env modern/orchestration/.venv modern/orchestration/requirements.txt "orchestration env (Dagster)"

echo
echo "▸ versions that matter"
printf '  pyarrow  %s   (must be 25.x — it encodes the landing Parquet)\n' \
  "$(modern/.venv/bin/python -c 'import pyarrow;print(pyarrow.__version__)')"
printf '  dagster  %s\n' \
  "$(modern/orchestration/.venv/bin/python -c 'import dagster;print(dagster.__version__)')"

echo
echo "▸ runtime state this script does NOT create"
for p in evidence modern/landing modern/lakehouse/ducklake; do
  [ -e "$p" ] && echo "  ✓ $p" || echo "  ✗ $p  — produced by running the nights, not by bootstrap"
done
echo
echo "Next: modern/scripts/night_e2e.sh"
