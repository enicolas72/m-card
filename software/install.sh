#!/usr/bin/env bash
# Installation de M-Card sur Raspberry Pi OS (Bookworm ou plus récent).
# À lancer sur le Pi, depuis le dossier software/ : sudo bash install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Lancer avec sudo : sudo bash install.sh" >&2
  exit 1
fi

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR=/opt/mcard
CONF_DIR=/etc/mcard

echo "== Paquets système =="
apt-get update
apt-get install -y python3-venv python3-dev libusb-1.0-0 i2c-tools swig liblgpio-dev

echo "== Utilisateur de service =="
if ! id mcard &>/dev/null; then
  useradd --system --home-dir /var/lib/mcard --create-home mcard
fi
# accès I2C (LCD), GPIO (boutons) et USB (lecteur NFC)
usermod -aG i2c,gpio,plugdev mcard || true

echo "== Activation du bus I2C =="
raspi-config nonint do_i2c 0 || echo "(raspi-config absent ? activer I2C manuellement)"

echo "== Lecteur ACR122U : liberer le peripherique du pilote noyau =="
cat > /etc/modprobe.d/blacklist-mcard-nfc.conf <<'EOF'
# Les modules noyau NFC monopolisent l'ACR122U ; nfcpy pilote l'USB en direct.
blacklist pn533_usb
blacklist pn533
blacklist nfc
EOF
modprobe -r pn533_usb pn533 nfc 2>/dev/null || true

cat > /etc/udev/rules.d/90-mcard-acr122u.rules <<'EOF'
# ACS ACR122U : accessible au groupe plugdev sans root
SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2200", MODE="0664", GROUP="plugdev"
EOF
udevadm control --reload-rules && udevadm trigger || true

echo "== Application Python =="
mkdir -p "$APP_DIR"
cp -r "$SRC_DIR/mcard" "$APP_DIR/"
cp "$SRC_DIR/requirements.txt" "$APP_DIR/"
if [[ ! -d "$APP_DIR/venv" ]]; then
  python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
# rendre le package importable depuis le venv
"$APP_DIR/venv/bin/python" - <<EOF
import site, pathlib
site_dir = pathlib.Path(site.getsitepackages()[0] if hasattr(site, "getsitepackages") else "")
(site_dir / "mcard.pth").write_text("$APP_DIR\n")
print("mcard.pth ->", site_dir)
EOF

echo "== Configuration =="
mkdir -p "$CONF_DIR" /var/log/mcard /var/lib/mcard
[[ -f "$CONF_DIR/mcard.yaml"  ]] || cp "$SRC_DIR/config/mcard.yaml.example"  "$CONF_DIR/mcard.yaml"
[[ -f "$CONF_DIR/albums.yaml" ]] || cp "$SRC_DIR/config/albums.yaml.example" "$CONF_DIR/albums.yaml"
chown -R mcard:mcard "$CONF_DIR" /var/log/mcard /var/lib/mcard
chmod 664 "$CONF_DIR"/*.yaml

echo "== Service systemd =="
cp "$SRC_DIR/systemd/mcard.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable mcard.service

cat <<'EOF'

Installation terminée.

Étapes suivantes :
  1. Éditer /etc/mcard/mcard.yaml si besoin (zone Roon, broches...)
  2. Démarrer :            sudo systemctl start mcard
  3. Autoriser l'extension « M-Card » dans Roon -> Settings -> Extensions
  4. Suivre les logs :     journalctl -u mcard -f
  5. Interface web :       http://<ip-du-pi>:8088

Un redémarrage est conseillé au premier install (blacklist modules + I2C) :
  sudo reboot
EOF
