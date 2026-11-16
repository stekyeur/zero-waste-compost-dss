import cv2
import numpy as np

# --- KAMERA AYARLARI ---
# 0: Dahili kamera veya ilk bağlanan USB kamera
cap = cv2.VideoCapture(1)  # 1, ikinci bağlanan USB kamera olabilir. Kameranızın numarasını kontrol edin.
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# --- KALİBRASYON ÇARPANI ---
# 1 mm'nin kaç piksele denk geldiğini buraya yazıyoruz.
# ÖNEMLİ: Kamerayı 25-30 cm'e sabitledikten sonra bir cetvel veya madeni para ile bu değeri güncellemelisiniz.
PIKSEL_PER_MM = 12.0  # Şimdilik tahmini başlangıç değeri

print("Kamera açılıyor... Çıkmak için 'q' tuşuna basın.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Kameradan görüntü alınamadı!")
        break

    # 1. Görüntüyü ön işleme hazırla (Gri tonlama ve Bulanıklaştırma)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # 2. Kenarları tespit et (Canny Algoritması)
    edged = cv2.Canny(blurred, 50, 150)
    
    # Kırıkları birleştirmek için kalınlaştırma ve inceltme
    edged = cv2.dilate(edged, None, iterations=1)
    edged = cv2.erode(edged, None, iterations=1)

    # 3. Şekillerin sınırlarını (Konturları) bul
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        # Arka plandaki çok küçük gölgeleri veya tozları (gürültüyü) yoksay
        if cv2.contourArea(c) < 200:
            continue

        # Sınırlayıcı dikdörtgeni oluştur
        x, y, w, h = cv2.boundingRect(c)
        
        # Pikselleri gerçek milimetreye dönüştür
        w_mm = w / PIKSEL_PER_MM
        h_mm = h / PIKSEL_PER_MM
        
        # Atığın en uzun kenarını baz al
        max_boyut_mm = max(w_mm, h_mm)

        # 4. 10 mm sınırına göre sınıflandır
        if max_boyut_mm <= 10.0:
            renk = (0, 255, 0) # Yeşil (Kompost için uygun)
            etiket = f"UYGUN: {max_boyut_mm:.1f}mm"
        else:
            renk = (0, 0, 255) # Kırmızı (Çok büyük, parçalanmalı)
            etiket = f"BUYUK: {max_boyut_mm:.1f}mm"

        # Çerçeveyi ve metni ekrana çiz
        cv2.rectangle(frame, (x, y), (x + w, y + h), renk, 2)
        cv2.putText(frame, etiket, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, renk, 2)

    # İşlenmiş görüntüyü ekranda göster
    cv2.imshow("Tubitak ZeroWaste - 10mm Atik Kontrolu", frame)

    # 'q' tuşuna basarak döngüyü sonlandır
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()