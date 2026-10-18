# M-Card presentation page

Live: **https://enicolas72.github.io/m-card/marketing/** (GitHub Pages, updated on every push to `main`).

[`index.html`](index.html) is **self-contained**: a single file (~3.5 MB) that
opens directly in a browser, with no server and no Internet connection.
Everything is inlined: three.js, fonts, cards, photos, 3D parts and web
console captures.

## Contents

- **Real-time 3D rendering** of the device: the actual enclosure parts
  (`enclosure/mcard.scad`, exported in assembled position) plus render-only
  parts (LCD module, buttons, screws, USB-C socket), with the LCD emulated
  and an M-Card sliding into the slot.
- **20×4 LCD emulation**: HD44780 font, same layout and scrolling as
  `software/mcard/display.py`.
- **Web console**: real HTML captures of the interface (`--fake` mode), shown
  frozen in a three-view carousel.
- Cards cut from `card-covers/` and prototype photos from `versions/proto2/`
  (both git-ignored, local only); the lightweight copies used here are in
  `build/cards/` and `build/img/`.

## Rebuilding

```bash
cd marketing/build
npm install
./export-stl.sh      # only if the enclosure changed (requires OpenSCAD)
npm run build        # → ../index.html
```

| Folder / file | Role |
|---|---|
| `src/` | HTML template, CSS, JS (3D scene, LCD emulator, card strip, page logic) |
| `parts.scad` + `export-stl.sh` | assembled parts → `stl/` (binary STLs) |
| `cards/`, `img/` | cut-out cards, lightweight photos, logo extracted from the cards |
| `capture/` | web console pages captured in `--fake` mode |
| `build.mjs` | esbuild bundle + inlining of every asset |

The card strip is drawn on a `<canvas>` on purpose: a CSS-animated strip lost
tiles (then froze) in Safari next to the WebGL context.
