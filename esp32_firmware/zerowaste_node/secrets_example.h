// =============================================================
//  secrets_example.h  ->  Bu dosyayı "secrets.h" adıyla kopyalayıp
//  kendi bilgilerinizi yazın. secrets.h git'e gönderilmez.
// =============================================================
#pragma once

// iPhone kişisel erişim noktası (hotspot) bilgileri.
// ÖNEMLİ: iPhone'da "Uyumluluğu En Üst Düzeye Çıkar" açık olmalı;
// ESP32 sadece 2.4 GHz Wi-Fi'ye bağlanabilir.
#define WIFI_SSID      "iPhone_Adi"
#define WIFI_PASSWORD  "hotspot_sifresi"

// MQTT broker'ın (Mosquitto) çalıştığı bilgisayarın IP adresi.
//  - Şimdilik dizüstü bilgisayar:  Windows'ta "ipconfig" ile bakın (ör. 172.20.10.4)
//  - Raspberry Pi'ye geçince:      Pi'de "hostname -I" ile bakın
#define MQTT_BROKER    "172.20.10.4"
#define MQTT_PORT      1883
