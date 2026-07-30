# Journal du projet M-Card

## 2026-07-30 (soir) — Prototype 2 assemblé et fonctionnel

Photos ajoutées dans `hardware/proto2/` (et en tête du README) : boîtier
V0.3 imprimé en noir, façade inclinée avec LCD (album/morceau affichés),
boutons métal, icônes couleur visibles à travers les ajours, vinyle posé
dans la fente et adossé au dosseret trapézoïdal — lecture Roon en cours.
Le concept du croquis d'origine est matérialisé.

## 2026-07-30 — Icônes couleur ajourées ; dosseret : lecteur logé, câble débouchant

**Icônes en couleur** (idée d'Eric) : les glyphes ⏮ ⏯ ⏭ de la façade
deviennent des découpes traversantes (peau avant 2 mm) ; un lamage
16×56×2 dans l'épaisseur au dos reçoit une plaquette imprimée dans une
couleur contrastée (nouvelle pièce `icon_plate`, 1,8 mm, jeu 0,2/côté,
collée) — la couleur apparaît en léger retrait. Technique bicolore sans
multi-matériaux ; possible car les glyphes n'ont aucun îlot. Icônes
agrandies à 5 mm.

**Deux défauts bloquants du dosseret détectés par Eric au slicing** :
1. Passage câble « non traversant » : recouvrement de 0,01 mm seulement
   entre la gaine et la cavité — surface coïncidente refermée en membrane
   par le slicer. Débouché porté à 2 mm francs.
2. Lecteur qui ne loge pas : avec le trapèze abaissé (h 84, sommet 90),
   le flanc réel passait à l'intérieur du coin du lecteur (48,9 mm de
   demi-largeur à z=70 pour 58,5 requis) — la carte sortait du volume
   extérieur. Sommet élargi 90 → 126 (minimum géométrique ~125), cavité
   dotée d'un rectangle explicite garanti 96×63, vis de plaque arrière
   recalculées ((±93,10)/(±66,58)), mur avant ramené à 3 mm exactement.

**Méthode consolidée** : vérifications par intersections OpenSCAD
automatiques (carte réelle ∩ dosseret = vide ; pilier traversant le
passage câble ∩ socle/dosseret = vide) — à rejouer après toute retouche
du dosseret. La branche `else` de sélection de pièce ne rend plus rien
pour une valeur inconnue, ce qui permet ces fichiers de contrôle.

## 2026-07-29 — Boîtier V0.3 « agitateur magnétique » + retrait de carte non bloquant

**Logiciel** : `behavior.on_card_removed` passe à `none` par défaut (demande
d'usage d'Eric) — retirer le CD/vinyle laisse l'album continuer, les 3 boutons
restent actifs ; ⏯ sert de pause. `pause`/`stop` restent configurables.
46 tests.

**Boîtier — refonte complète en deux itérations** à partir des retours de
montage du premier prototype (inserts impossibles à positionner, vis LCD
inaccessibles, socle trop haut, passage USB sous-dimensionné, fente trop
courte pour un vinyle) :

- **V0.2** : façade rapportée (LCD vissé à plat sur l'établi puis façade
  vissée sur le corps), poches à inserts filetés à chaque point M3, fente
  débouchante pleine largeur, passages câble 18×10,5 (prise USB-A surmoulée),
  hauteur 95 → 68 (boutons en colonne à droite de l'écran, icônes gravées).
- **V0.3** : silhouette « agitateur magnétique » sur suggestion d'Eric —
  socle 48 mm (210×150, le Pi loge à plat derrière la fente), console avant
  inclinée ~34° portant la façade ; l'écran se lit de dessus.
- **Dosseret** itéré avec Eric : trapèze pleine largeur épaulé sur le socle,
  coins hauts arrondis (r14), h 84 ; lecteur ACR122U **en paysage** (cavité
  93×62, décalé de 12 mm pour recentrer l'antenne, câble à droite vers un
  passage déck décalé) ; intérieur globalement creux (passage câble libre,
  butées de positionnement de la carte) ; plaque arrière pleine forme,
  affleurante, sur 4 inserts.
- **Quincaillerie réelle vérifiée** (fiches fournisseur) : poches d'inserts
  Ø4,4×7 (Hangtife M3×5×4, reco 4,31-4,35), vis 100 % CHC → lamages
  cylindriques Ø6,2×3,2 au lieu de fraisages, plaques concernées épaissies à
  4 mm, dégagement Ø16 au dos des boutons. Une seule longueur de vis (M3×8)
  pour tout le boîtier.

**Bugs attrapés en route** (leçon : transformations OpenSCAD imbriquées =
zone à risque ; contrôle systématique par bornes de STL + rendus) : vis du
dosseret transperçant le flanc (le flanc réel est la tangente au coin
arrondi, pas le côté du trapèze théorique — recalcul analytique), poches
d'inserts percées vers l'extérieur, orientation d'impression du dosseret
inversée (cavité côté plateau), plaque arrière extrudée 21 mm hors position
(d'où « trous manquants »).

## 2026-07-29 — Dosseret calé sur les cotes réelles de l'ACR122U

Carte nue mesurée par Eric : 60 × 91 mm (câble sortant par le petit côté,
antenne dans la grande zone plane du bas, électronique/module blanc en haut).
Logement redimensionné 95×65 (paysage) → 62×93 (portrait, jeu de 1 mm par
côté), bas du logement abaissé de 12 à 8 mm au-dessus de la face supérieure :
l'antenne se retrouve centrée face à la carte RFID posée dans la fente, le
câble redescend par la cavité arrière vers le passage du socle.
`backrest.stl` et `backrest_cover.stl` régénérés, aperçus mis à jour.

## 2026-07-28 — Icônes des boutons moulées dans la façade

Ajout des glyphes ⏮ ⏯ ⏭ en relief (0,6 mm, hauteur 6 mm) au-dessus des trois
perçages de boutons, entre ceux-ci et la fenêtre LCD. Dessinés en polygones 2D
extrudés dans `mcard.scad` (paramètres `btn_icon_relief/s/z`) ; la façade étant
verticale à l'impression, le relief sort sans support. `stl/shell.stl`
régénéré, aperçus (`assembly_front.png`, nouveau `facade_icons.png`) mis à
jour. Alternative gravée en creux possible en 2 lignes si le rendu en relief
ne convient pas.

## 2026-07-26 (soir) — Résolution tolérante des noms d'albums

**Problème** (constaté avec les premières vraies cartes) : `play_media` de
pyroon exige le titre exact de la bibliothèque, casse et accents compris —
« The Girl in **The** Other Room » ≠ « The Girl in **the** Other Room » →
échec. De plus sa valeur de retour est inexploitable (None en succès comme en
échec selon les versions), ce qui laissait l'appareil bloqué sur
« Lancement... » sans message d'erreur. Première tentative de correctif via le
paramètre `report_error` de play_media : abandonnée, paramètre absent de
certaines versions de pyroon (blocage constaté sur le Pi).

**Solution retenue** : ne plus dépendre de play_media pour la recherche — le
titre canonique est résolu AVANT lecture, contre la liste réelle des albums
(hiérarchie `albums` du browse Roon, paginée, cache 5 min rafraîchi
automatiquement sur échec de résolution). Correspondance : égalité normalisée
(casse/accents/apostrophes/espaces) puis inclusion non ambiguë ; en cas
d'ambiguïté, pas de lecture au hasard, jusqu'à 5 candidats listés dans le log.
Les entrées `path:` explicites restent en correspondance stricte. Le log
conseille le titre canonique à reporter dans albums.yaml. 45 tests (+10 :
normalisation, correspondance, pagination du browse, cache).

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
