"""
ZeroWaste Gateway: MQTT -> Supabase
====================================
Raspberry Pi'de (veya bilgisayarda) çalışır. ESP32'nin "kompost/sensorler" konusuna
yayınladığı JSON ölçümleri dinler ve Supabase'deki "kompost_olcumleri" tablosuna
HTTPS POST (Supabase REST API) ile yazar.

İnternet yoksa ölçümler "bekleyen_kayitlar.jsonl" dosyasında bekletilir ve bağlantı
geri gelince sırayla gönderilir (offline buffer).

Kullanım:
    python mqtt_dinleyici.py              # örnek numarası .env'deki ORNEK_ID (yoksa 1)
    python mqtt_dinleyici.py --ornek 5    # bu deneyin örnek numarası 5

Ayarlar .env dosyasından okunur (bkz. .env.example).
"""
import argparse
import json
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------- AYARLAR ----------------
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
TABLO = os.getenv("SUPABASE_TABLO", "kompost_olcumleri")

MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")    # Pi'de broker aynı cihazda çalışır
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "kompost/sensorler")

KUYRUK_DOSYASI = "bekleyen_kayitlar.jsonl"   # internet yokken bekleyen ölçümler
HATALI_DOSYASI = "hatali_kayitlar.jsonl"     # Supabase'in reddettiği ölçümler

REST_URL = f"{SUPABASE_URL}/rest/v1/{TABLO}"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Tabloda en baştan beri olan sütunlar
ESKI_SUTUNLAR = {"ornek_id", "bilesen_sinifi", "kutle", "sicaklik", "nem", "co2", "nh3",
                 "ph", "c_n_orani", "partikul_boyutu", "uygulanan_formulasyon"}
yeni_sutunlar_var = True     # supabase_kurulum.sql çalıştırılmadıysa otomatik False olur
ornek_id = os.getenv("ORNEK_ID", "1")


class BaglantiHatasi(Exception):
    """İnternet / Supabase'e ulaşılamadı: ölçüm kuyruğa alınmalı."""


class VeriHatasi(Exception):
    """Supabase ölçümü reddetti (sütun, tip vb.): tekrar denemek işe yaramaz."""


# ---------------- VERİ DÖNÜŞÜMÜ ----------------
def satir_olustur(veri):
    """ESP32 JSON'unu kompost_olcumleri tablosunun bir satırına çevirir."""
    return {
        # Deney bilgileri
        "ornek_id": ornek_id,
        "bilesen_sinifi": os.getenv("BILESEN_SINIFI") or None,
        "uygulanan_formulasyon": os.getenv("FORMULASYON") or None,
        "kutle": None,               # tartım yapılınca
        "partikul_boyutu": None,     # görüntü işlemeden gelecek
        "c_n_orani": None,           # analiz sonucu

        # Fiziksel birimdeki ölçümler
        "sicaklik": veri.get("sicaklik_kompost"),   # DS18B20, kompost içi °C
        "nem": veri.get("nem_yuzde"),               # toprak nemi % (kalibrasyon sonrası anlamlı)
        "co2": None,                                # MQ135 kalibre edilince hesaplanacak
        "nh3": None,
        "ph": None,                                 # pH 4 / 7 tamponlarıyla kalibrasyon sonrası

        # Yeni sütunlar (supabase_kurulum.sql ile eklenir)
        "olcum_zamani": datetime.now(timezone.utc).isoformat(),
        "cihaz": veri.get("cihaz"),
        "olcum_no": veri.get("olcum_no"),
        "sicaklik_hava": veri.get("sicaklik_hava"),  # DHT11 °C
        "nem_hava": veri.get("nem_hava"),            # DHT11 %
        "nem_ham": veri.get("nem_ham"),
        "gaz_ham": veri.get("gaz_ham"),
        "gaz_mv": veri.get("gaz_mv"),
        "ph_ham": veri.get("ph_ham"),
        "ph_mv": veri.get("ph_mv"),
    }


# ---------------- SUPABASE'E GÖNDERME ----------------
def supabase_gonder(satir):
    """Bir satırı Supabase'e yazar. Başarısızlıkta BaglantiHatasi veya VeriHatasi fırlatır."""
    global yeni_sutunlar_var
    if not yeni_sutunlar_var:
        satir = {k: v for k, v in satir.items() if k in ESKI_SUTUNLAR}

    try:
        r = requests.post(REST_URL, headers=HEADERS, json=satir, timeout=10)
    except requests.exceptions.RequestException as e:
        raise BaglantiHatasi(type(e).__name__) from e

    if r.status_code in (200, 201, 204):
        return
    if r.status_code >= 500 or r.status_code == 429:
        raise BaglantiHatasi(f"Supabase {r.status_code}")

    try:
        kod = r.json().get("code")
    except ValueError:
        kod = None
    if kod == "PGRST204" and yeni_sutunlar_var:
        print("[UYARI] Yeni sütunlar tabloda yok (supabase_kurulum.sql çalıştırılmamış).\n"
              "        Şimdilik sadece eski sütunlar yazılıyor.")
        yeni_sutunlar_var = False
        return supabase_gonder(satir)
    raise VeriHatasi(f"Supabase {r.status_code}: {r.text[:300]}")


def dosyaya_ekle(dosya, satir):
    with open(dosya, "a", encoding="utf-8") as f:
        f.write(json.dumps(satir, ensure_ascii=False) + "\n")


def kuyrugu_bosalt():
    """Bekleyen ölçümleri sırayla göndermeyi dener. İnternet hâlâ yoksa durur."""
    if not os.path.exists(KUYRUK_DOSYASI):
        return
    with open(KUYRUK_DOSYASI, encoding="utf-8") as f:
        bekleyenler = [json.loads(s) for s in f if s.strip()]
    if not bekleyenler:
        return

    gonderilen = 0
    for satir in bekleyenler:
        try:
            supabase_gonder(satir)
        except BaglantiHatasi:
            break
        except VeriHatasi as e:
            print(f"[HATA] Bekleyen kayıt reddedildi: {e}")
            dosyaya_ekle(HATALI_DOSYASI, satir)
        gonderilen += 1

    kalanlar = bekleyenler[gonderilen:]
    with open(KUYRUK_DOSYASI, "w", encoding="utf-8") as f:
        for satir in kalanlar:
            f.write(json.dumps(satir, ensure_ascii=False) + "\n")
    if gonderilen:
        print(f"[KUYRUK] {gonderilen} bekleyen ölçüm gönderildi, {len(kalanlar)} kaldı.")


def olcum_isle(payload):
    """Gelen MQTT mesajını işler. Testlerde de doğrudan çağrılabilir."""
    try:
        veri = json.loads(payload)
    except json.JSONDecodeError:
        print(f"[HATA] JSON çözülemedi: {payload[:200]}")
        return

    satir = satir_olustur(veri)
    print(f"\n📦 Ölçüm #{veri.get('olcum_no')} | kompost: {veri.get('sicaklik_kompost')} °C | "
          f"hava: {veri.get('sicaklik_hava')} °C, %{veri.get('nem_hava')} | "
          f"toprak nemi ham: {veri.get('nem_ham')} | gaz: {veri.get('gaz_mv')} mV | "
          f"pH: {veri.get('ph_mv')} mV")

    kuyrugu_bosalt()
    try:
        supabase_gonder(satir)
        print("✅ Supabase'e kaydedildi.")
    except BaglantiHatasi as e:
        dosyaya_ekle(KUYRUK_DOSYASI, satir)
        print(f"⏳ İnternet/Supabase yok, ölçüm kuyruğa alındı ({e}).")
    except VeriHatasi as e:
        dosyaya_ekle(HATALI_DOSYASI, satir)
        print(f"❌ Supabase ölçümü reddetti: {e}")


# ---------------- MQTT ----------------
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[MQTT] Bağlantı reddedildi: {reason_code}")
        return
    client.subscribe(MQTT_TOPIC)
    print(f"[MQTT] {MQTT_BROKER}:{MQTT_PORT} broker'ına bağlanıldı. '{MQTT_TOPIC}' dinleniyor...")


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[MQTT] Bağlantı koptu ({reason_code}), yeniden bağlanılıyor...")


def on_connect_fail(client, userdata):
    print(f"[MQTT] {MQTT_BROKER}:{MQTT_PORT} broker'ına ulaşılamadı, tekrar deneniyor... "
          "(Mosquitto çalışıyor mu?)")


def on_message(client, userdata, msg):
    olcum_isle(msg.payload.decode("utf-8", errors="replace"))


def main():
    global ornek_id
    ap = argparse.ArgumentParser(description="ZeroWaste MQTT -> Supabase gateway")
    ap.add_argument("--ornek", help="Bu deneyin örnek (sample) numarası")
    args = ap.parse_args()
    if args.ornek:
        ornek_id = args.ornek

    print(f"ZeroWaste Gateway başlıyor | Örnek ID: {ornek_id} | Tablo: {TABLO}")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="zerowaste-gateway")
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_connect_fail = on_connect_fail
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
    try:
        client.loop_forever(retry_first_connection=True)   # broker henüz açılmadıysa bekler
    except KeyboardInterrupt:
        print("\nGateway durduruldu.")
        client.disconnect()


if __name__ == "__main__":
    main()
