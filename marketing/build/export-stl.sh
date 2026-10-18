#!/bin/bash
# Exporte les pièces assemblées (STL binaire) pour la page marketing.
set -euo pipefail
cd "$(dirname "$0")"
OPENSCAD=${OPENSCAD:-/opt/homebrew/bin/openscad}
mkdir -p stl
for p in shell faceplate icon_plate backrest backrest_cover lid lcd_bezel lcd_screen buttons screws usbc_body usbc_metal usbc_slot; do
    "$OPENSCAD" -q --export-format binstl -o "stl/$p.stl" -D "piece=\"$p\"" parts.scad &
done
wait
