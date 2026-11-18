// =============================================================
//  ZeroWaste - ESP32 Sensör Düğümü
//  Sensörleri okur ve JSON olarak MQTT'ye yayınlar.
//
//  Bağlantılar (rapordaki Figure 2 ile aynı):
//    DHT11 (hava sıcaklığı & nemi)  -> GPIO4
//    DS18B20 (kompost sıcaklığı)    -> GPIO5  (+ 4.7k pull-up, 3.3V'a)
//    Toprak nemi (analog)           -> GPIO32
//    Gaz sensörü MQ135 (analog)     -> GPIO34
//    pH modülü (analog)             -> GPIO35
//
//  Gerekli kütüphaneler (Arduino IDE > Kütüphane Yöneticisi):
//    - PubSubClient            (Nick O'Leary)
//    - DHT sensor library      (Adafruit)  + Adafruit Unified Sensor
//    - OneWire                 (Paul Stoffregen)
//    - DallasTemperature       (Miles Burton)
//
//  Bağlı olmayan bir sensör programı durdurmaz: değeri "null" gönderilir.
// =============================================================

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "secrets.h"

// ---------------- PINLER ----------------
#define PIN_DHT        4
#define PIN_DS18B20    5
#define PIN_TOPRAK     32
#define PIN_GAZ        34
#define PIN_PH         35
#define PIN_LED        2      // DevKit üzerindeki mavi LED

#define DHT_TIPI       DHT11

// ---------------- AYARLAR ----------------
const char*    MQTT_TOPIC       = "kompost/sensorler";
const uint32_t OLCUM_ARALIGI_MS = 5000;   // 5 saniyede bir ölçüm
const int      ORNEK_SAYISI     = 20;     // analog okumalarda ortalama

// 5V ile beslenen modüllerin çıkışında gerilim bölücü varsa oranı yazın.
// Örn. 10k (üst) + 20k (alt) bölücü -> 1.5.  Bölücü yoksa 1.0 bırakın.
const float GAZ_BOLUCU_ORANI = 1.0;
const float PH_BOLUCU_ORANI  = 1.0;

// Toprak nemi kalibrasyonu (ham ADC değerleri).
// Sensör kuru havadayken ve suya batırılmışken Seri Monitörde görülen
// "toprak_ham" değerlerini buraya yazın.
const int TOPRAK_KURU_HAM = 3000;
const int TOPRAK_ISLAK_HAM = 1300;

// ---------------- NESNELER ----------------
WiFiClient        wifiClient;
PubSubClient      mqtt(wifiClient);
DHT               dht(PIN_DHT, DHT_TIPI);
OneWire           oneWire(PIN_DS18B20);
DallasTemperature ds18b20(&oneWire);

uint32_t sonOlcum = 0;
uint32_t sonMqttDeneme = 0;
uint32_t olcumNo = 0;
char     cihazId[32];

// ---------------- YARDIMCI FONKSİYONLAR ----------------

// Analog pini ORNEK_SAYISI kez okuyup ortalamasını verir.
void analogOku(int pin, int &ham, int &mv) {
  long hamToplam = 0, mvToplam = 0;
  for (int i = 0; i < ORNEK_SAYISI; i++) {
    hamToplam += analogRead(pin);
    mvToplam  += analogReadMilliVolts(pin);   // ESP32 kalibrasyonlu mV
    delay(2);
  }
  ham = hamToplam / ORNEK_SAYISI;
  mv  = mvToplam / ORNEK_SAYISI;
}

// float değeri JSON'a yazar; geçersizse null yazar.
void jsonFloat(char *buf, size_t n, float v, int basamak) {
  if (isnan(v)) snprintf(buf, n, "null");
  else          snprintf(buf, n, "%.*f", basamak, v);
}

void wifiBaglan() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("[WiFi] '%s' agina baglaniliyor", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t bas = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - bas < 15000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Baglandi. IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] Baglanamadi, olcumler yine de Seri Monitore yazilacak.");
  }
}

void mqttBaglan() {
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED) return;
  if (millis() - sonMqttDeneme < 5000) return;   // 5 sn'de bir dene, programı kilitleme
  sonMqttDeneme = millis();
  Serial.printf("[MQTT] %s:%d broker'ina baglaniliyor... ", MQTT_BROKER, MQTT_PORT);
  if (mqtt.connect(cihazId)) {
    Serial.println("baglandi.");
  } else {
    Serial.printf("basarisiz (durum=%d). Broker IP'sini ve Mosquitto'yu kontrol edin.\n", mqtt.state());
  }
}

void olcVeGonder() {
  olcumNo++;

  // --- Dijital sensörler ---
  float havaSicaklik = dht.readTemperature();   // °C, okunamazsa NaN
  float havaNem      = dht.readHumidity();      // %,  okunamazsa NaN

  ds18b20.requestTemperatures();
  float kompostSicaklik = ds18b20.getTempCByIndex(0);
  if (kompostSicaklik == DEVICE_DISCONNECTED_C) kompostSicaklik = NAN;

  // --- Analog sensörler ---
  int toprakHam, toprakMv, gazHam, gazMv, phHam, phMv;
  analogOku(PIN_TOPRAK, toprakHam, toprakMv);
  analogOku(PIN_GAZ,    gazHam,    gazMv);
  analogOku(PIN_PH,     phHam,     phMv);

  // Bölücü varsa sensörün kendi çıkış gerilimine geri çevir
  int gazSensorMv = (int)(gazMv * GAZ_BOLUCU_ORANI);
  int phSensorMv  = (int)(phMv  * PH_BOLUCU_ORANI);

  // Toprak nemi yüzdesi (kuru = %0, ıslak = %100)
  float toprakYuzde = 100.0f * (TOPRAK_KURU_HAM - toprakHam) / (float)(TOPRAK_KURU_HAM - TOPRAK_ISLAK_HAM);
  toprakYuzde = constrain(toprakYuzde, 0.0f, 100.0f);

  // --- JSON oluştur ---
  // "nem_ham", "gaz_ham", "ph_ham" alanları mevcut mqtt_dinleyici.py ile uyumludur.
  char s1[12], s2[12], s3[12];
  jsonFloat(s1, sizeof(s1), havaSicaklik, 1);
  jsonFloat(s2, sizeof(s2), havaNem, 1);
  jsonFloat(s3, sizeof(s3), kompostSicaklik, 2);

  char json[400];
  snprintf(json, sizeof(json),
    "{\"cihaz\":\"%s\",\"olcum_no\":%lu,"
    "\"sicaklik_hava\":%s,\"nem_hava\":%s,\"sicaklik_kompost\":%s,"
    "\"nem_ham\":%d,\"nem_yuzde\":%.1f,"
    "\"gaz_ham\":%d,\"gaz_mv\":%d,"
    "\"ph_ham\":%d,\"ph_mv\":%d}",
    cihazId, (unsigned long)olcumNo,
    s1, s2, s3,
    toprakHam, toprakYuzde,
    gazHam, gazSensorMv,
    phHam, phSensorMv);

  Serial.println(json);

  if (mqtt.connected()) {
    if (mqtt.publish(MQTT_TOPIC, json)) {
      digitalWrite(PIN_LED, HIGH); delay(80); digitalWrite(PIN_LED, LOW);   // gönderildi işareti
    } else {
      Serial.println("[MQTT] Yayinlama basarisiz.");
    }
  }
}

// ---------------- KURULUM ----------------
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== ZeroWaste ESP32 Sensor Dugumu ===");

  pinMode(PIN_LED, OUTPUT);
  analogReadResolution(12);              // 0-4095 (varsayılan zayıflatma ~0-3.1 V aralığını okur)

  dht.begin();
  ds18b20.begin();
  Serial.printf("[DS18B20] Bulunan sensor sayisi: %d\n", ds18b20.getDeviceCount());

  WiFi.mode(WIFI_STA);                   // MAC adresini okumadan önce Wi-Fi'yi başlat
  uint8_t mac[6];
  WiFi.macAddress(mac);
  snprintf(cihazId, sizeof(cihazId), "esp32-zw-%02X%02X%02X", mac[3], mac[4], mac[5]);

  WiFi.setAutoReconnect(true);
  wifiBaglan();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setBufferSize(512);               // JSON 256 bayttan uzun olabilir
}

// ---------------- ANA DÖNGÜ ----------------
void loop() {
  mqttBaglan();   // Wi-Fi koparsa ESP32 kendisi yeniden bağlanır (setAutoReconnect)
  mqtt.loop();

  if (millis() - sonOlcum >= OLCUM_ARALIGI_MS) {
    sonOlcum = millis();
    olcVeGonder();
  }
}
