# Journal du projet M-Card

## 2026-10-18 17:56 — Page de présentation (marketing/)

Pitch : « re-matérialiser la musique dématérialisée avec M-Card et Roon ».
`marketing/index.html` : **un seul fichier autonome** (3,55 Mo, hors ligne,
aucune ressource externe), textes en anglais, charte reprise des cartes
d'Eric (brun espresso du logo « M. », ambre des icônes de façade, bleu LCD).

- **3D temps réel** (three.js, bundlé) : vraies pièces du boîtier exportées
  en position assemblée (`build/parts.scad` inclut `mcard.scad` avec
  `part = "none"` → aucune cote dupliquée), + pièces de rendu : module LCD,
  boutons inox, vis CHC M3 (façade, dosseret, fond) et embase USB-C (corps,
  réceptacle, vis M2) qui comblent lamages et découpe. Une M-Card glisse
  dans la fente toutes les 7 s (ou au choix via « Try a card »), le LCD
  passe par « .. loading » puis affiche l'album. Orbite à la souris,
  balancement auto, rendu suspendu hors écran, repli photo sans WebGL.
- **LCD émulé** (canvas) : police 5×7 HD44780, mise en page et défilement
  identiques à `display.py`. Section « A screen with soul » : simple
  exemple (boutons interactifs retirés, jugés « too much »).
- **Console** : captures HTML réelles (mode `--fake`, `albums.yaml` construit
  via `AlbumStore.assign` pour le format canonique), rendues figées en
  Shadow DOM, carrousel horizontal État / Albums / Recherche à 3 points.
  Itérations : onglets inventés (refusés : n'existent pas), puis iframe
  cliquable (listener parent non fiable selon navigateur), puis carrousel.
- **Cartes** : découpées de `card-covers/albums*.png` (détection auto de la
  grille), logo « M. » extrait en PNG transparent. `card-covers/` ignoré.
- **Bug Safari** : le bandeau animé en CSS (translateX + mask-image) perdait
  des bandes puis se figeait à côté du contexte WebGL ; ni le retrait du
  lazy-loading ni celui du masque ne suffisaient → bandeau dessiné en
  canvas 2D (ombres pré-rendues par carte), validé par Eric sous Safari.
- Usage vinyle explicité : une M-Card glissée dans la pochette fait du
  disque lui-même le déclencheur (hero, étape « Drop », encadré dédié).
- Vérifié par captures Chrome headless (puppeteer, hors dépôt), 1440 et
  390 px, sans erreur JS ni débordement horizontal.

## 2026-10-18 17:09 — Format canonique d'albums.yaml ; téléchargement brut pour sauvegardes

- **Format mixte constaté** (fragment collé `path: [...]` vs liste en bloc
  et clés triées écrites par `yaml.safe_dump`). `AlbumStore._save_locked`
  écrit désormais à la main le même format que les fragments de `/search` :
  UID entre guillemets (un UID tout en chiffres serait relu comme entier,
  zéros de tête perdus), `path` sur une ligne puis `artist`, chaînes
  sérialisées en JSON (JSON ⊂ YAML : guillemets, `\`, accents sûrs).
- L'éditeur `/config/albums.yaml` écrivait le texte tel quel : il appelle
  maintenant `reload_and_normalize` (recharge + réécriture canonique).
  Choix assumé : les commentaires utilisateur sont perdus (déjà le cas pour
  add_todo/assign), l'en-tête d'aide est régénéré.
- **Sauvegardes** : `GET /config/<nom>/download` renvoie le fichier brut
  (mêmes restrictions `EDITABLE_FILES`), lien « télécharger » sur la page
  d'édition. Préféré à un scp (pas de clé SSH nécessaire) et à un parsing
  du HTML. Pas de tâche planifiée (choix d'Eric) : commande curl documentée
  dans SETUP/README ; `backups/` ajouté au `.gitignore`.

5 tests ajoutés (73 au total).

## 2026-10-18 15:05 — Page de recherche d'albums Roon (/search)

Demande d'Eric : identifier les albums par un ID Roon dans `albums.yaml`.
**Constat** : l'API d'extension Roon n'expose aucun ID stable — les
`item_key` de navigation ne valent que pour la session de browse. Seul
identifiant durable : le chemin de navigation, matché titre exact par titre
exact par `play_media`. Décision (Eric) : la page produit **toujours** un
`path:`, jamais un `album:` approximatif.

- `roon_client` : `search_library()` (pure, testée) — tous les mots de la
  requête présents dans « titre artiste » normalisés, tri par titre, 50 max ;
  `album_path()` → `["Library", "Artists", artiste, titre]` si l'artiste
  (subtitle de la hiérarchie `albums`) existe dans la hiérarchie `artists`,
  sinon repli `["Library", "Albums", titre]` avec avertissement (compilations,
  multi-artistes ; homonymes signalés). Le cache 5 min liste désormais
  (titre, artiste) + l'ensemble des artistes (`_list_items` générique).
  Nouveau `_browse_lock` : sérialise les parcours (lecture de carte vs
  recherche web en parallèle).
- `AlbumStore.assign(uid, path, artist)` ; page `/search` (fragment YAML à
  copier + bouton « Associer à cette carte », cartes TODO en premier) et
  `POST /search/assign` (UID doit exister, chemin JSON validé).
- `FakeRoonClient.search_albums` sur une mini-bibliothèque pour `--fake`.
- Limites connues : noms « Library »/« Artists » = Roon en anglais ;
  l'association réécrit `albums.yaml` (commentaires perdus, comme add_todo).
  Non encore validé contre le vrai Roon.

12 tests ajoutés (68 au total), vérification bout en bout en mode `--fake`.

## 2026-10-18 14:33 — Correspondance des titres d'albums en mots entiers

Deux faux « ambigu » constatés sur le Pi :

1. « Electronica Vol 1 The Time Machine » → candidats `['I', 'V']` :
   l'inclusion se faisait **par sous-chaîne**, donc tout album d'une lettre
   « correspondait » à n'importe quel titre contenant cette lettre.
   → `_norm` découpe désormais en mots (ponctuation supprimée, apostrophes
   collées : « l'emprise » ~ « lemprise »), ignore les mots `vol`/`volume`,
   et l'inclusion se teste **en mots entiers contigus** (`_contains_words`).
   `titles_match` (comparaison carte re-posée) en bénéficie aussi.
2. « Electronica The Heart of Noise » → `['Electronica: The Heart of Noise,
   Vol. 2', 'Noise']` : « Noise » est bien un mot entier du titre.
   → départage par **plus longue partie commune** (en mots) ; ambigu
   seulement en cas d'égalité (« Live » vs « Live at… »/« Live in… » reste
   ambigu, comme voulu).

3 tests ajoutés (56 au total, tous verts).

## 2026-07-31 — Réorganisation des répertoires (par Eric)

`hardware/enclosure/` remonte en `enclosure/` ; `idea/` (croquis et photos
du matériel) et `proto2/` (photos du prototype) sont regroupés dans
`versions/`. Renommages faits avec suivi git ; toutes les références des
docs (README, CLAUDE.md, ASSEMBLY, BOM) mises à jour — les chemins cités
dans les entrées passées de ce journal restent tels quels (historique).
Dans la foulée, `PROJECT.md` (cahier des charges d'origine, entièrement
réalisé) rejoint ses croquis dans `versions/idea/`.

## 2026-07-31 — Reposer la même carte = ne rien faire ; veille du rétro-éclairage

Deux raffinements d'usage demandés par Eric après quelques jours avec le
prototype 2 :

1. **Carte identique re-posée** : si l'album de la carte correspond à celui
   en cours (comparaison tolérante `titles_match` : casse/accents/inclusion),
   on ne relance rien — en lecture : aucune action ; en pause : reprise par
   `playpause` (plutôt que repartir piste 1). On peut ainsi prendre le
   vinyle en main et le reposer sans perturber l'écoute.
2. **Veille du rétro-éclairage** (`lcd.backlight_timeout_s`, défaut 120 s,
   0 = jamais) : extinction après N s sans interaction physique (carte
   posée/retirée, bouton) ; toute interaction rallume et exécute son action.
   Piloté par `backlight_enabled` de RPLCD (PCF8574), surveillé par le
   thread ticker du Display ; les changements de piste ne rallument pas.

53 tests (7 nouveaux : non-relance/reprise/changement, réveil par bouton,
veille et réveil du Display, timeout 0, tolérance de titres).

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
