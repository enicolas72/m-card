"""Micro-serveur web local (Flask) — uniquement sur le réseau local.

- /            : état de l'appareil (morceau en cours, Roon, dernière carte)
- /logs        : consultation du log (lecture seule)
- /config      : édition des fichiers de configuration (albums.yaml, mcard.yaml)
- /search      : recherche d'albums dans Roon → fragment `path:` pour albums.yaml,
                 ou association directe à une carte
- /api/status  : état JSON

Aucune authentification : l'appareil n'est accessible que sur le LAN
(aucune connexion Internet, conformément au cahier des charges).
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
<html lang="fr"><head><meta charset="utf-8">
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
<nav><a href="/">État</a> <a href="/logs">Logs</a> <a href="/config">Configuration</a> <a href="/search">Recherche</a></nav>
{body}
</body></html>"""


def _tail(path: Path, lines: int) -> str:
    if not path.exists():
        return "(fichier de log absent)"
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
        roon = ('<span class="ok">connecté</span>' if s.get("roon_connected")
                else '<span class="err">déconnecté</span>')
        rows = [
            ("Roon", f'{roon} {html.escape(s.get("roon_message", ""))}'),
            ("État", html.escape(s.get("state", ""))),
            ("Album", html.escape(s.get("album", ""))),
            ("Morceau", html.escape(s.get("track", ""))),
            ("Artiste", html.escape(s.get("artist", ""))),
            ("Carte posée", html.escape(s.get("card_uid", "") or "aucune")),
            ("Album de la carte", html.escape(s.get("card_album", ""))),
        ]
        table = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
        return PAGE.format(body=f"<table>{table}</table>")

    @app.get("/api/status")
    def api_status():
        return status_fn()

    @app.get("/logs")
    def logs():
        n = max(10, min(int(request.args.get("n", "200")), 5000))
        body = (f"<p>{n} dernières lignes — <a href='/logs?n=1000'>1000</a>, "
                f"<a href='/logs/download'>télécharger tout</a></p>"
                f"<pre>{html.escape(_tail(log_file, n))}</pre>")
        return PAGE.format(body=body)

    @app.get("/logs/download")
    def logs_download():
        if not log_file.exists():
            return Response("log absent", status=404)
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
        if name not in EDITABLE_FILES:  # protège aussi contre les traversées de chemin
            raise FileNotFoundError(name)
        return config_dir / name

    @app.get("/config/<name>")
    def config_edit(name):
        try:
            path = _check_name(name)
        except FileNotFoundError:
            return Response("fichier inconnu", status=404)
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        saved = request.args.get("saved")
        error = request.args.get("error", "")
        note = ('<p class="ok">Enregistré.</p>' if saved
                else f'<p class="err">Erreur : {html.escape(error)}</p>' if error else "")
        body = (f"<h2>{name}</h2>{note}"
                f'<form method="post" action="/config/{name}">'
                f'<textarea name="content" spellcheck="false">{html.escape(content)}</textarea>'
                f'<p><button type="submit">Enregistrer</button></p></form>')
        return PAGE.format(body=body)

    @app.post("/config/<name>")
    def config_save(name):
        try:
            path = _check_name(name)
        except FileNotFoundError:
            return Response("fichier inconnu", status=404)
        content = request.form.get("content", "")
        try:
            parsed = yaml.safe_load(content)
            if parsed is not None and not isinstance(parsed, dict):
                raise ValueError("le contenu doit être un mapping YAML")
        except Exception as exc:
            return redirect(url_for("config_edit", name=name, error=str(exc)))
        path.write_text(content, encoding="utf-8")
        log.info("Fichier %s enregistré via l'interface web", name)
        if name == "albums.yaml":
            try:
                on_albums_saved()
            except Exception as exc:
                return redirect(url_for("config_edit", name=name, error=f"rechargement: {exc}"))
        return redirect(url_for("config_edit", name=name, saved=1))

    def _card_options() -> str:
        """Cartes connues, celles en TODO d'abord (les plus probables)."""
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
        note = (f'<p class="ok">Carte {html.escape(assigned)} associée.</p>' if assigned
                else f'<p class="err">Erreur : {html.escape(error)}</p>' if error else "")
        body = (f'<h2>Recherche dans Roon</h2>{note}'
                f'<form method="get" action="/search">'
                f'<input type="search" name="q" value="{html.escape(q)}" '
                f'placeholder="titre et/ou artiste" autofocus> '
                f'<button type="submit">Chercher</button></form>')
        if not q or search_fn is None:
            return PAGE.format(body=body)
        results = search_fn(q)
        if results is None:
            return PAGE.format(body=body + '<p class="err">Roon non connecté.</p>')
        if not results:
            return PAGE.format(body=body + "<p>Aucun album trouvé.</p>")
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
                          f'<button type="submit">Associer à cette carte</button></form>')
            rows.append(f'<tr><td><b>{html.escape(r["title"])}</b><br>'
                        f'{html.escape(r["artist"])}{warn}'
                        f'<pre>{html.escape(fragment)}</pre>{assign}</td></tr>')
        count = (f"<p>{len(results)} album(s) — à copier sous l'UID de la carte "
                 f"dans <a href='/config/albums.yaml'>albums.yaml</a>, ou à associer "
                 f"directement à une carte.</p>")
        return PAGE.format(body=body + count + f"<table>{''.join(rows)}</table>")

    @app.post("/search/assign")
    def search_assign():
        q = request.form.get("q", "")
        uid = request.form.get("uid", "").strip().upper()
        try:
            path = json.loads(request.form.get("path", ""))
            if (not isinstance(path, list) or len(path) < 2
                    or not all(isinstance(p, str) and p for p in path)):
                raise ValueError("chemin invalide")
            if cards_fn is None or assign_fn is None or uid not in cards_fn():
                raise ValueError(f"carte inconnue : {uid}")
            assign_fn(uid, path, request.form.get("artist", ""))
        except Exception as exc:
            return redirect(url_for("search", q=q, error=str(exc)))
        return redirect(url_for("search", q=q, assigned=uid))

    return app


def start_in_thread(app: Flask, host: str, port: int) -> None:
    import threading

    def _serve():
        # serveur WSGI intégré : suffisant pour un usage LAN mono-utilisateur
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

    thread = threading.Thread(target=_serve, daemon=True, name="web")
    thread.start()
    log.info("Interface web sur http://%s:%d", host, port)
