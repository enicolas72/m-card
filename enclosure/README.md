# Boîtier M-Card — impression 3D (V0.3)

Modèle paramétrique : [`mcard.scad`](mcard.scad) (toutes les cotes en tête de
fichier). STL pré-générés dans [`stl/`](stl/).

Vue d'ensemble (fond en vue éclatée) :
[face](assembly_front.png) · [dos](assembly_back.png) · [façade](facade_icons.png)

La V0.3 adopte une silhouette « agitateur magnétique » : socle bas de
48 mm (empreinte 210 × 150) et **console avant inclinée à ~34°** portant la
façade LCD + boutons — l'écran se lit de dessus, le Raspberry Pi loge à plat
derrière la fente. Conserve les acquis V0.2 : façade rapportée (LCD vissé à
plat sur l'établi), poches à inserts filetés à chaque point de vissage,
fente débouchante sur toute la longueur (compatible vinyle), passages
élargis pour la prise USB-A du lecteur.

## Pièces

| Pièce | Orientation d'impression | Rôle |
|---|---|---|
| `shell` | **à l'envers** (dessus sur le plateau) | socle : console inclinée ouverte, fente traversante, arrière USB-C |
| `faceplate` | face avant sur le plateau | façade inclinée : fenêtre LCD + plots, 3 boutons en colonne, icônes **ajourées** |
| `backrest` | couché sur la face avant | dosseret trapézoïdal pleine largeur (coins hauts arrondis, h 84, sommet 126), intérieur creux : loge la carte ACR122U **en paysage** (93×62, antenne à gauche, câble à droite), butées de positionnement |
| `backrest_cover` | à plat | plaque arrière **affleurante**, même forme trapézoïdale que le dosseret |
| `lid` | à plat | fond vissé, plots Raspberry Pi, aérations |
| `icon_plate` | à plat, **couleur contrastée** | plaquette collée dans le lamage au dos de la façade : sa couleur apparaît à travers les icônes ajourées |

Les STL sont déjà exportés dans la bonne orientation.

## Impression

- **Matériau** : PLA (ou PETG). Buse 0,4, couches 0,2 mm, **3 périmètres**,
  remplissage 15 %, **sans support**.
- Plateau requis : 210 × 150 mm pour le socle.
- Les icônes de la façade sont **ajourées** : imprimer `icon_plate` dans une
  couleur contrastée et la coller dans le lamage au dos (cyanoacrylate ou
  double-face fin) — la couleur apparaît au fond des découpes, légèrement
  en retrait (effet de profondeur).

## Inserts filetés

Chaque point de vissage M3 a une **poche de positionnement Ø4,4 × 7 mm avec
cône d'entrée** : l'insert se pose dedans, se centre tout seul, puis se presse
au fer. Dimensionné pour les inserts **Hangtife M3×5×4** (OD 5,0, longueur 4,
trou recommandé 4,31–4,35 — l'imprimé Ø4,4 sort ~4,3 réel). Autres inserts :
ajuster `insert_d` / `insert_depth`.

| Emplacement | Nombre | Pressage depuis |
|---|---|---|
| Corps, cadre avant (façade) | 4 | l'avant, avant montage de la façade |
| Corps, bosses du fond | 4 | le dessous (boîtier ouvert) |
| Dosseret, face inférieure | 2 | le dessous, avant pose |
| Dosseret, face arrière (plaque) | 4 | l'arrière |

**Total : 14 inserts M3.**

## Visserie (kit de vis M3 CHC — têtes cylindriques Ø5,5×3, noyées en lamage)

- 4 × M3×8 CHC : façade → inserts de la console (lamages en face avant)
- 4 × M3×8 CHC : fond → inserts des bosses (lamages sous le fond)
- 2 × M3×8 CHC : face supérieure → inserts du dosseret (par l'intérieur, boîtier ouvert)
- 4 × M3×8 CHC : plaque arrière → inserts du dosseret (lamages)
- 4 × M3×8 CHC : LCD → avant-trous Ø2,8 des plots (la vis M3 se taraude dans le PLA)
- 4 × M2,5×6 : Raspberry Pi → plots du fond (non incluses dans le kit M3)
- Boutons 12 mm : écrou fourni ; embase USB-C : 2 × M2

Les plaques percées de lamages (façade, fond, plaque arrière) font 4 mm
d'épaisseur : la tête CHC affleure. Une seule longueur de vis (M3×8) suffit
pour tout le boîtier.

## Cotes vérifiées / à vérifier

1. **Carte nue ACR122U** : mesurée 60 × 91 mm — posée **en paysage** dans la
   cavité du dosseret (butées de positionnement), antenne à gauche, câble
   sortant à droite vers le passage décalé du socle.
2. **Embase USB-C panneau** : découpe `usbc_w / usbc_h` et entraxe
   `usbc_screw_dx` — à vérifier avant d'imprimer le corps.
3. **Inserts M3** : `insert_d` / `insert_depth` selon vos inserts.

## Régénérer les STL

```bash
for p in shell faceplate backrest backrest_cover lid; do
  openscad -o stl/$p.stl -D "part=\"$p\"" mcard.scad
done
```

`part="assembly"` dans l'interface graphique donne la vue d'ensemble.
