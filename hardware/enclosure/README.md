# Boîtier M-Card — impression 3D

Modèle paramétrique : [`mcard.scad`](mcard.scad) (toutes les cotes en tête de
fichier). STL pré-générés dans [`stl/`](stl/).

Vue d'ensemble (fond en vue éclatée) :
[face](assembly_front.png) · [dos](assembly_back.png)

## Pièces

| Pièce | Orientation d'impression | Rôle |
|---|---|---|
| `shell` | **à l'envers** (face supérieure sur le plateau) | corps : façade LCD + boutons (icônes ⏮ ⏯ ⏭ en relief 0,6 mm), fente CD/vinyle, arrière USB-C |
| `backrest` | couché sur la face avant | dosseret : soutient le CD/vinyle, loge la carte du lecteur ACR122U |
| `backrest_cover` | à plat | plaque de fermeture arrière du dosseret |
| `lid` | à plat | fond vissé, plots Raspberry Pi, aérations |

Les STL sont déjà exportés dans la bonne orientation.

## Impression

- **Matériau** : PLA (ou PETG). Aucune pièce ne chauffe.
- **Buse** 0,4 mm, couches 0,2 mm, **3 périmètres**, remplissage 15 %.
- **Sans support** : le chanfrein d'entrée de la fente est à 45°, le canal
  interne de la fente est un pont court (le slicer gère), les découpes de
  façade sont verticales.
- Plateau requis : 210 × 130 mm pour le corps (OK sur 220 × 220).

## Régénérer les STL

```bash
# macOS (brew install --cask openscad) :
alias openscad=/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD
for p in shell backrest backrest_cover lid; do
  openscad -o stl/$p.stl -D "part=\"$p\"" mcard.scad
done
```

`part="assembly"` dans l'interface graphique donne la vue d'ensemble.

## Cotes à vérifier avant impression

1. **Carte nue de l'ACR122U** : mesurée à 60 × 91 mm — logement calé à
   62 × 93 × 10 mm (`reader_w / reader_h / reader_t`), montage **en portrait,
   antenne (grande zone plane) vers le bas**, câble vers le haut. Ajuster
   `reader_t` si l'épaisseur avec composants dépasse 10 mm.
2. **Embase USB-C panneau** achetée : découpe `usbc_w / usbc_h` et entraxe
   `usbc_screw_dx` — à vérifier avant d'imprimer le corps.

Imprimez d'abord le `lid` (rapide) pour valider votre calibration de jeu :
les vis M3 doivent mordre dans les avant-trous de Ø2,8 mm.

## Visserie

- 4 × M3×10 : fond → bosses du corps
- 2 × M3×12 : face supérieure → dosseret (par l'intérieur)
- 4 × M3×8 : plaque arrière du dosseret
- 4 × M3×8 : LCD → plots de façade
- 4 × M2,5×6 : Raspberry Pi → plots du fond
- Boutons 12 mm : écrou fourni ; embase USB-C : 2 × M2
