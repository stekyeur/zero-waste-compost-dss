"""
Canlı kamera görüntüsünde organik / yabancı madde sınıflandırması.
Kamera kaynağı .env dosyasındaki KAMERA değişkeninden okunur (bkz. kamera.py).
"""
import cv2
import numpy as np
import tensorflow as tf
from kamera import kamera_ac

print("Yapay Zeka modeli yükleniyor...")
model = tf.keras.models.load_model("atik_siniflandirma_modeli.keras")

# Sınıf sırası eğitimdeki klasör sırasıyla aynıdır: 'O' (organik), 'R' (geri dönüştürülebilir)
kategoriler = ["Organik Gida (Komposta Uygun)", "YABANCI MADDE (Plastik/Cam)"]

cap = kamera_ac()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Kameradan görüntü alınamadı!")
        break

    # Model RGB görüntülerle eğitildi; OpenCV ise BGR verir -> RGB'ye çevir.
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = cv2.resize(rgb, (224, 224)).astype("float32")
    # NOT: Modelin ilk katmanı zaten Rescaling(1/255) içeriyor,
    # bu yüzden burada tekrar 255'e BÖLMÜYORUZ.
    img_array = np.expand_dims(img, axis=0)

    logits = model.predict(img_array, verbose=0)[0]
    olasiliklar = tf.nn.softmax(logits).numpy()
    sinif_index = int(np.argmax(olasiliklar))
    guven_skoru = olasiliklar[sinif_index] * 100

    etiket = f"{kategoriler[sinif_index]} (%{guven_skoru:.1f})"
    renk = (0, 255, 0) if sinif_index == 0 else (0, 0, 255)

    cv2.putText(frame, etiket, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, renk, 2)
    cv2.imshow("Kompost AI Kontrol (Cikis: Q)", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
