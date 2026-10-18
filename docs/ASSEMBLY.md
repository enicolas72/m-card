# Assembly — M-Card (enclosure V0.3)

Prerequisites: the 6 printed parts (see `enclosure/README.md`), 14 M3
threaded inserts, the screws, and electronics **already validated on a
breadboard** (see `docs/WIRING.md`).

## 1. Threaded inserts

Each location has a chamfered pocket: drop the insert in (it centers itself),
press it in with a soldering iron (~230 °C for PLA), let it cool.

- 4 in the front frame of the base (from the front),
- 4 in the floor bosses (from below),
- 2 under the backrest, 4 at the back of the backrest.

## 2. Faceplate (flat, on the bench)

1. **Color plate**: glue `icon_plate` (contrasting color) into the recess on
   the back of the faceplate, under the icon cut-outs; a drop of
   cyanoacrylate or thin double-sided tape is enough.
2. **LCD**: set the module on the 4 posts, panel in the window, drive
   4 × M3×8 socket head screws into the Ø2.8 pilot holes (the screw taps its
   own thread in the PLA); easy access since the faceplate lies flat.
3. **Buttons**: fit the 3 × 12 mm buttons (⏮ at the bottom, ⏯ in the middle,
   ⏭ at the top, facing their icons) and tighten the nuts.
4. Wire the LCD and buttons (Dupont wires, see WIRING.md), then **screw the
   faceplate** onto the sloped console of the base: 4 × M3×8 socket head
   screws (heads sunk in their counterbores).

## 3. Backrest + reader

1. Feed the USB-A plug of the reader cable through the oblong opening of the
   backrest (right side), then through the one in the top face of the base
   (the slack coils up inside the base).
2. Stick the reader board against the front wall of the cavity (double-sided
   tape), **in landscape between the two stops: antenna (the large flat
   area) on the left, cable exiting on the right**, components facing back.
   The rest of the cavity stays free for the cable.
3. Screw on the flush back plate (4 × M3×8 socket head).
4. Set the backrest on the base: the 2 pegs line it up, then 2 × M3×8 socket
   head screws from inside the enclosure, through the top face.

## 4. Rear and bottom

1. Screw the panel-mount USB-C socket to the rear (2 × M2), plug the
   micro-USB pigtail into the Pi's power input.
2. Screw the Raspberry Pi onto the floor posts (4 × M2.5×6), USB ports
   facing the rear.
3. Connect: reader cable → Pi USB, LCD/button Dupont wires → GPIO.
4. Close the bottom (4 × M3×8 socket head, heads sunk).

## 5. Final test

1. Plug in the USB-C charger: "Place an album" appears
   within ~30 s.
2. Stand a CD case with an RFID card in the slot: Roon starts playing.
3. Stand a vinyl record: the through slot lets it rest at the bottom of the
   groove, leaning against the backrest.
4. Check the 3 buttons, then `http://mcard.local:8088/`.

## Tips

- The CD case goes in **with the RFID card facing back** (backrest side).
  For a vinyl record, slip the card into the sleeve, bottom corner, backrest
  side; mark that corner with a discreet sticker.
- If reading through the sleeve is unreliable, move the card closer to the
  bottom-rear corner (~4 cm range from the antenna).
- Spiral wrap or cable ties for the internal wiring, so the bottom closes
  without pinching anything.
