import cv2
import os

# Fotoğrafların kaydedileceği klasör
kayit_klasoru = "dataset/uygun_boyut" # Büyük parçaları çekerken burayı "dataset/buyuk_parca" yapın
os.makedirs(kayit_klasoru, exist_ok=True)

# 0, varsayılan web kamerasını temsil eder
cap = cv2.VideoCapture(0)
sayac = 0

print("Fotoğraf çekmek için 's' tuşuna, çıkmak için 'q' tuşuna basın.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Kameradan görüntü alınamıyor!")
        break

    cv2.imshow("Veri Toplama (S: Kaydet, Q: Cikis)", frame)

    # Klavyeden basılan tuşu dinle
    tus = cv2.waitKey(1) & 0xFF

    if tus == ord('s'):
        dosya_adi = os.path.join(kayit_klasoru, f"atik_{sayac}.jpg")
        cv2.imwrite(dosya_adi, frame)
        print(f"Kaydedildi: {dosya_adi}")
        sayac += 1
    elif tus == ord('q'):
        break

# Kamera bağlantısını kes ve pencereleri kapat
cap.release()
cv2.destroyAllWindows()