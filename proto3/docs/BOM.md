# Bill of materials (BOM) — M-Card V0.1

## Already on hand

| Part | Role | Note |
|---|---|---|
| Raspberry Pi 3 Model B+ | Embedded computer | Built-in Wi-Fi, plenty of power |
| micro-SD card (≥ 8 GB) | System | Raspberry Pi OS Lite 64-bit |
| LCD 2004A 20×4 + PCF8574 I2C backpack ("MH") | Album/track display | Only 4 wires (backpack usually pre-soldered) |
| ACS ACR122U (PN532) | 13.56 MHz RFID reader | Stays on USB, no soldering; taken out of its shell for integration |
| 13.56 MHz RFID cards (MIFARE/NTAG) | Album identification | Only the UID is used, nothing is written to the card |
| 3D printer | Enclosure | PLA or PETG |

## To buy (~€15–25)

| Qty | Part | Role | Where (search terms) | Rough price |
|---|---|---|---|---|
| 3 | 12 mm momentary push button, panel mount | prev / play-pause / next | Amazon: "12mm momentary push button" (packs of 5–10) | ~€8 |
| 1 | Panel-mount female USB-C → male micro-USB (25–30 cm cable) | Clean rear power port | Amazon: "USB C panel mount micro USB" | ~€8 |
| 1 | Female-female Dupont jumper wires, 20 cm | LCD + buttons ↔ GPIO | Amazon / electronics kit | ~€5 |
| 14 | M3 heat-set threaded inserts + matching M3 socket head cap screws (see enclosure/README.md) | Enclosure assembly | Amazon: "M3 heat set inserts 3D printing" | ~€10 (pack) |

Power: USB-C charger, 5 V ≥ 3 A (any recent phone charger), probably already on hand.

## Optional

| Part | Why |
|---|---|
| Breadboard + 6×6 mm tactile buttons | Test phase before final assembly (often included in a kit) |
| Bidirectional I2C level shifter (2 channels) | Extra caution on the 5 V ↔ 3.3 V I2C bus; in practice the direct connection works fine (see WIRING.md) |
| Double-sided tape / hot glue | Holding the ACR122U board in the backrest |

**Total to order: ~€15–25** depending on packs. No custom PCB is needed for V0.1: the I2C backpack brings the wiring down to 8 Dupont wires in total.
