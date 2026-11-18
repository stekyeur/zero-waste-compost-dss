#!/usr/bin/env bash
# =============================================================
#  ZeroWaste - Raspberry Pi gateway kurulumu
#  Proje klasörünün içinde çalıştırın:   bash pi_kurulum.sh
#  Yaptıkları: Mosquitto kurar ve ağa açar, Python ortamını kurar,
#  gateway'i Pi her açıldığında otomatik başlayan bir servis yapar.
# =============================================================
set -e
KLASOR="$(cd "$(dirname "$0")" && pwd)"
KULLANICI="$(whoami)"

if [ ! -f "$KLASOR/.env" ]; then
  echo "HATA: $KLASOR/.env bulunamadı. Önce .env dosyasını bu klasöre kopyalayın."
  exit 1
fi

echo "== 1/4 Paketler kuruluyor (Mosquitto, Python venv) =="
sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients python3-venv

echo "== 2/4 Mosquitto ağa açılıyor (port 1883) =="
sudo tee /etc/mosquitto/conf.d/zerowaste.conf > /dev/null <<'CONF'
listener 1883 0.0.0.0
allow_anonymous true
CONF
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

echo "== 3/4 Python ortamı kuruluyor =="
python3 -m venv "$KLASOR/.venv"
"$KLASOR/.venv/bin/pip" install --upgrade pip
"$KLASOR/.venv/bin/pip" install -r "$KLASOR/requirements_pi.txt"

echo "== 4/4 Otomatik başlatma servisi oluşturuluyor =="
sudo tee /etc/systemd/system/zerowaste-gateway.service > /dev/null <<UNIT
[Unit]
Description=ZeroWaste MQTT -> Supabase gateway
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
User=$KULLANICI
WorkingDirectory=$KLASOR
ExecStart=$KLASOR/.venv/bin/python -u $KLASOR/mqtt_dinleyici.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable zerowaste-gateway

echo
echo "Kurulum tamamlandı."
echo "  Pi'nin IP adresi (ESP32 secrets.h > MQTT_BROKER):  $(hostname -I | awk '{print $1}')"
echo "  Önce elle test:       .venv/bin/python mqtt_dinleyici.py"
echo "  Servisi başlat:       sudo systemctl start zerowaste-gateway"
echo "  Servis kayıtları:     journalctl -u zerowaste-gateway -f"
