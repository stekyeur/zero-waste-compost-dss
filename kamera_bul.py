"""
Bilgisayardaki kameraları sırayla dener ve hangi numaranın hangi kamera olduğunu gösterir.
DroidCam'in numarasını bulduktan sonra .env dosyasına  KAMERA=<numara>  yazın.

Kullanım:  python kamera_bul.py
Her pencerede herhangi bir tuşa basınca bir sonraki kameraya geçer.
"""
import os
import cv2

arka_uc = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
bulunanlar = []

for i in range(6):
    cap = cv2.VideoCapture(i, arka_uc)
    if not cap.isOpened():
        continue
    ok, frame = cap.read()
    if ok and frame is not None:
        h, w = frame.shape[:2]
        bulunanlar.append(i)
        print(f"Kamera {i}: çalışıyor ({w}x{h})")
        cv2.putText(frame, f"KAMERA={i}  (devam icin bir tusa basin)", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.imshow(f"Kamera {i}", frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    cap.release()

if bulunanlar:
    print(f"\nÇalışan kameralar: {bulunanlar}")
    print("DroidCam görüntüsünü gösteren numarayı .env dosyasına yazın, örn:  KAMERA=1")
else:
    print("Hiç kamera bulunamadı. DroidCam Client açık ve telefon bağlı mı?")
