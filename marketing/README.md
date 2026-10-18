# Page de présentation M-Card

[`index.html`](index.html) est **autonome** : un seul fichier (≈ 3 Mo) qui
s'ouvre directement dans un navigateur, sans serveur ni connexion Internet.
Tout y est embarqué : three.js, polices, cartes, photos, pièces 3D et
captures de l'interface web.

## Contenu

- **Rendu 3D temps réel** de l'appareil : les vraies pièces du boîtier
  (`enclosure/mcard.scad`, exportées en position assemblée), avec l'écran LCD
  émulé et une carte M-Card qui glisse dans la fente.
- **Émulation du LCD 20×4** : police HD44780, mise en page et défilement
  identiques à `software/mcard/display.py`, avec des boutons qui fonctionnent.
- **Console web** : captures HTML réelles de l'interface (mode `--fake`).
- Cartes tirées de `card-covers/`, photos du prototype tirées de `versions/proto2/`.

## Régénérer

```bash
cd marketing/build
npm install
./export-stl.sh      # seulement si le boîtier a changé (OpenSCAD requis)
npm run build        # → ../index.html
```

| Dossier / fichier | Rôle |
|---|---|
| `src/` | gabarit HTML, CSS, JS (scène 3D, émulateur LCD, logique de page) |
| `parts.scad` + `export-stl.sh` | pièces assemblées → `stl/` (STL binaires) |
| `cards/`, `img/` | cartes découpées, photos allégées, logo extrait des cartes |
| `capture/` | pages de l'interface web capturées en mode `--fake` |
| `build.mjs` | bundle esbuild + inlining de toutes les ressources |
