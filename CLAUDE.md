# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**M-Card** is a DIY hardware device: place a CD case or vinyl sleeve fitted with an RFID card on it, and the matching album plays on **Roon** (server runs on the user's Mac). Full spec: `PROJECT.md` (French, read it first); sketches, hardware photos and prototype photos in `versions/`. User-facing docs are in French — keep communication with the user in French.

Hardware: Raspberry Pi 3 B+ (Wi-Fi), ACS ACR122U NFC reader kept on USB (no soldering), LCD 2004A with PCF8574 I2C backpack, 3 GPIO buttons prev/playpause/next (BCM 5/6/13; legacy 4-button names play/pause still map), panel-mount USB-C power. No network access besides local Roon; no auth on the web UI by design.

## Commands

All software work happens in `software/` with the local venv (`software/.venv`, plain python3 + flask/pyyaml/pytest — no Pi hardware libs on the Mac):

```bash
cd software
./.venv/bin/python -m pytest tests/          # run tests (29, all mocked hardware)
./.venv/bin/python -m pytest tests/test_controller.py -k cooldown   # single test
./.venv/bin/python -m mcard --config <dir> --fake   # run app with simulated hardware
                                                    # (type UID + Enter = place card; Enter = remove; EOF = quit)
```

3D enclosure (`enclosure/`): OpenSCAD snapshot is installed at `/opt/homebrew/bin/openscad` (the 2021.01 x86_64 cask hangs on this arm64 Mac — don't use it).

```bash
cd enclosure
openscad -o stl/shell.stl -D 'part="shell"' mcard.scad   # parts: shell|backrest|backrest_cover|lid|assembly
```

Deployment to the Pi is via `scp` + `sudo bash install.sh` (see `docs/SETUP.md`). Never `pip install` the Pi-only deps (nfcpy, RPLCD, gpiozero, roonapi) on the Mac — all hardware imports are lazy so tests/fake mode run without them; keep it that way when adding code.

## Architecture

Single event queue, one central controller, one thread per peripheral. Every hardware component has a fake twin in `mcard/fakes.py`; `app.py` picks real vs fake at wiring time (`--fake`).

```
software/mcard/
  events.py       dataclass events: CardPresented/CardRemoved/ButtonPressed/NowPlaying/RoonConnection/Shutdown
  controller.py   consumes the queue; business rules: known card → play, unknown → auto-add TODO,
                  card removed → none (default)/pause/stop, buttons → transport. Holds `status` dict for the web UI.
  config.py       AppConfig (mcard.yaml merged over DEFAULTS) + AlbumStore (albums.yaml, thread-safe,
                  rewrites file with ALBUMS_HEADER on add_todo)
  roon_client.py  supervised reconnect loop; discovery→token pairing→zone resolution; pushes NowPlaying events
  nfc_reader.py   nfcpy loop; connect() blocks while card present (on-connect returns True), USB error backoff
  display.py      Display (4 lines, scrolling ticker thread, accent transliteration for HD44780) over a
                  LcdBackend (CharLcdBackend real / FakeLcdBackend / MemoryLcd in tests)
  webserver.py    Flask: / status, /logs (RO, tail+download), /config/<name> (RW, YAML-validated,
                  hot-reloads albums.yaml). Only files in EDITABLE_FILES are reachable.
  app.py          composition root; Controller gets `roon` injected after creation (RoonClient needs the queue)
```

Config lives in a directory (`--config`), two files: `mcard.yaml` (settings) and `albums.yaml` (UID → album/artist or explicit Roon browse `path`). UIDs are uppercased everywhere.

## Gotchas

- ACR122U on Linux requires blacklisting `pn533_usb/pn533/nfc` kernel modules (install.sh does it) or nfcpy can't open the reader.
- Roon pairing: first run needs the extension enabled in Roon → Settings → Extensions; token persisted to `roon.token_file`.
- `roonapi.play_media(zone_id, ["Library", "Albums", <name>])` needs the exact Roon album name; ambiguous names use an explicit `path:` in albums.yaml.
- Tests import `conftest.py` helpers (`MemoryLcd`, `SpyRoon`) directly (`from conftest import ...`).
- STL exports are ASCII; print orientations are baked into the `part=` transforms (shell prints upside-down).
