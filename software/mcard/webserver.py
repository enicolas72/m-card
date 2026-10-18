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

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M-Card</title>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; margin: 2rem auto; max-width: 46rem;
        padding: 0 1rem; background: #101418; color: #e6e6e6; }}
 h1 {{ font-size: 1.4rem; }} h1 a {{ color: inherit; text-decoration: none; }}
 nav a {{ margin-right: 1rem; color: #7ab8ff; }}
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
<nav><a href="/">Status</a> <a href="/logs">Logs</a> <a href="/config">Configuration</a> <a href="/search">Search</a></nav>
{body}
</body></html>"""


def _tail(path: Path, lines: int) -> str:
    if not path.exists():
        return "(log file missing)"
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
) -> Flask:
    app = Flask("mcard")
    config_dir = Path(config_dir)
    log_file = Path(log_file)

    @app.get("/")
    def index():
        s = status_fn()
        roon = ('<span class="ok">connected</span>' if s.get("roon_connected")
                else '<span class="err">disconnected</span>')
        rows = [
            ("Roon", f'{roon} {html.escape(s.get("roon_message", ""))}'),
            ("State", html.escape(s.get("state", ""))),
            ("Album", html.escape(s.get("album", ""))),
            ("Track", html.escape(s.get("track", ""))),
            ("Artist", html.escape(s.get("artist", ""))),
            ("Card in slot", html.escape(s.get("card_uid", "") or "none")),
            ("Card album", html.escape(s.get("card_album", ""))),
        ]
        table = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
        return PAGE.format(body=f"<table>{table}</table>")

    @app.get("/api/status")
    def api_status():
        return status_fn()

    @app.get("/logs")
    def logs():
        n = max(10, min(int(request.args.get("n", "200")), 5000))
        body = (f"<p>last {n} lines — <a href='/logs?n=1000'>1000</a>, "
                f"<a href='/logs/download'>download all</a></p>"
                f"<pre>{html.escape(_tail(log_file, n))}</pre>")
        return PAGE.format(body=body)

    @app.get("/logs/download")
    def logs_download():
        if not log_file.exists():
            return Response("log missing", status=404)
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
        return PAGE.format(body=f"<ul>{items}</ul>")

    def _check_name(name: str) -> Path:
        if name not in EDITABLE_FILES:  # also guards against path traversal
            raise FileNotFoundError(name)
        return config_dir / name

    @app.get("/config/<name>")
    def config_edit(name):
        try:
            path = _check_name(name)
        except FileNotFoundError:
            return Response("unknown file", status=404)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        saved = request.args.get("saved")
        error = request.args.get("error", "")
        note = ('<p class="ok">Saved.</p>' if saved
                else f'<p class="err">Error: {html.escape(error)}</p>' if error else "")
        body = (f"<h2>{name}</h2>{note}"
                f'<p><a href="/config/{name}/download">download</a></p>'
                f'<form method="post" action="/config/{name}">'
                f'<textarea name="content" spellcheck="false">{html.escape(content)}</textarea>'
                f'<p><button type="submit">Save</button></p></form>')
        return PAGE.format(body=body)

    @app.get("/config/<name>/download")
    def config_download(name):
        try:
            path = _check_name(name)
        except FileNotFoundError:
            return Response("unknown file", status=404)
        if not path.exists():
            return Response("file missing", status=404)
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
            return Response("unknown file", status=404)
        content = request.form.get("content", "")
        try:
            parsed = yaml.safe_load(content)
            if parsed is not None and not isinstance(parsed, dict):
                raise ValueError("content must be a YAML mapping")
        except Exception as exc:
            return redirect(url_for("config_edit", name=name, error=str(exc)))
        path.write_text(content, encoding="utf-8")
        log.info("File %s saved from the web UI", name)
        if name == "albums.yaml":
            try:
                on_albums_saved()
            except Exception as exc:
                return redirect(url_for("config_edit", name=name, error=f"reload: {exc}"))
        return redirect(url_for("config_edit", name=name, saved=1))

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
        note = (f'<p class="ok">Card {html.escape(assigned)} assigned.</p>' if assigned
                else f'<p class="err">Error: {html.escape(error)}</p>' if error else "")
        body = (f'<h2>Search Roon</h2>{note}'
                f'<form method="get" action="/search">'
                f'<input type="search" name="q" value="{html.escape(q)}" '
                f'placeholder="title and/or artist" autofocus> '
                f'<button type="submit">Search</button></form>')
        if not q or search_fn is None:
            return PAGE.format(body=body)
        results = search_fn(q)
        if results is None:
            return PAGE.format(body=body + '<p class="err">Roon not connected.</p>')
        if not results:
            return PAGE.format(body=body + "<p>No album found.</p>")
        options = _card_options()
        rows = []
        for r in results:
            path_json = json.dumps(r["path"], ensure_ascii=False)
            fragment = f"path: {path_json}"
            if r["artist"]:
                fragment += f'\nartist: {json.dumps(r["artist"], ensure_ascii=False)}'
            warn = (f'<div class="warn">⚠ {html.escape(r["warning"])}</div>'
                    if r["warning"] else "")
            assign = ""
            if options and assign_fn is not None:
                assign = (f'<form method="post" action="/search/assign">'
                          f'<input type="hidden" name="q" value="{html.escape(q)}">'
                          f'<input type="hidden" name="path" value="{html.escape(path_json)}">'
                          f'<input type="hidden" name="artist" value="{html.escape(r["artist"])}">'
                          f'<select name="uid">{options}</select>'
                          f'<button type="submit">Assign to this card</button></form>')
            rows.append(f'<tr><td><b>{html.escape(r["title"])}</b><br>'
                        f'{html.escape(r["artist"])}{warn}'
                        f'<pre>{html.escape(fragment)}</pre>{assign}</td></tr>')
        count = (f"<p>{len(results)} album(s) — copy under the card's UID "
                 f"in <a href='/config/albums.yaml'>albums.yaml</a>, or assign "
                 f"directly to a card.</p>")
        return PAGE.format(body=body + count + f"<table>{''.join(rows)}</table>")

    @app.post("/search/assign")
    def search_assign():
        q = request.form.get("q", "")
        uid = request.form.get("uid", "").strip().upper()
        try:
            path = json.loads(request.form.get("path", ""))
            if (not isinstance(path, list) or len(path) < 2
                    or not all(isinstance(p, str) and p for p in path)):
                raise ValueError("invalid path")
            if cards_fn is None or assign_fn is None or uid not in cards_fn():
                raise ValueError(f"unknown card: {uid}")
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
