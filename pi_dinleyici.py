import paho.mqtt.client as mqtt
import json
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Supabase bilgileri .env dosyasından okunur (bkz. .env.example)
load_dotenv()

# Supabase API Ayarları
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

broker_adresi = "127.0.0.1"
port = 1883
konu = "kompost/sensorler"

def mesaj_geldi(client, userdata, msg):
    try:
        gelen_veri = json.loads(msg.payload.decode())
        print(f"\n[YENİ VERİ] Örnek ID: {gelen_veri['ornek_id']} | Sıcaklık: {gelen_veri['sicaklik']}°C")
        
        # Sadece gelen sensör verilerini Supabase'e ekle (diğer sütunlar boş/null kalacak)
        data, count = supabase.table('kompost_olcumleri').insert({
            "ornek_id": gelen_veri['ornek_id'],
            "sicaklik": gelen_veri['sicaklik'],
            "nem": gelen_veri['nem'],
            "co2": gelen_veri['co2'],
            "nh3": gelen_veri['nh3'],
            "ph": gelen_veri['pH']
        }).execute()
        
        print("[BAŞARILI] Veri Supabase'e kaydedildi.")
        
    except Exception as e:
        print(f"[HATA] İşlem başarısız: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = mesaj_geldi

client.connect(broker_adresi, port)
client.subscribe(konu)

print("Raspberry Pi - Supabase Köprüsü Çalışıyor. Dinleniyor... (Durdurmak için Ctrl+C)")
client.loop_forever()