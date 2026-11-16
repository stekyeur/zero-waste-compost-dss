import paho.mqtt.client as mqtt
import json
import time
import random

# MQTT Ayarları
broker_adresi = "127.0.0.1"  # Localhost (kendi bilgisayarımız)
port = 1883
konu = "kompost/sensorler"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(broker_adresi, port)

print("ESP32 Simülatörü Başladı. Veriler gönderiliyor... (Durdurmak için Ctrl+C)")

try:
    while True:
        # Formda belirtilen ölçümler için sahte veriler
        veri = {
            "ornek_id": 1001,
            "sicaklik": round(random.uniform(22.0, 28.0), 1),
            "nem": round(random.uniform(40.0, 60.0), 1),
            "pH": round(random.uniform(5.5, 7.5), 1),
            "co2": random.randint(400, 800),
            "nh3": round(random.uniform(0.1, 5.0), 2)
        }
        
        mesaj = json.dumps(veri)
        client.publish(konu, mesaj)
        print(f"[YAYINLANDI] {mesaj}")
        
        time.sleep(3)  # 3 saniyede bir veri gönder
except KeyboardInterrupt:
    print("Veri gönderimi durduruldu.")
    client.disconnect()