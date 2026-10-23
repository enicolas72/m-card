#!/usr/bin/env bash
# Installs M-Card on Raspberry Pi OS (Bookworm or newer).
# Run on the Pi, from the software/ folder: sudo bash install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash install.sh" >&2
  exit 1
fi

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR=/opt/mcard
CONF_DIR=/etc/mcard

echo "== System packages =="
apt-get update
apt-get install -y python3-venv python3-dev libusb-1.0-0 i2c-tools swig liblgpio-dev

echo "== Service user =="
if ! id mcard &>/dev/null; then
  useradd --system --home-dir /var/lib/mcard --create-home mcard
fi
# I2C (LCD), GPIO (buttons) and USB (NFC reader) access
usermod -aG i2c,gpio,plugdev mcard || true

echo "== Enabling the I2C bus =="
raspi-config nonint do_i2c 0 || echo "(raspi-config missing? enable I2C manually)"

echo "== ACR122U reader: release the device from the kernel driver =="
cat > /etc/modprobe.d/blacklist-mcard-nfc.conf <<'EOF'
# The NFC kernel modules grab the ACR122U; nfcpy drives the USB device directly.
blacklist pn533_usb
blacklist pn533
blacklist nfc
EOF
modprobe -r pn533_usb pn533 nfc 2>/dev/null || true

cat > /etc/udev/rules.d/90-mcard-acr122u.rules <<'EOF'
# ACS ACR122U: accessible to the plugdev group without root
SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2200", MODE="0664", GROUP="plugdev"
EOF
udevadm control --reload-rules && udevadm trigger || true

echo "== Python application =="
mkdir -p "$APP_DIR"
cp -r "$SRC_DIR/mcard" "$APP_DIR/"
cp "$SRC_DIR/requirements.txt" "$APP_DIR/"
if [[ ! -d "$APP_DIR/venv" ]]; then
  python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
# make the package importable from the venv
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

Installation complete.

Next steps:
  1. Edit /etc/mcard/mcard.yaml if needed (Roon zone, pins...)
  2. Start:                sudo systemctl start mcard
  3. Enable the "M-Card" extension in Roon -> Settings -> Extensions
  4. Follow the logs:      journalctl -u mcard -f
  5. Web console:          http://<pi-ip>:8088

A reboot is recommended after the first install (module blacklist + I2C):
  sudo reboot
EOF
