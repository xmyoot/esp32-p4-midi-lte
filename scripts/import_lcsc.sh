#!/usr/bin/env bash
# Import LCSC parts (symbol + footprint + 3D) into lib/lcsc.*
# usage: scripts/import_lcsc.sh C123456 C234567 ...
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
"$PY" -m easyeda2kicad --full --project-relative --lcsc_id "$@" --output "$(pwd -W)/lib/lcsc" --overwrite --use-cache
