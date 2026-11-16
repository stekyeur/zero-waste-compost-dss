import cv2
import numpy as np
import tensorflow as tf

# Eğitilen modeli belleğe yükle
print("Yapay Zeka modeli yükleniyor...")
model = tf.keras.models.load_model('atik_siniflandirma_modeli.keras')

# Sınıflar (0: Organik, 1: Geri Dönüştürülebilir)
kategoriler = ["Organik Gida (Komposta Uygun)", "YABANCI MADDE (Plastik/Cam)"]

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Görüntüyü AI modelinin beklediği 224x224 boyutuna ve formata getir
    img = cv2.resize(frame, (224, 224))
    img_array = np.expand_dims(img, axis=0) / 255.0 # Normalizasyon ve Batch boyutu ekleme

    # Tahmin yap
    tahminler = model.predict(img_array, verbose=0)
    sinif_index = np.argmax(tahminler[0])
    
    # Güven skorunu hesapla (Softmax)
    guven_skoru = tf.nn.softmax(tahminler[0])[sinif_index].numpy() * 100

    # Ekrana sonuçları yazdır (Organik ise Yeşil, değilse Kırmızı)
    etiket = f"{kategoriler[sinif_index]} (%{guven_skoru:.1f})"
    renk = (0, 255, 0) if sinif_index == 0 else (0, 0, 255)
    
    cv2.putText(frame, etiket, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, renk, 2)
    cv2.imshow("Kompost AI Kontrol (Cikis: Q)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()