# M-Card

**Re-materialize your music.** One card per album, or one tucked inside the vinyl
sleeve you already own: drop it in the slot and the album plays on **Roon**. No app,
no phone, no cloud.

👉 **[See M-Card in action: interactive 3D, display, web console](https://enicolas72.github.io/m-card/marketing/)**

An open-source DIY device: Raspberry Pi 3 B+, ACR122U NFC reader, 20×4 LCD,
three push buttons, and a 3D-printed enclosure.

## Repository

| Path | Contents |
|---|---|
| [`software/`](software/) | Python application (`mcard/`), sample configs, `install.sh`, systemd service, tests |
| [`docs/BOM.md`](docs/BOM.md) | bill of materials, no custom PCB |
| [`docs/WIRING.md`](docs/WIRING.md) | full wiring + [SVG diagram](docs/wiring-diagram.svg) |
| [`docs/SETUP.md`](docs/SETUP.md) | SD card, install, Roon pairing, web console, troubleshooting |
| [`docs/ASSEMBLY.md`](docs/ASSEMBLY.md) | assembly into the enclosure |
| [`enclosure/`](enclosure/) | parametric 3D enclosure (OpenSCAD) + print-ready STLs |
| [`marketing/`](marketing/) | the presentation page: one self-contained offline HTML file, sources in `marketing/build/` |
| [`versions/`](versions/) | prototype photos |

## Build one

1. **Order** the few parts listed in the [BOM](docs/BOM.md).
2. **Wire** the LCD and buttons ([WIRING.md](docs/WIRING.md)); plug the ACR122U into USB.
3. **Install** on the Pi ([SETUP.md](docs/SETUP.md)): `sudo bash install.sh`.
4. **Enable** the M-Card extension in Roon → Settings → Extensions.
5. **Pair cards**: an unknown card shows up as `TODO` in `albums.yaml`. Open
   `http://mcard.local:8088/search`, find the album, and click *Associer à cette carte* (assign to this card; the device UI is in French).
   This writes an exact Roon path, e.g. `path: ["Library", "Artists", "<artist>", "<album>"]`.
6. **Print** the enclosure and assemble it ([ASSEMBLY.md](docs/ASSEMBLY.md)).

Back up your card mappings at any time:

```bash
curl -fsS http://mcard.local:8088/config/albums.yaml/download -o backups/albums-$(date +%Y%m%d-%H%M).yaml
```

## Try it without hardware

```bash
cd software && python3 -m venv .venv && ./.venv/bin/pip install flask pyyaml pytest
./.venv/bin/python -m mcard --config <config-dir> --fake
./.venv/bin/python -m pytest tests/
```

In `--fake` mode, type a card UID + Enter to "place" a card and Enter alone to remove
it. The LCD is drawn in the terminal and Roon is simulated.

## Software architecture

A single event queue, one central controller, and one thread per peripheral. Every
hardware component has a fake twin, so development needs no Pi:

```
nfc_reader (thread) ──┐                         ┌──► roon_client ──► Roon API
buttons    (GPIO)  ───┼──► queue ──► controller ─┼──► display ──► LCD (I²C)
roon callbacks ───────┘                         └──► albums.yaml (auto TODO entries)
                    webserver (Flask): status / logs / config / Roon library search
```

## License & credits

Code, documentation and enclosure files are released under the [MIT License](LICENSE).

Independent DIY project, not affiliated with or endorsed by Roon Labs. Roon is a
trademark of Roon Labs LLC. Album artwork shown on the presentation page (and in
`marketing/build/cards/`) belongs to its respective owners and is not covered by
the MIT License.
