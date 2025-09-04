#!/usr/bin/env bash
set -euo pipefail
FORCE=${FORCE:-0}
echo "=== Pipeline Environment Cleanup (Unix) ==="
targets=( .venv work models )
targets+=( *.lipsync.json *.wav *.m4a )
for t in "${targets[@]}"; do
  for path in $t; do
    [ -e "$path" ] || continue
    if [ "$FORCE" != "1" ]; then
      read -r -p "Delete $path ? (y/N) " ans
      [[ $ans == [Yy] ]] || continue
    fi
    echo "Removing $path"
    rm -rf "$path"
  done
done
echo "Cleanup complete."
