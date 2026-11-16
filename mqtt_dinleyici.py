import paho.mqtt.client as mqtt
import json
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Supabase bilgileri .env dosyasından okunur (bkz. .env.example)
load_dotenv()

# --- SUPABASE BAĞLANTI AYARLARI ---
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MQTT AYARLARI ---
MQTT_BROKER = "172.20.10.4"
MQTT_PORT = 1883
MQTT_TOPIC = "kompost/sensorler"

def on_connect(client, userdata, flags, rc):
    print(f"Mosquitto Broker'a Başarıyla Bağlanıldı! (Durum Kodu: {rc})")
    client.subscribe(MQTT_TOPIC)
    print(f"Havadan '{MQTT_TOPIC}' konusu dinleniyor...\n")

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print(f"\n📦 YENİ VERİ PAKETİ GELDİ: {payload}")
    
    try:
        # 1. JSON'ı Python sözlüğüne çevir
        veri = json.loads(payload)
        
        # 2. Supabase tablosuna uygun formata getir
        # Sol taraftaki isimler Supabase tablondaki sütun isimleriyle BİREBİR aynı olmalıdır.
        db_verisi = {
            "ornek_id": "1",           # Hangi atık grubunu ölçüyorsak onun ID'si
            "bilesen_sinifi": "Domates-Biber",   # Şimdilik varsayılan bir metin
            "kutle": 0.0,                        # Tartım yapılana kadar varsayılan 
            "sicaklik": None,                    # DS18B20 sensörü bağlanınca güncelleyeceğiz
            "nem": veri.get("nem_ham"),          # Toprak nemi
            "co2": veri.get("gaz_ham"),          # MQ135 Gaz verisi
            "nh3": None,                         # İkinci bir gaz sensörü/hesaplaması için
            "ph": veri.get("ph_ham"),            # pH verisi
            "c_n_orani": None,                   # Analiz/Hesaplama sonucu
            "partikul_boyutu": 0.0,              # Görüntü işlemeden (OpenCV) gelecek değer
            "uygulanan_formulasyon": "Tübitak_1" # Deney grubunun adı
        }
        
        # 3. Veriyi Supabase'e gönder 
        response = supabase.table("kompost_olcumleri").insert(db_verisi).execute()
        
        print("✅ Veri Supabase'e başarıyla kaydedildi!")
        
    except Exception as e:
        print("❌ HATA - Veri işlenemedi veya veritabanına yazılamadı:", e)

# MQTT İstemcisini başlat
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Sistem Başlatılıyor...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()