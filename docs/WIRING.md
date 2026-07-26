# Câblage — M-Card V0.1

Schéma visuel : [`wiring-diagram.svg`](wiring-diagram.svg)

Aucune soudure n'est nécessaire pour la phase breadboard : tout se fait en
câbles Dupont femelle-femelle. Le lecteur ACR122U reste en USB.

## Vue d'ensemble

```
                        ┌────────────────────────┐
   Chargeur USB-C ──────► Embase USB-C (arrière) │
                        │        │ micro-USB     │
                        │  ┌─────▼──────────┐    │  câble USB captif  ┌───────────┐
                        │  │ Raspberry Pi 3B+ ◄──┼────────────────────► ACR122U   │
                        │  └─┬────────┬─────┘    │                    │ (derrière │
                        │    │ I2C    │ GPIO     │                    │ la fente) │
                        │  ┌─▼────┐ ┌─▼───────┐  │                    └───────────┘
                        │  │ LCD  │ │ 3 boutons│ │
                        │  │ 20×4 │ │  ⏮ ⏯ ⏭  │  │
                        │  └──────┘ └─────────┘  │
                        └────────────────────────┘
         Wi-Fi ↔ serveur Roon (Mac) — aucune autre connexion réseau
```

## LCD 2004 (backpack I2C PCF8574) — 4 fils

| Backpack LCD | Broche Pi (physique) | Signal Pi |
|---|---|---|
| GND | 6 | GND |
| VCC | 2 | 5 V |
| SDA | 3 | GPIO2 (SDA1) |
| SCL | 5 | GPIO3 (SCL1) |

- Adresse I2C : `0x27` en général (vérifier : `i2cdetect -y 1` ; si `0x3F`,
  ajuster `lcd.i2c_address` dans `mcard.yaml`).
- Contraste : petit potentiomètre bleu au dos du backpack.
- **Niveaux logiques** : le backpack est alimenté en 5 V, le Pi est en 3,3 V.
  Les pull-ups internes du Pi (1,8 kΩ vers 3,3 V) dominent celles du backpack :
  ce montage direct est le montage standard utilisé partout et fonctionne de
  façon fiable. Les puristes peuvent intercaler un convertisseur de niveau
  bidirectionnel sur SDA/SCL (cf. BOM, optionnel).

## Boutons — 6 fils

Chaque bouton momentané relie une broche GPIO à GND (pull-up interne activé
par le logiciel, appui = niveau bas). L'ordre sur la façade, de gauche à
droite : ⏮ prev, ⏯ play/pause (bascule), ⏭ next.

| Bouton | GPIO (BCM) | Broche Pi (physique) | GND commun |
|---|---|---|---|
| ⏮ prev | GPIO5 | 29 | 39 |
| ⏯ play/pause | GPIO6 | 31 | 39 |
| ⏭ next | GPIO13 | 33 | 39 |

Les 3 retours GND peuvent être chaînés entre eux puis ramenés en un seul fil
à la broche 39 (ou répartis sur les broches 30/34/39).

Pins choisis volontairement adjacents (29→33, côté extérieur du connecteur,
sérigraphiés l'un sous l'autre sur un cobbler) et loin de l'I2C : câblage
propre et lisible.

## Lecteur RFID ACR122U — USB

- Branché sur un port USB-A du Pi avec son câble captif d'origine
  (l'excédent s'enroule dans le socle).
- **Aucune modification électronique** : pour l'intégration, on retire
  simplement la coque blanche (4 vis sous les patins) et la carte nue se
  fixe derrière la paroi de la fente (portée de lecture ~4 cm, traverse
  sans problème 3 mm de PLA + le boîtier CD).
- Côté système, les modules noyau `pn533_usb`/`pn533`/`nfc` doivent être
  blacklistés (fait par `install.sh`, cf. SETUP.md) sinon Linux monopolise
  le lecteur.

## Alimentation

- Embase USB-C femelle montée dans le panneau arrière → câble micro-USB
  vers le port d'alimentation du Pi. L'extérieur ne voit qu'un port USB-C.
- Chargeur 5 V / 3 A recommandé (Pi 3B+ ~1,2 A + ACR122U 0,2 A + LCD 0,05 A,
  marge confortable).

## Phase breadboard (avant montage final)

1. Câbler le LCD (4 fils) et vérifier : `i2cdetect -y 1` doit montrer `27`.
2. Câbler 3 boutons tactiles 6×6 mm sur breadboard vers GPIO 5/6/13 et GND.
3. Brancher l'ACR122U en USB.
4. Lancer `python -m mcard --config /etc/mcard` et valider :
   carte connue → lecture Roon ; carte inconnue → entrée TODO ; boutons →
   transport ; LCD → album/piste.
5. Ensuite seulement, démonter et intégrer dans le boîtier (ASSEMBLY.md).
   Les boutons 12 mm du boîtier se câblent exactement pareil.
