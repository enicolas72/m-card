# M-Card enclosure — 3D printing (V0.3)

Parametric model: [`mcard.scad`](mcard.scad) (all dimensions at the top of the
file). Pre-generated STLs in [`stl/`](stl/).

Overview (bottom shown exploded):
[front](assembly_front.png) · [back](assembly_back.png) · [faceplate](facade_icons.png)

V0.3 takes a "magnetic stirrer" silhouette: a low 48 mm base (210 × 150
footprint) with a **front console sloped at ~34°** carrying the LCD + buttons
faceplate. The screen reads from above, and the Raspberry Pi lies flat behind
the slot. It keeps what V0.2 got right: separate faceplate (LCD screwed on
flat on the bench), threaded-insert pockets at every screw point, a slot that
runs the full length (vinyl compatible), and widened passages for the reader's
USB-A plug.

## Parts

| Part | Print orientation | Role |
|---|---|---|
| `shell` | **upside down** (top on the bed) | base: open sloped console, through slot, USB-C at the rear |
| `faceplate` | front face on the bed | sloped faceplate: LCD window + posts, 3 buttons in a column, **cut-out** icons |
| `backrest` | lying on its front face | full-width trapezoidal backrest (rounded top corners, h 84, top 126), hollow: holds the ACR122U board **in landscape** (93×62, antenna left, cable right), positioning stops |
| `backrest_cover` | flat | **flush** back plate, same trapezoid as the backrest |
| `lid` | flat | screwed bottom, Raspberry Pi posts, vents |
| `icon_plate` | flat, **contrasting color** | plate glued into the recess behind the faceplate: its color shows through the cut-out icons |

The STLs are already exported in the right orientation.

## Printing

- **Material**: PLA (or PETG). 0.4 nozzle, 0.2 mm layers, **3 perimeters**,
  15 % infill, **no supports**.
- Required bed: 210 × 150 mm for the base.
- The faceplate icons are **cut through**: print `icon_plate` in a contrasting
  color and glue it into the recess at the back (cyanoacrylate or thin
  double-sided tape). The color shows at the bottom of the cut-outs, slightly
  recessed (depth effect).

## Threaded inserts

Each M3 screw point has a **Ø4.4 × 7 mm locating pocket with an entry cone**:
the insert sits in it, centers itself, then gets pressed in with the iron.
Sized for **Hangtife M3×5×4** inserts (OD 5.0, length 4, recommended hole
4.31–4.35; the printed Ø4.4 comes out at ~4.3). For other inserts, adjust
`insert_d` / `insert_depth`.

| Location | Count | Pressed from |
|---|---|---|
| Base, front frame (faceplate) | 4 | the front, before mounting the faceplate |
| Base, floor bosses | 4 | below (enclosure open) |
| Backrest, bottom face | 2 | below, before mounting |
| Backrest, rear face (plate) | 4 | the rear |

**Total: 14 M3 inserts.**

## Screws (M3 socket head cap screw kit, Ø5.5×3 heads sunk in counterbores)

- 4 × M3×8: faceplate → console inserts (counterbores on the front face)
- 4 × M3×8: bottom → boss inserts (counterbores under the bottom)
- 2 × M3×8: top face → backrest inserts (from inside, enclosure open)
- 4 × M3×8: back plate → backrest inserts (counterbores)
- 4 × M3×8: LCD → Ø2.8 pilot holes in the posts (the M3 screw taps into the PLA)
- 4 × M2.5×6: Raspberry Pi → floor posts (not part of the M3 kit)
- 12 mm buttons: nut supplied; USB-C socket: 2 × M2

The counterbored plates (faceplate, bottom, back plate) are 4 mm thick, so the
socket head sits flush. A single screw length (M3×8) covers the whole
enclosure.

## Dimensions checked / to check

1. **Bare ACR122U board**: measured 60 × 91 mm, placed **in landscape** in the
   backrest cavity (positioning stops), antenna on the left, cable exiting on
   the right toward the offset passage in the base.
2. **Panel-mount USB-C socket**: `usbc_w / usbc_h` cut-out and `usbc_screw_dx`
   spacing; check before printing the base.
3. **M3 inserts**: `insert_d` / `insert_depth` to match your inserts.

## Regenerating the STLs

```bash
for p in shell faceplate backrest backrest_cover lid icon_plate; do
  openscad -o stl/$p.stl -D "part=\"$p\"" mcard.scad
done
```

`part="assembly"` in the GUI shows the overall view.
