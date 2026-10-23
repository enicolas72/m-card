# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**M-Card** is a DIY hardware device: place a CD case or vinyl sleeve fitted with an RFID card on it, and the matching album plays on **Roon** (server runs on the user's Mac). `versions/` is **local only** (git-ignored, the owner's private material): original spec `versions/idea/PROJECT.md` (French, archival, fully realized), sketches, and prototype photos `versions/proto2/` (lightweight copies used by the presentation page live in `marketing/build/img/`). **Prototype 2 (the working, in-use device) is archived as a whole in `proto2/`** (`proto2/software`, `proto2/enclosure`, `proto2/docs`); **Prototype 3 is the active work in `proto3/`** (same layout, started 2026-10-23 as a copy of proto 2 and evolving from it) — all new work goes there; don't modify `proto2/` unless fixing the deployed device. `marketing/` stays at the root (public Pages URL) and presents proto 2. Root README.md is a short pitch + link to the GitHub Pages presentation https://enicolas72.github.io/m-card/marketing/ — don't duplicate the page's content there. Licensed MIT (`LICENSE`); album artwork in `marketing/build/cards/` is excluded.

Hardware: Raspberry Pi 3 B+ (Wi-Fi), ACS ACR122U NFC reader kept on USB (no soldering), LCD 2004A with PCF8574 I2C backpack, 3 GPIO buttons prev/playpause/next (BCM 5/6/13; legacy 4-button names play/pause still map), panel-mount USB-C power. No network access besides local Roon; no auth on the web UI by design.

## Language

**Everything written in this project is in English**: docs, READMEs, sample configs, code comments and docstrings, log messages, user-facing strings (LCD, web UI), commit messages and new LOG.md entries. The whole codebase has been translated (2026-10-18); only LOG.md entries before that date remain in French (historical record, leave them). Accented proper nouns in tests (Angèle, Oxygène, the `to_lcd_ascii` sentence) are deliberate test data. Only the conversation with the user stays in French.

## Commands

Software work happens in `proto3/software/` with its own local venv (`proto3/software/.venv`; proto 2 has its own in `proto2/software/.venv`, plain python3 + flask/pyyaml/pytest — no Pi hardware libs on the Mac):

```bash
cd proto3/software
./.venv/bin/python -m pytest tests/          # run tests (79, all mocked hardware)
./.venv/bin/python -m pytest tests/test_controller.py -k cooldown   # single test
./.venv/bin/python -m mcard --config <dir> --fake   # run app with simulated hardware
                                                    # (type UID + Enter = place card; Enter = remove; EOF = quit)
```

3D enclosure (`proto3/enclosure/`): OpenSCAD snapshot is installed at `/opt/homebrew/bin/openscad` (the 2021.01 x86_64 cask hangs on this arm64 Mac — don't use it).

```bash
cd proto3/enclosure
openscad -o stl/shell.stl -D 'part="shell"' mcard.scad   # parts: shell|backrest|backrest_cover|lid|assembly
```

Marketing page (`marketing/`): `index.html` is a single self-contained file (everything inlined, works offline) built from `marketing/build/` — `npm install && npm run build`; `./export-stl.sh` re-exports the assembled enclosure parts (`parts.scad` includes `proto2/enclosure/mcard.scad` with `part = "none"`). Copy is in English. The card strip is canvas-drawn on purpose (CSS-animated strip + mask lost tiles in Safari next to the WebGL context). `card-covers/` (source artwork, PSD) is git-ignored.

Deployment to the Pi is via `scp` + `sudo bash install.sh` (see `proto3/docs/SETUP.md`; the device in use runs proto 2). Never `pip install` the Pi-only deps (nfcpy, RPLCD, gpiozero, roonapi) on the Mac — all hardware imports are lazy so tests/fake mode run without them; keep it that way when adding code.

## Architecture

Single event queue, one central controller, one thread per peripheral. Every hardware component has a fake twin in `mcard/fakes.py`; `app.py` picks real vs fake at wiring time (`--fake`).

```
proto3/software/mcard/
  events.py       dataclass events: CardPresented/CardRemoved/ButtonPressed/NowPlaying/RoonConnection/Shutdown
  controller.py   consumes the queue; business rules: known card → play, unknown → auto-add TODO,
                  card removed → none (default)/pause/stop, buttons → transport. Holds `status` dict for the web UI.
  config.py       AppConfig (mcard.yaml merged over DEFAULTS) + AlbumStore (albums.yaml, thread-safe,
                  rewrites file with ALBUMS_HEADER on add_todo)
  roon_client.py  supervised reconnect loop; discovery→token pairing→zone resolution; pushes NowPlaying events
  nfc_reader.py   nfcpy loop; connect() blocks while card present (on-connect returns True), USB error backoff
  display.py      Display (4 lines, scrolling ticker thread, accent transliteration for HD44780) over a
                  LcdBackend (CharLcdBackend real / FakeLcdBackend / MemoryLcd in tests)
  webserver.py    Flask: / status, /logs (RO, tail+download), /config/<name> (RW, YAML-validated, raw GET at /config/<name>/download,
                  hot-reloads albums.yaml), /search (Roon library search → `path:` fragment,
                  POST /search/assign writes it via AlbumStore.assign). UI strings are English in code; `TRANSLATIONS` maps them for `web.language` (en|fr). Only EDITABLE_FILES reachable.
  app.py          composition root; Controller gets `roon` injected after creation (RoonClient needs the queue)
```

Config lives in a directory (`--config`), two files: `mcard.yaml` (settings) and `albums.yaml` (UID → album/artist or explicit Roon browse `path`). UIDs are uppercased everywhere.

## Gotchas

- ACR122U on Linux requires blacklisting `pn533_usb/pn533/nfc` kernel modules (install.sh does it) or nfcpy can't open the reader.
- Roon pairing: first run needs the extension enabled in Roon → Settings → Extensions; token persisted to `roon.token_file`.
- `roonapi.play_media(zone_id, path)` matches each path element by exact title. Roon exposes no stable album ID (browse `item_key`s are session-scoped), so `path: ["Library", "Artists", <artist>, <album>]` is the stable identifier; /search builds it from the albums hierarchy (subtitle = artist), falling back to `["Library", "Albums", <title>]` when the artist isn't in the Artists hierarchy.
- Tests import `conftest.py` helpers (`MemoryLcd`, `SpyRoon`) directly (`from conftest import ...`).
- STL exports are ASCII; print orientations are baked into the `part=` transforms (shell prints upside-down).
