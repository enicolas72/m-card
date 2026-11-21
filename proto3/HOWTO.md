# Prototype 3 — HOWTO

Proto 3 evolves from proto 2 (copied from `../proto2/`). Changes so far:

| | Proto 2 | Proto 3 |
|---|---|---|
| Screen | LCD 2004A, 20×4 characters, blue backlight, I2C | **OLED 3.12" 256×64, white on black**, 16 grey levels, SPI |
| RFID reader | ACR122U board out of its shell (~91 mm wide, USB) | **PN532 NFC module V3** (42.7 × 40.4 mm, UART) |

Status (2026-11-21): **both parts validated on the hardware**, on a second
Pi 3 (`mcard2`). PN532 (2026-10-25): cards read over UART, albums play on
Roon (the extension shows up as "M-Card 0.2", next to the proto 2 device's
"M-Card 0.1"). OLED (2026-11-21): wired as in the diagram below, luma test
and the M-Card screens work. The enclosure and the other docs (`docs/`)
still describe proto 2.

## 1. Parts

### Screen: OLED 3.12" 256×64, white, SSD1322

- Ordered: **Audiophonics** ref. 14604, "Écran OLED 3.12" SPI / IIC 256x64
  Blanc", €29.90 incl. VAT, ships from France, header pre-soldered.
- Active area ~76.8 × 19.2 mm: same width as the 2004A's window, less tall,
  but 256 pixels across instead of 20 characters.
- OLED = true black: unlit pixels emit nothing, so "white text on a black
  background" is exactly what a white OLED gives (a "blue background" is an
  LCD backlight, not an OLED option).
- Driven by the Python library `luma.oled` (SSD1322, 4-wire SPI).

**Larger screen, later** — same SSD1322 controller, so the same software
(only the layout would grow):

| Model | Colour | Active area | Price (2026-10) | Notes |
|---|---|---|---|---|
| Newhaven NHD-5.5-25664UCG3 | green (yellow announced) | 136.9 × 35.1 mm | ~€88 shipped (DigiKey) | module 147.2 × 64.15 mm, 3.3 V, SPI by jumpers |
| BuyDisplay ER-OLEDM055-1W | white | 136.9 × 35.1 mm | ~$70 + shipping from China | take the **M** version (breakout board), the bare panel has a 30-pin FPC |

Colour screens were considered and set aside for now:
- 4.58" 320×960 bar IPS (BuyDisplay ER-TFT4.58-1, ~$15): good format, but the
  ST7701S takes pixels over an 18-bit RGB bus = Pi DPI output, ~22 GPIOs and
  a custom kernel overlay.
- 6.86" 480×1280 "PC case" screens: mostly USB-only (proprietary Windows
  software), and too large for the sloped face (module ~189 × 77 mm). Only
  worth it with an HDMI input and a redesigned enclosure.

### RFID reader: PN532 NFC module V3

- Elechouse design, cloned everywhere (often red), ~€5–10; 42.7 × 40.4 ×
  4 mm, antenna on the board, read range ~4–7 cm depending on the tag.
- Same PN532 chip as inside the ACR122U: same cards, **same UIDs**, so
  `albums.yaml` stays valid; `nfcpy` drives it over the serial port.
- No kernel module blacklist needed (unlike the ACR122U).
- If reading through a vinyl sleeve turns out too weak: Elechouse V4
  (6–8 cm).

## 2. Wiring

The full wiring reference is [`docs/WIRING.md`](docs/WIRING.md): Pi header
map, both modules, buttons, power and bring-up order, with an overview
diagram ([`docs/wiring-diagram.svg`](docs/wiring-diagram.svg)) and one
detail diagram per module ([`docs/pn532-wiring.svg`](docs/pn532-wiring.svg),
[`docs/oled-wiring.svg`](docs/oled-wiring.svg)).

In short: PN532 on pins 1 / 6 / 8 / 10, OLED on pins 17–24 (not 21),
buttons unchanged on 29 / 31 / 33 + GND 39. The LCD is gone, which frees
the I2C pins. Two traps, both met on the first build:
- the PN532's mode switches must be on **0-0** (HSU) and are read at
  power-on only;
- the Audiophonics OLED's **2×8 header is unlabelled** on the side where
  the wires plug in: odd pins are in the column next to the glass, and
  screen pins 1 (GND) and 2 (VDD) are side by side.

## 3. Software installation

The proto 3 software lives in `proto3/software/`. **Do not deploy it on the
proto 2 device as is**: its defaults expect the OLED and the PN532 (a
missing SPI screen raises no error, the LCD would just stay blank). To run
it on proto 2 hardware, set `display.type: lcd` and `nfc.device: usb`.

```bash
# from the Mac (repo root)
rsync -a --exclude .venv --exclude __pycache__ proto3/software/ pi@mcard.local:mcard-software/
ssh pi@mcard.local
cd mcard-software && sudo bash install.sh
sudo reboot     # required: UART, SPI and Bluetooth changes
```

`install.sh` now also:
- enables **SPI** (OLED),
- frees the **PL011 UART** on GPIO 14/15 for the PN532: serial console off,
  UART hardware on, `dtoverlay=disable-bt` in `config.txt` (Bluetooth is not
  used; the mini UART is not reliable enough), `hciuart` disabled,
- adds the `mcard` user to the `spi` and `dialout` groups,
- installs `luma.oled`, Pillow, spidev and rpi-lgpio (OLED DC/RST lines).

### Existing `/etc/mcard/mcard.yaml`

`install.sh` never overwrites it. Add the new sections from
`config/mcard.yaml.example`:

```yaml
nfc:
  device: "tty:AMA0:pn532"   # "usb" = ACR122U

display:
  type: oled                 # oled | lcd
  sleep_timeout_s: 120       # replaces lcd.backlight_timeout_s

oled:
  gpio_dc: 24
  gpio_rst: 25
  rotate: 0                  # 2 = panel mounted upside down
  contrast: 180              # 0-255
```

and remove `lcd.backlight_timeout_s` (the log warns about unknown keys).

## 4. Validating the parts (one at a time)

Stop the service while testing: `sudo systemctl stop mcard`.

### PN532 first (simplest)

```bash
ls -l /dev/ttyAMA0                                  # must exist after the reboot
sudo -u mcard /opt/mcard/venv/bin/python -c \
  "import nfc; clf = nfc.ContactlessFrontend('tty:AMA0:pn532'); print(clf); clf.close()"
```

It should print ` on /dev/ttyAMA0` (validated 2026-10-25; nfcpy has no
vendor/product name for a serial reader, hence the bare text). An error
here = see Troubleshooting. `python -m nfc --search-tty` also lists the
readers found on serial ports. Then start the service, place a
few known cards: they must play exactly as before (same UIDs). Try a card in
a vinyl sleeve, bottom corner on the backrest side, to check the range.

### Then the OLED

```bash
sudo systemctl stop mcard                           # it holds the DC/RST GPIOs
ls /dev/spidev0.*                                   # spidev0.0 must exist
cd /tmp                                             # lgpio needs a writable cwd
sudo -u mcard /opt/mcard/venv/bin/python - <<'EOF'
import time
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1322
dev = ssd1322(spi(port=0, device=0, gpio_DC=24, gpio_RST=25))
with canvas(dev) as draw:
    draw.rectangle(dev.bounding_box, outline="white")
    draw.text((10, 25), "Hello M-Card", fill="white")
time.sleep(15)   # luma blanks the panel when the script exits
EOF
```

A white frame with "Hello M-Card" for 15 s = wiring OK. (Not `input()`:
the heredoc is Python's stdin, so it would return at once and the screen
would only flash.)

Then `sudo systemctl start mcard`: "Place an album" in large type.

## 5. What the OLED displays

- **Now playing**: state icon (▶ ❚❚ ■) + artist on top, **track title in
  large type**, album below. Lines too wide scroll pixel by pixel (2 s pause
  on the start of the text, 30 px/s).
- Accents and typography displayed as-is (bundled **Inter** font, latin
  subset, SIL OFL: `software/mcard/fonts/`). Non-latin scripts (Japanese,
  Cyrillic...) are not in the subset; `oled.font` accepts any TrueType file.
- **Burn-in protection**: the screen switches off after
  `display.sleep_timeout_s` (any card/button wakes it), the picture moves by
  one pixel every 5 minutes, and the default contrast is 180/255.
- **Live preview** on the web console's status page (`/display.png`), also
  in `--fake` mode: the screen can be designed without the hardware.

```bash
cd proto3/software
./.venv/bin/python -m mcard --config <config-dir> --fake   # then open http://localhost:8088/
```

## 6. Troubleshooting

| Symptom | Things to check |
|---|---|
| `TimeoutError: [Errno 110]` from the test above (nothing received) | `mcard` service stopped? Mode switches on 0-0, then power-cycle (validated cause); TX/RX crossed |
| `NFC reader error ... tty:AMA0` in the log | reboot done? `dtoverlay=disable-bt` in `/boot/firmware/config.txt`; serial console off (`raspi-config` → Interface → Serial: login shell **no**, hardware **yes**); TX/RX crossed; switches on HSU |
| Reader found but no card detected | 3.3 V power; card closer to the antenna; try without the sleeve |
| `/dev/spidev0.0` missing | SPI not enabled: `sudo raspi-config nonint do_spi 0`, reboot |
| OLED stays black, no error | module in 4-wire SPI mode? CS on pin 24, DC on 18, RST on 22; `oled.contrast` not 0 |
| Picture upside down | `oled.rotate: 2` |
| Scrolling jerky / high CPU | lower `oled.fps` (default 20) |
