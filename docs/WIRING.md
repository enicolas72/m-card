# Wiring — M-Card V0.1

Visual diagram: [`wiring-diagram.svg`](wiring-diagram.svg)

No soldering is needed for the breadboard phase: everything uses
female-female Dupont wires. The ACR122U reader stays on USB.

## Overview

```
                        ┌────────────────────────┐
   USB-C charger ───────► USB-C socket (rear)    │
                        │        │ micro-USB     │
                        │  ┌─────▼──────────┐    │  captive USB cable ┌───────────┐
                        │  │ Raspberry Pi 3B+ ◄──┼────────────────────► ACR122U   │
                        │  └─┬────────┬─────┘    │                    │ (behind   │
                        │    │ I2C    │ GPIO     │                    │ the slot) │
                        │  ┌─▼────┐ ┌─▼───────┐  │                    └───────────┘
                        │  │ LCD  │ │ 3 buttons│ │
                        │  │ 20×4 │ │  ⏮ ⏯ ⏭  │  │
                        │  └──────┘ └─────────┘  │
                        └────────────────────────┘
         Wi-Fi ↔ Roon server (Mac): no other network connection
```

## LCD 2004 (PCF8574 I2C backpack): 4 wires

| LCD backpack | Pi pin (physical) | Pi signal |
|---|---|---|
| GND | 6 | GND |
| VCC | 2 | 5 V |
| SDA | 3 | GPIO2 (SDA1) |
| SCL | 5 | GPIO3 (SCL1) |

- I2C address: usually `0x27` (check with `i2cdetect -y 1`; if it shows `0x3F`,
  set `lcd.i2c_address` in `mcard.yaml`).
- Contrast: small blue potentiometer on the back of the backpack.
- **Logic levels**: the backpack runs on 5 V, the Pi on 3.3 V. The Pi's own
  pull-ups (1.8 kΩ to 3.3 V) dominate the backpack's: this direct connection
  is the standard setup used everywhere and works reliably. Purists can add a
  bidirectional level shifter on SDA/SCL (see BOM, optional).

## Buttons: 6 wires

Each momentary button connects a GPIO pin to GND (internal pull-up enabled in
software, press = low level). On the faceplate, from bottom to top:
⏮ prev, ⏯ play/pause (toggle), ⏭ next.

| Button | GPIO (BCM) | Pi pin (physical) | Common GND |
|---|---|---|---|
| ⏮ prev | GPIO5 | 29 | 39 |
| ⏯ play/pause | GPIO6 | 31 | 39 |
| ⏭ next | GPIO13 | 33 | 39 |

The 3 GND returns can be daisy-chained and brought back to pin 39 with a
single wire (or spread over pins 30/34/39).

The pins are deliberately adjacent (29→33, on the outer row of the header,
printed one under the other on a cobbler) and far from I2C: clean, readable
wiring.

## ACR122U RFID reader: USB

- Plugged into a USB-A port of the Pi with its original captive cable
  (the slack coils up inside the base).
- **No electronic modification**: for integration, just remove the white
  shell (4 screws under the feet); the bare board mounts behind the slot wall
  (read range ~4 cm, easily goes through 3 mm of PLA plus a CD case).
- On the system side, the `pn533_usb`/`pn533`/`nfc` kernel modules must be
  blacklisted (done by `install.sh`, see SETUP.md), otherwise Linux grabs
  the reader.

## Power

- Panel-mount female USB-C socket in the rear wall → micro-USB cable to the
  Pi's power input. From the outside, only a USB-C port is visible.
- 5 V / 3 A charger recommended (Pi 3B+ ~1.2 A + ACR122U 0.2 A + LCD 0.05 A,
  comfortable margin).

## Breadboard phase (before final assembly)

1. Wire the LCD (4 wires) and check: `i2cdetect -y 1` should show `27`.
2. Wire 3 tactile 6×6 mm buttons on a breadboard to GPIO 5/6/13 and GND.
3. Plug the ACR122U into USB.
4. Run `python -m mcard --config /etc/mcard` and validate:
   known card → Roon playback; unknown card → TODO entry; buttons →
   transport; LCD → album/track.
5. Only then take it apart and integrate it into the enclosure (ASSEMBLY.md).
   The enclosure's 12 mm buttons are wired exactly the same way.
