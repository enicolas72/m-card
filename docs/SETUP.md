# Software installation — M-Card

## 1. Prepare the SD card

1. **Raspberry Pi Imager** (on the Mac) → *Raspberry Pi OS Lite (64-bit)*.
2. In the Imager options (gear icon / "Edit settings"):
   - hostname: `mcard`
   - **SSH enabled**, user `pi` + password
   - **Wi-Fi**: SSID + password of the network Roon runs on, and your country
   - (this is where Wi-Fi is configured; the device needs no other network
     access, and no Internet after installation)
3. Write, insert into the Pi, boot, then: `ssh pi@mcard.local`

> Note: the installation itself (apt/pip) needs temporary Internet access.
> In operation, M-Card only talks to the local Roon server.

## 2. Install M-Card

```bash
# from the Mac, copy the software/ folder to the Pi:
rsync -a --exclude .venv --exclude __pycache__ software/ pi@mcard.local:mcard-software/

# then on the Pi:
ssh pi@mcard.local
cd mcard-software
sudo bash install.sh
sudo reboot
```

`install.sh` does everything: packages, service user, Python venv, I2C
activation, NFC kernel module blacklist (required for the ACR122U), udev rule,
default configs in `/etc/mcard`, enabled systemd service.

To update later, run the same `rsync`, then `sudo bash install.sh` and
`sudo systemctl restart mcard` (no reboot needed; existing configs in
`/etc/mcard` are kept).

## 3. First start

```bash
sudo systemctl start mcard
journalctl -u mcard -f
```

1. The LCD shows "M-Card / Starting...", then "Place an album".
2. **Enable the extension**: on the Mac, Roon → *Settings* → *Extensions*
   → **Enable** next to "M-Card". (The log shows it waiting.)
3. Place an RFID card on the reader:
   - unknown card → the LCD shows its UID, and an `album: TODO` entry appears
     in `/etc/mcard/albums.yaml`
   - pair the album: `/search` page of the web console (search →
     "Assign to this card"), or replace `TODO`
     by hand in `/etc/mcard/albums.yaml`
   - place the card again → the album starts.

## 4. Web console (logs + configuration)

From any browser on the local network:

| URL | Contents |
|---|---|
| `http://mcard.local:8088/` | status: current track, Roon connection, last card |
| `http://mcard.local:8088/logs` | log (read-only, downloadable) |
| `http://mcard.local:8088/config` | edit `albums.yaml` and `mcard.yaml` (YAML validated before saving, albums hot-reloaded; every save rewrites `albums.yaml` in the canonical format) |
| `http://mcard.local:8088/config/albums.yaml/download` | raw file, for backups: `curl -fsS http://mcard.local:8088/config/albums.yaml/download -o albums-$(date +%Y%m%d-%H%M).yaml` |
| `http://mcard.local:8088/search` | free-text Roon library search → exact `path:` snippet to copy, or "Assign to this card" button (TODO cards listed first) |

## 5. Useful settings (`/etc/mcard/mcard.yaml`)

- `roon.zone_name`: exact name of the zone to control (otherwise the first zone).
- `behavior.on_card_removed`: `none` (default: the album keeps playing,
  buttons stay active), `pause` or `stop`.
- `lcd.i2c_address`: `0x27` by default; check with `i2cdetect -y 1`.
- `lcd.backlight_timeout_s`: backlight sleeps after N s without interaction
  (default 120; 0 = always on). Any card or button wakes it up.
- `web.language`: web console language, `en` (default) or `fr`.
- After a change: `sudo systemctl restart mcard`.

## 6. Development without a Raspberry Pi (fake mode)

On the Mac, with no hardware at all:

```bash
cd software
python3 -m venv .venv && ./.venv/bin/pip install flask pyyaml
mkdir -p /tmp/mcard && cp config/*.example /tmp/mcard/
mv /tmp/mcard/mcard.yaml.example /tmp/mcard/mcard.yaml
mv /tmp/mcard/albums.yaml.example /tmp/mcard/albums.yaml
# point log.file to a writable path, then:
./.venv/bin/python -m mcard --config /tmp/mcard --fake
```

Type a UID (e.g. `04A1B2C3`) + Enter to "place a card", Enter alone to remove
it. The LCD is drawn in the terminal and Roon is simulated.

## 7. Troubleshooting

| Symptom | Things to check |
|---|---|
| `no Roon server found` | same network/VLAN as the Mac? Is Roon running? Try `roon.host: <mac-ip>` |
| NFC reader not found | `lsusb` should list `072f:2200`; check the blacklist: `lsmod \| grep pn533` must be empty; reboot |
| Blank LCD | contrast (potentiometer on the back); `i2cdetect -y 1` → address `27` or `3F` |
| Garbage characters on the LCD | GND/VCC swapped on the backpack, or SDA/SCL wires too long |
| Extension never shows up in Roon | Mac firewall: allow Roon; the Pi and the Mac must be on the same subnet |
| Buttons do nothing | BCM numbering (GPIO5 = physical pin 29); watch `journalctl -u mcard -f` |
