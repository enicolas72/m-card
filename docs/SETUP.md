# Installation logicielle — M-Card

## 1. Préparer la carte SD

1. **Raspberry Pi Imager** (sur le Mac) → *Raspberry Pi OS Lite (64-bit)*.
2. Dans les options de l'Imager (roue dentée / « Modifier les réglages ») :
   - nom d'hôte : `mcard`
   - **SSH activé**, utilisateur `pi` + mot de passe
   - **Wi-Fi** : SSID + mot de passe du réseau où tourne Roon, pays `FR`
   - (c'est ici que se règle le Wi-Fi ; l'appareil n'a besoin d'aucun autre
     accès réseau — pas d'Internet requis après l'installation)
3. Écrire, insérer dans le Pi, démarrer, puis : `ssh pi@mcard.local`

> Note : l'installation elle-même (apt/pip) nécessite un accès Internet
> temporaire. En fonctionnement, M-Card ne parle qu'au serveur Roon local.

## 2. Installer M-Card

```bash
# depuis le Mac, copier le dossier software/ sur le Pi :
rsync -a --exclude .venv --exclude __pycache__ software/ pi@mcard.local:mcard-software/

# puis sur le Pi :
ssh pi@mcard.local
cd mcard-software
sudo bash install.sh
sudo reboot
```

`install.sh` fait tout : paquets, utilisateur de service, venv Python,
activation I2C, blacklist des modules noyau NFC (indispensable pour
l'ACR122U), règle udev, configs par défaut dans `/etc/mcard`, service
systemd activé.

## 3. Premier démarrage

```bash
sudo systemctl start mcard
journalctl -u mcard -f
```

1. Le LCD affiche « M-Card / Démarrage... » puis « Posez un album ».
2. **Autoriser l'extension** : sur le Mac, Roon → *Settings* → *Extensions*
   → **Enable** en face de « M-Card ». (Le log affiche l'attente.)
3. Poser une carte RFID sur le lecteur :
   - carte inconnue → le LCD affiche l'UID, une entrée `album: TODO`
     apparaît dans `/etc/mcard/albums.yaml`
   - associer l'album : page `/search` de l'interface web (recherche →
     « Associer à cette carte »), ou remplacer `TODO` à la main dans
     `/etc/mcard/albums.yaml`
   - reposer la carte → l'album se lance.

## 4. Interface web (logs + configuration)

Depuis n'importe quel navigateur du réseau local :

| URL | Contenu |
|---|---|
| `http://mcard.local:8088/` | état : morceau en cours, connexion Roon, dernière carte |
| `http://mcard.local:8088/logs` | journal (lecture seule, téléchargeable) |
| `http://mcard.local:8088/config` | édition de `albums.yaml` et `mcard.yaml` (YAML validé avant sauvegarde, rechargement à chaud des albums) |
| `http://mcard.local:8088/search` | recherche libre d'albums dans Roon → fragment `path:` exact à copier, ou bouton « Associer à cette carte » (cartes en TODO proposées en premier) |

## 5. Réglages utiles (`/etc/mcard/mcard.yaml`)

- `roon.zone_name` : nom exact de la zone à piloter (sinon première zone).
- `behavior.on_card_removed` : `none` (défaut — l'album continue, boutons
  actifs), `pause` ou `stop`.
- `lcd.i2c_address` : `0x27` par défaut ; vérifier avec `i2cdetect -y 1`.
- `lcd.backlight_timeout_s` : veille du rétro-éclairage après N s sans
  interaction (défaut 120 ; 0 = toujours allumé). Toute carte ou bouton
  le rallume.
- Après modification : `sudo systemctl restart mcard`.

## 6. Développement sans Raspberry Pi (mode simulé)

Sur le Mac, sans aucun matériel :

```bash
cd software
python3 -m venv .venv && ./.venv/bin/pip install flask pyyaml
mkdir -p /tmp/mcard && cp config/*.example /tmp/mcard/
mv /tmp/mcard/mcard.yaml.example /tmp/mcard/mcard.yaml
mv /tmp/mcard/albums.yaml.example /tmp/mcard/albums.yaml
# adapter log.file vers un chemin accessible, puis :
./.venv/bin/python -m mcard --config /tmp/mcard --fake
```

Tapez un UID (ex. `04A1B2C3`) + Entrée pour « poser une carte », Entrée
seule pour la retirer. Le LCD s'affiche dans le terminal, Roon est simulé.

## 7. Dépannage

| Symptôme | Piste |
|---|---|
| `aucun serveur Roon découvert` | même réseau/VLAN que le Mac ? Roon lancé ? Essayer `roon.host: <ip-du-mac>` |
| Lecteur NFC introuvable | `lsusb` doit montrer `072f:2200` ; vérifier le blacklist : `lsmod \| grep pn533` doit être vide ; rebooter |
| LCD vide | contraste (potentiomètre au dos) ; `i2cdetect -y 1` → adresse `27` ou `3F` |
| LCD caractères aléatoires | GND/VCC inversés sur le backpack, ou câble SDA/SCL trop long |
| Extension jamais proposée dans Roon | pare-feu du Mac : autoriser Roon ; le Pi et le Mac doivent être sur le même sous-réseau |
| Boutons sans effet | numérotation BCM (GPIO5 = broche physique 29) ; tester avec `journalctl -u mcard -f` |
