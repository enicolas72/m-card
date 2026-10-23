"""Small local web server (Flask) — local network only.

- /            : device status (current track, Roon, last card)
- /logs        : log viewer (read-only)
- /config      : config file editor (albums.yaml, mcard.yaml),
                 /config/<name>/download for the raw file (backups)
- /search      : Roon album search → `path:` snippet for albums.yaml,
                 or direct assignment to a card
- /api/status  : JSON status

No authentication: the device is only reachable on the LAN
(no Internet connection, as per the original spec).
"""

from __future__ import annotations

import html
import json
import logging
from collections import deque
from pathlib import Path
from typing import Callable, Optional

from flask import Flask, Response, redirect, request, url_for

import yaml

log = logging.getLogger(__name__)

EDITABLE_FILES = ("albums.yaml", "mcard.yaml")

# UI languages (`web.language` in mcard.yaml). Strings are written in English
# in the code; other languages map each English string to its translation
# (missing entries fall back to English).
LANGUAGES = ("en", "fr")
TRANSLATIONS = {
    "fr": {
        "Status": "État",
        "Search": "Recherche",
        "connected": "connecté",
        "disconnected": "déconnecté",
        "State": "État",
        "Track": "Morceau",
        "Artist": "Artiste",
        "Card in slot": "Carte posée",
        "none": "aucune",
        "Card album": "Album de la carte",
        "last {n} lines": "{n} dernières lignes",
        "download all": "tout télécharger",
        "download": "télécharger",
        "Saved.": "Enregistré.",
        "Error: {error}": "Erreur : {error}",
        "Save": "Enregistrer",
        "Card {uid} assigned.": "Carte {uid} associée.",
        "Search Roon": "Recherche dans Roon",
        "title and/or artist": "titre et/ou artiste",
        "Roon not connected.": "Roon non connecté.",
        "No album found.": "Aucun album trouvé.",
        "Assign to this card": "Associer à cette carte",
        "{n} album(s) — copy under the card's UID in {link}, or assign directly to a card.":
            "{n} album(s) — à copier sous l'UID de la carte dans {link}, ou à associer "
            "directement à une carte.",
        "artist not in Library › Artists: path goes through the album list":
            "artiste absent de Library › Artists : chemin par la liste des albums",
        " — duplicate title, the first one will play": " — titre homonyme, le premier sera joué",
        "invalid path": "chemin invalide",
        "unknown card: {uid}": "carte inconnue : {uid}",
        "content must be a YAML mapping": "le contenu doit être un mapping YAML",
        "reload: {error}": "rechargement : {error}",
        "unknown file": "fichier inconnu",
        "file missing": "fichier absent",
        "log missing": "log absent",
        "(log file missing)": "(fichier de log absent)",
    },
}

PAGE = """<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M-Card</title>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; margin: 2rem auto; max-width: 46rem;
        padding: 0 1rem; background: #101418; color: #e6e6e6; }}
 a {{ color: #7ab8ff; }}
 h1 {{ font-size: 1.4rem; }} h1 a {{ color: inherit; text-decoration: none; }}
 nav a {{ margin-right: 1rem; }}
 table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
 td, th {{ text-align: left; padding: .35rem .6rem; border-bottom: 1px solid #2a3038; }}
 textarea {{ width: 100%; min-height: 24rem; background: #181d23; color: #e6e6e6;
            font-family: ui-monospace, monospace; font-size: .85rem; }}
 pre {{ background: #181d23; padding: 1rem; overflow-x: auto; font-size: .8rem; }}
 button {{ padding: .5rem 1.2rem; background: #2b6cb0; border: 0; color: white;
          border-radius: 4px; cursor: pointer; }}
 .err {{ color: #ff8080; }} .ok {{ color: #7dd87d; }} .warn {{ color: #e8c06a; font-size: .8rem; }}
 input, select {{ background: #181d23; color: #e6e6e6; border: 1px solid #2a3038;
                 padding: .45rem; border-radius: 4px; max-width: 100%; }}
 input[type=search] {{ width: 22rem; }}
 code {{ font-size: .75rem; word-break: break-all; }}
 td form {{ display: flex; gap: .4rem; flex-wrap: wrap; margin-top: .4rem; }}
 td form button {{ padding: .3rem .8rem; }}
</style></head><body>
<h1><a href="/">M-Card</a></h1>
<nav><a href="/">{nav_status}</a> <a href="/logs">Logs</a> <a href="/config">Configuration</a> <a href="/search">{nav_search}</a></nav>
{body}
</body></html>"""


def _tail(path: Path, lines: int) -> Optional[str]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        return "".join(deque(fh, maxlen=lines))


def create_app(
    config_dir: Path,
    log_file: Path,
    status_fn: Callable[[], dict],
    on_albums_saved: Callable[[], None],
    search_fn: Optional[Callable[[str], Optional[list[dict]]]] = None,
    cards_fn: Optional[Callable[[], dict]] = None,
    assign_fn: Optional[Callable[[str, list[str], str], object]] = None,
    language: str = "en",
) -> Flask:
    app = Flask("mcard")
    config_dir = Path(config_dir)
    log_file = Path(log_file)
    if language not in LANGUAGES:
        log.warning("Unknown web.language %r, falling back to English", language)
        language = "en"
    texts = TRANSLATIONS.get(language, {})

    def t(text: str, **fields) -> str:
        """Translated UI string (English if no translation), then formatted."""
        return texts.get(text, text).format(**fields)

    def page(body: str) -> str:
        return PAGE.format(lang=language, nav_status=t("Status"),
                           nav_search=t("Search"), body=body)

    @app.get("/")
    def index():
        s = status_fn()
        roon = (f'<span class="ok">{t("connected")}</span>' if s.get("roon_connected")
                else f'<span class="err">{t("disconnected")}</span>')
        rows = [
            ("Roon", f'{roon} {html.escape(s.get("roon_message", ""))}'),
            (t("State"), html.escape(s.get("state", ""))),
            ("Album", html.escape(s.get("album", ""))),
            (t("Track"), html.escape(s.get("track", ""))),
            (t("Artist"), html.escape(s.get("artist", ""))),
            (t("Card in slot"), html.escape(s.get("card_uid", "") or t("none"))),
            (t("Card album"), html.escape(s.get("card_album", ""))),
        ]
        table = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
        return page(f"<table>{table}</table>")

    @app.get("/api/status")
    def api_status():
        return status_fn()

    @app.get("/logs")
    def logs():
        n = max(10, min(int(request.args.get("n", "200")), 5000))
        tail = _tail(log_file, n)
        body = (f"<p>{t('last {n} lines', n=n)} — <a href='/logs?n=1000'>1000</a>, "
                f"<a href='/logs/download'>{t('download all')}</a></p>"
                f"<pre>{html.escape(t('(log file missing)') if tail is None else tail)}</pre>")
        return page(body)

    @app.get("/logs/download")
    def logs_download():
        if not log_file.exists():
            return Response(t("log missing"), status=404)
        return Response(
            log_file.read_bytes(),
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment; filename={log_file.name}"},
        )

    @app.get("/config")
    def config_list():
        items = "".join(
            f'<li><a href="/config/{name}">{name}</a></li>'
            for name in EDITABLE_FILES
            if (config_dir / name).exists()
        )
        return page(f"<ul>{items}</ul>")

    def _check_name(name: str) -> Path:
        if name not in EDITABLE_FILES:  # also guards against path traversal
            raise FileNotFoundError(name)
        return config_dir / name

    @app.get("/config/<name>")
    def config_edit(name):
        try:
            path = _check_name(name)
        except FileNotFoundError:
            return Response(t("unknown file"), status=404)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        saved = request.args.get("saved")
        error = request.args.get("error", "")
        note = (f'<p class="ok">{t("Saved.")}</p>' if saved
                else f'<p class="err">{t("Error: {error}", error=html.escape(error))}</p>'
                if error else "")
        body = (f"<h2>{name}</h2>{note}"
                f'<p><a href="/config/{name}/download">{t("download")}</a></p>'
                f'<form method="post" action="/config/{name}">'
                f'<textarea name="content" spellcheck="false">{html.escape(content)}</textarea>'
                f'<p><button type="submit">{t("Save")}</button></p></form>')
        return page(body)

    @app.get("/config/<name>/download")
    def config_download(name):
        try:
            path = _check_name(name)
        except FileNotFoundError:
            return Response(t("unknown file"), status=404)
        if not path.exists():
            return Response(t("file missing"), status=404)
        return Response(
            path.read_bytes(),
            mimetype="text/yaml",
            headers={"Content-Disposition": f"attachment; filename={name}"},
        )

    @app.post("/config/<name>")
    def config_save(name):
        try:
            path = _check_name(name)
        except FileNotFoundError:
            return Response(t("unknown file"), status=404)
        content = request.form.get("content", "")
        try:
            parsed = yaml.safe_load(content)
            if parsed is not None and not isinstance(parsed, dict):
                raise ValueError(t("content must be a YAML mapping"))
        except Exception as exc:
            return redirect(url_for("config_edit", name=name, error=str(exc)))
        path.write_text(content, encoding="utf-8")
        log.info("File %s saved from the web UI", name)
        if name == "albums.yaml":
            try:
                on_albums_saved()
            except Exception as exc:
                return redirect(url_for("config_edit", name=name, error=t("reload: {error}", error=exc)))
        return redirect(url_for("config_edit", name=name, saved=1))

    def _warning(text: str) -> str:
        """search_library() warnings are English sentences joined together:
        translate each known part."""
        for part in ("artist not in Library › Artists: path goes through the album list",
                     " — duplicate title, the first one will play"):
            text = text.replace(part, texts.get(part, part))
        return text

    def _card_options() -> str:
        """Known cards, TODO ones first (the most likely targets)."""
        if cards_fn is None:
            return ""
        cards = sorted(cards_fn().values(), key=lambda e: (not e.is_todo, e.uid))
        return "".join(
            f'<option value="{html.escape(e.uid)}">{html.escape(e.uid)} — '
            f'{"TODO" if e.is_todo else html.escape(e.display_name())}</option>'
            for e in cards
        )

    @app.get("/search")
    def search():
        q = request.args.get("q", "").strip()
        assigned = request.args.get("assigned", "")
        error = request.args.get("error", "")
        note = (f'<p class="ok">{t("Card {uid} assigned.", uid=html.escape(assigned))}</p>'
                if assigned
                else f'<p class="err">{t("Error: {error}", error=html.escape(error))}</p>'
                if error else "")
        body = (f'<h2>{t("Search Roon")}</h2>{note}'
                f'<form method="get" action="/search">'
                f'<input type="search" name="q" value="{html.escape(q)}" '
                f'placeholder="{t("title and/or artist")}" autofocus> '
                f'<button type="submit">{t("Search")}</button></form>')
        if not q or search_fn is None:
            return page(body)
        results = search_fn(q)
        if results is None:
            return page(body + f'<p class="err">{t("Roon not connected.")}</p>')
        if not results:
            return page(body + f"<p>{t('No album found.')}</p>")
        options = _card_options()
        rows = []
        for r in results:
            path_json = json.dumps(r["path"], ensure_ascii=False)
            fragment = f"path: {path_json}"
            if r["artist"]:
                fragment += f'\nartist: {json.dumps(r["artist"], ensure_ascii=False)}'
            warn = (f'<div class="warn">⚠ {html.escape(_warning(r["warning"]))}</div>'
                    if r["warning"] else "")
            assign = ""
            if options and assign_fn is not None:
                assign = (f'<form method="post" action="/search/assign">'
                          f'<input type="hidden" name="q" value="{html.escape(q)}">'
                          f'<input type="hidden" name="path" value="{html.escape(path_json)}">'
                          f'<input type="hidden" name="artist" value="{html.escape(r["artist"])}">'
                          f'<select name="uid">{options}</select>'
                          f'<button type="submit">{t("Assign to this card")}</button></form>')
            rows.append(f'<tr><td><b>{html.escape(r["title"])}</b><br>'
                        f'{html.escape(r["artist"])}{warn}'
                        f'<pre>{html.escape(fragment)}</pre>{assign}</td></tr>')
        link = "<a href='/config/albums.yaml'>albums.yaml</a>"
        count = ("<p>" + t("{n} album(s) — copy under the card's UID in {link}, "
                           "or assign directly to a card.", n=len(results), link=link)
                 + "</p>")
        return page(body + count + f"<table>{''.join(rows)}</table>")

    @app.post("/search/assign")
    def search_assign():
        q = request.form.get("q", "")
        uid = request.form.get("uid", "").strip().upper()
        try:
            path = json.loads(request.form.get("path", ""))
            if (not isinstance(path, list) or len(path) < 2
                    or not all(isinstance(p, str) and p for p in path)):
                raise ValueError(t("invalid path"))
            if cards_fn is None or assign_fn is None or uid not in cards_fn():
                raise ValueError(t("unknown card: {uid}", uid=uid))
            assign_fn(uid, path, request.form.get("artist", ""))
        except Exception as exc:
            return redirect(url_for("search", q=q, error=str(exc)))
        return redirect(url_for("search", q=q, assigned=uid))

    return app


def start_in_thread(app: Flask, host: str, port: int) -> None:
    import threading

    def _serve():
        # built-in WSGI server: enough for single-user LAN use
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

    thread = threading.Thread(target=_serve, daemon=True, name="web")
    thread.start()
    log.info("Web UI on http://%s:%d", host, port)
