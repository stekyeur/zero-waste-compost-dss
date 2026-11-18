"""
Ortak kamera açma yardımcısı.

Kamera kaynağı .env dosyasındaki KAMERA değişkeninden okunur:
    KAMERA=1                               -> USB / sanal webcam (DroidCam Client) numarası
    KAMERA=http://172.20.10.1:4747/video   -> ağ üzerinden video akışı (URL)

Hangi numaranın DroidCam olduğunu bulmak için:  python kamera_bul.py
"""
import os
import cv2
from dotenv import load_dotenv

load_dotenv()


def kamera_ac(kaynak=None, genislik=1280, yukseklik=720):
    """Kamerayı açar ve cv2.VideoCapture nesnesini döndürür."""
    if kaynak is None:
        kaynak = os.getenv("KAMERA", "0")
    kaynak = str(kaynak).strip()

    if kaynak.isdigit():
        # Windows'ta DirectShow, sanal kameraları (DroidCam) daha hızlı ve güvenilir açar
        arka_uc = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
        cap = cv2.VideoCapture(int(kaynak), arka_uc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, genislik)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, yukseklik)
    else:
        cap = cv2.VideoCapture(kaynak)   # URL akışı

    if not cap.isOpened():
        raise RuntimeError(
            f"Kamera açılamadı (KAMERA={kaynak}). "
            "DroidCam Client açık mı? Doğru numarayı bulmak için: python kamera_bul.py"
        )
    gercek_g = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    gercek_y = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[Kamera] Kaynak: {kaynak}  |  Çözünürlük: {gercek_g}x{gercek_y}")
    return cap
