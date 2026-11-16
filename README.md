# Zero Food Waste & Compost Decision Support System

An IoT and computer-vision system that monitors food waste on its way to composting. Sensor
readings (temperature, moisture, pH, gas) and camera-based checks of the waste itself are
collected into one cloud database, which will feed a decision support layer for compost quality.

> **Status: in progress.** Course project for the Internet of Things course at Dokuz Eylül
> University. See [Roadmap](#roadmap) for what is done and what is next.

## How it works

```
Sensor node (ESP32) ──MQTT──▶ Raspberry Pi 4 gateway ──▶ Supabase (PostgreSQL)
                                     ▲
Camera ──▶ OpenCV + CNN (organic / foreign material, particle size)
```

Two data streams meet on the Raspberry Pi:

- **Sensor stream.** The sensor node publishes JSON readings to the MQTT topic
  `kompost/sensorler`. A listener on the Pi writes each reading to the `kompost_olcumleri`
  table in Supabase.
- **Vision stream.** A camera looks at the shredded waste. A CNN classifies each frame as
  organic or foreign material (plastic, glass), and an OpenCV contour pipeline checks whether
  particles are within the 10 mm size limit for composting.

## Repository contents

| File | What it does |
|---|---|
| `esp32_simulator.py` | Simulates the sensor node: publishes random but realistic readings over MQTT every 3 s, so the pipeline can be tested without hardware |
| `pi_dinleyici.py` | Gateway: subscribes to the MQTT topic and inserts readings into Supabase |
| `mqtt_dinleyici.py` | Gateway variant for the real ESP32 payload (raw sensor values mapped to the table schema) |
| `ai_veri_hazirla.py` | Loads the image dataset in batches, builds and trains the CNN (TensorFlow/Keras), saves `atik_siniflandirma_modeli.keras` |
| `canli_test.py` | Live camera inference with the trained model, with on-screen label and confidence |
| `boyut_analizi.py` | Live particle size check: Canny edges → contours → bounding boxes → mm conversion → 10 mm threshold |
| `veri_topla.py` | Captures labelled photos from the camera to build a project-specific dataset |
| `veri_oku.py` | Previews and resizes dataset images to 224×224 |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux / Raspberry Pi OS: source .venv/bin/activate
pip install -r requirements.txt
```

1. **Supabase.** Copy `.env.example` to `.env` and fill in your project URL and anon key.
2. **MQTT broker.** Install and start Mosquitto (default port 1883). Set the broker address at
   the top of the listener scripts if it is not running on the same machine.
3. **Dataset.** The training images are not included in the repository. Place a waste
   classification dataset with one folder per class under `dataset/kaggle_atiklar/TRAIN/`
   (this project uses a Kaggle dataset with `O` = organic and `R` = recyclable classes).
4. **Model.** The trained model file (~77 MB) is not included either. Run
   `python ai_veri_hazirla.py` to train it.

## Running

```bash
# Sensor stream, without hardware
python esp32_simulator.py        # terminal 1
python pi_dinleyici.py           # terminal 2

# Vision stream
python canli_test.py             # organic vs. foreign material
python boyut_analizi.py          # 10 mm particle size check
```

## Roadmap

- [x] Supabase schema and MQTT → Supabase gateway
- [x] CNN classifier trained on a public waste dataset, live camera inference
- [x] Contour-based particle size check with a fixed pixel-per-mm calibration
- [ ] ESP32 firmware for the physical sensor node (temperature, moisture, pH, gas)
- [ ] ArUco-marker calibration to replace the fixed pixel-per-mm constant
- [ ] Linking sensor and vision results per sample in the database
- [ ] Rule-based compost decision engine and dashboard

## Tech stack

Python · OpenCV · TensorFlow/Keras · MQTT (Mosquitto, paho-mqtt) · Supabase · Raspberry Pi 4 · ESP32
