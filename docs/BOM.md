# Nomenclature (BOM) — M-Card V0.1

## Déjà en votre possession

| Composant | Rôle | Note |
|---|---|---|
| Raspberry Pi 3 Model B+ | Ordinateur embarqué | Wi-Fi intégré, suffisant |
| Carte micro-SD (≥ 8 Go) | Système | Raspberry Pi OS Lite 64-bit |
| LCD 2004A 20×4 + backpack I2C PCF8574 (« MH ») | Affichage album/piste | 4 fils seulement (photo : backpack déjà soudé) |
| ACS ACR122U (PN532) | Lecteur RFID 13,56 MHz | Reste en USB, aucune soudure ; sorti de sa coque pour l'intégration |
| Cartes RFID 13,56 MHz (MIFARE/NTAG) | Identification des albums | L'UID suffit, pas d'écriture sur la carte |
| Imprimante 3D | Boîtier | PLA ou PETG |

## À acheter (~15–25 €)

| Qté | Composant | Rôle | Où (France, livraison rapide) | Prix indicatif |
|---|---|---|---|---|
| 3 | Bouton poussoir momentané 12 mm à visser (panel mount) | prev / play-pause / next | Amazon.fr « bouton poussoir 12mm momentané » (lot de 5–10) | ~8 € |
| 1 | Embase USB-C femelle panneau → micro-USB mâle (câble 25–30 cm) | Port d'alimentation arrière propre | Amazon.fr « USB C panel mount micro USB » | ~8 € |
| 1 | Lot de câbles Dupont femelle-femelle 20 cm | LCD + boutons ↔ GPIO | Amazon.fr / kit électronique | ~5 € |
| 8 | Vis M3 + inserts filetés à chaud M3 (ou vis auto-taraudeuses) | Assemblage boîtier | Amazon.fr « inserts filetés M3 impression 3D » | ~8 € (lot) |

Alimentation : chargeur USB-C 5 V ⩾ 3 A (type chargeur de téléphone récent) — probablement déjà disponible.

## Optionnel

| Composant | Pourquoi |
|---|---|
| Breadboard + boutons tactiles 6×6 mm | Phase de test avant montage final (souvent déjà dans un kit) |
| Convertisseur de niveau I2C bidirectionnel (2 canaux) | Par prudence sur le bus I2C 5 V ↔ 3,3 V ; en pratique le montage direct fonctionne (voir WIRING.md) |
| Ruban adhésif double face / colle chaude | Fixation du lecteur ACR122U dans le dosseret |

**Total à commander : ~15–25 €** selon lots. Aucun PCB custom nécessaire pour la V0.1 : le backpack I2C réduit le câblage à 8 fils Dupont au total.
