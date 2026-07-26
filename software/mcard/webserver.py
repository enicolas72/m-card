"""Micro-serveur web local (Flask) — uniquement sur le réseau local.

- /            : état de l'appareil (morceau en cours, Roon, dernière carte)
- /logs        : consultation du log (lecture seule)
- /config      : édition des fichiers de configuration (albums.yaml, mcard.yaml)
- /api/status  : état JSON

Aucune authentification : l'appareil n'est accessible que sur le LAN
(aucune connexion Internet, conformément au cahier des charges).
"""

from __future__ import annotations

import html
import logging
from collections import deque
from pathlib import Path
from typing import Callable

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
 .err {{ color: #ff8080; }} .ok {{ color: #7dd87d; }}
</style></head><body>
<h1><a href="/">M-Card</a></h1>
<nav><a href="/">État</a> <a href="/logs">Logs</a> <a href="/config">Configuration</a></nav>
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

    return app


def start_in_thread(app: Flask, host: str, port: int) -> None:
    import threading

    def _serve():
        # serveur WSGI intégré : suffisant pour un usage LAN mono-utilisateur
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

    thread = threading.Thread(target=_serve, daemon=True, name="web")
    thread.start()
    log.info("Interface web sur http://%s:%d", host, port)
