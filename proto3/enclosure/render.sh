#!/usr/bin/env bash
# Regenerates the STLs, the PNG views and the dimension drawing of the
# proto 3 enclosure from mcard.scad.
set -euo pipefail
cd "$(dirname "$0")"
OS=${OPENSCAD:-/opt/homebrew/bin/openscad}
VIEW=(--colorscheme=Tomorrow)

for p in tray cover icon_plate logo; do
  "$OS" -q -o "stl/$p.stl" -D "part=\"$p\"" mcard.scad
done

"$OS" -q -o view_front.png --imgsize=1400,1000 --camera=95,48,40,58,0,340,480 "${VIEW[@]}" -D 'part="assembly"' mcard.scad
"$OS" -q -o view_back.png --imgsize=1400,1000 --camera=95,48,40,62,0,160,480 "${VIEW[@]}" -D 'part="assembly"' mcard.scad
"$OS" -q -o view_exploded.png --imgsize=1400,1100 --camera=95,48,70,62,0,20,560 "${VIEW[@]}" -D 'part="exploded"' mcard.scad
"$OS" -q -o view_cover_under.png --imgsize=1400,1000 --camera=95,48,30,130,0,200,460 "${VIEW[@]}" -D 'view="under"' tools/views.scad

tmp=$(mktemp -d)
for w in s_tray s_cover s_card s_reader t_cover t_outline; do
  "$OS" -q -o "$tmp/$w.svg" -D "what=\"$w\"" tools/cut2d.scad
done
python3 tools/compose_drawing.py "$tmp" drawing.svg
rm -rf "$tmp"
