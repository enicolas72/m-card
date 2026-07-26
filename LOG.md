# Journal du projet M-Card

## 2026-07-26 — Premier jet complet + prototype breadboard validé

**Réalisé** (session initiale puis débogage en direct sur le matériel) :

- **Logiciel** (`software/mcard/`) : package Python complet — queue d'événements
  unique + contrôleur central, client Roon (découverte SOOD, appairage par jeton,
  reconnexion supervisée), lecteur NFC nfcpy/ACR122U, LCD 2004 I2C (RPLCD,
  défilement, translittération des accents pour HD44780), boutons gpiozero,
  serveur web Flask (état / logs RO / configs RW avec validation YAML et
  rechargement à chaud), logging rotatif, mode `--fake` complet pour développer
  sans matériel. 35 tests pytest (matériel simulé), tous verts.
- **Électronique** : docs/WIRING.md + schéma SVG + BOM (~10–20 €). Choix clés :
  ACR122U conservé en USB (zéro soudure), LCD via backpack I2C (4 fils),
  alimentation par embase USB-C panneau → micro-USB.
- **Boîtier 3D** (`hardware/enclosure/`) : OpenSCAD paramétrique, 4 pièces sans
  support (corps imprimé à l'envers, dosseret porte-lecteur, plaque arrière,
  fond avec plots Pi), STL exportés et vérifiés visuellement.
- **Docs** : README, SETUP (SD → Roon → dépannage), ASSEMBLY, CLAUDE.md.

**Corrections issues du test sur le vrai matériel** :

- `install.sh` : ajout `swig` + `liblgpio-dev` (compilation du paquet pip lgpio).
- systemd : `WorkingDirectory=/var/lib/mcard` (lgpio écrit son fichier de
  notification dans le cwd ; sous systemd, cwd=/ → GPIO indisponibles).
- `requirements.txt` : ajout `smbus2` (backend I2C de RPLCD, oublié).
- **nfc_reader** : période de grâce (1 s, configurable) sur le retrait — avec
  l'ACR122U, le test de présence nfcpy échoue sur les Mifare Ultralight et
  connect() « clignote » ~5 Hz ; sans lissage : rafale de détections/retraits
  et de commandes pause. 5 tests reproduisent le scénario.
- BOM : suppression du câble USB superflu (l'ACR122U a un câble captif).

**Décision d'ergonomie** (retour d'usage d'Eric) : passage de 4 à 3 boutons —
prev / play-pause (bascule native Roon `playpause`) / next, GPIO 5/6/13.
Anciens noms `play`/`pause` toujours acceptés par le contrôleur.

**État** : prototype breadboard 100 % fonctionnel (Roon zone « Devialet »,
cartes → albums, boutons, LCD après refonte des soudures du backpack par Eric).
Reste : impression du boîtier (vérifier cotes carte ACR122U nue et embase
USB-C), assemblage final, remplissage d'albums.yaml.
