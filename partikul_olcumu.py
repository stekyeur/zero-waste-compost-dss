"""
ArUco marker ile kalibre edilmiş partikül boyutu ölçümü (10 mm kriteri).

Kullanım:
    python partikul_olcumu.py                    # canlı kamera (KAMERA değeri .env'den)
    python partikul_olcumu.py --foto resim.jpg   # kayıtlı bir fotoğrafı ölç

Tuşlar:  S = görüntüyü ve ölçüm sonuçlarını "olcumler/" klasörüne kaydet,  Q = çıkış

Düzenek:
    - ArUco marker'ı (DICT_4X4_50) kağıda GERÇEK BOYUTTA yazdırın, cetvelle 30 mm olduğunu doğrulayın.
    - Marker ve atık parçaları aynı düz zeminde olsun (ör. beyaz A4 kağıt).
    - Telefonu masaya paralel tutun ve tepeden çekin.
"""
import argparse
import csv
import os
import time

import cv2
import numpy as np

# ---------------- AYARLAR ----------------
MARKER_SIZE_MM = 30.0     # Yazdırılan marker'ın cetvelle ölçülen kenar uzunluğu
SINIR_MM = 10.0           # Kompost için izin verilen en büyük parça boyutu
MIN_ALAN_MM2 = 2.0        # Bundan küçük lekeler gürültü sayılır
ARKA_PLAN = "acik"        # "acik": beyaz zemin + koyu parçalar | "koyu": koyu zemin + açık parçalar
ALT_YOK_SAY_ORAN = 0.0    # DroidCam filigranı ölçüme karışırsa 0.12 yapın (görüntünün alt %12'si yok sayılır)
EGIM_UYARI_ORANI = 1.08   # Marker kenarları arasındaki fark bundan büyükse "telefon eğik" uyarısı
KAYIT_KLASORU = "olcumler"

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
detector = cv2.aruco.ArucoDetector(aruco_dict, cv2.aruco.DetectorParameters())

YESIL, KIRMIZI, SARI, CAMGOBEGI = (0, 200, 0), (0, 0, 255), (0, 255, 255), (255, 255, 0)


def kalibrasyon(gray):
    """ArUco marker'dan piksel/mm oranını hesaplar. Bulamazsa (None, None, None) döner."""
    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None:
        return None, None, None
    kose = corners[0][0]                                   # 4 köşe (x, y)
    kenarlar = [np.linalg.norm(kose[i] - kose[(i + 1) % 4]) for i in range(4)]
    ppm = float(np.mean(kenarlar)) / MARKER_SIZE_MM        # 4 kenarın ortalaması
    egim = max(kenarlar) / min(kenarlar)
    return ppm, kose, egim


def olc(frame):
    """Bir kareyi ölçer. (işaretlenmiş görüntü, px/mm, parça listesi) döndürür."""
    out = frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ppm, kose, egim = kalibrasyon(gray)

    if ppm is None:
        cv2.putText(out, "ArUco marker bekleniyor...", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, KIRMIZI, 2)
        return out, None, []

    cv2.polylines(out, [kose.astype(np.int32)], True, CAMGOBEGI, 2)

    # 1) Parçaları zeminden ayır (Otsu eşikleme ışığa göre kendini ayarlar)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    tip = cv2.THRESH_BINARY_INV if ARKA_PLAN == "acik" else cv2.THRESH_BINARY
    _, maske = cv2.threshold(blurred, 0, 255, tip + cv2.THRESH_OTSU)
    maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    # 2) Marker'ın kendisini ölçme: marker bölgesini maskeden sil
    marker_bolgesi = np.zeros_like(maske)
    cv2.fillConvexPoly(marker_bolgesi, kose.astype(np.int32), 255)
    marker_bolgesi = cv2.dilate(marker_bolgesi, np.ones((15, 15), np.uint8))
    maske[marker_bolgesi > 0] = 0
    if ALT_YOK_SAY_ORAN > 0:
        maske[int(maske.shape[0] * (1 - ALT_YOK_SAY_ORAN)):, :] = 0

    # 3) Konturları bul ve ölç
    konturlar, _ = cv2.findContours(maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H, W = maske.shape
    min_alan_px = MIN_ALAN_MM2 * ppm * ppm
    parcalar = []

    for cnt in konturlar:
        if cv2.contourArea(cnt) < min_alan_px:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        if x <= 1 or y <= 1 or x + w >= W - 1 or y + h >= H - 1:
            continue                    # görüntü kenarına değen şeyler (kağıt kenarı, masa) ölçülmez

        rect = cv2.minAreaRect(cnt)
        (w_px, h_px) = rect[1]
        uzun_mm = max(w_px, h_px) / ppm
        kisa_mm = min(w_px, h_px) / ppm
        uygun = uzun_mm <= SINIR_MM
        renk = YESIL if uygun else KIRMIZI

        kutu = np.int32(cv2.boxPoints(rect))
        cv2.drawContours(out, [kutu], 0, renk, 2)
        etiket = f"{uzun_mm:.1f}mm {'UYGUN' if uygun else 'PARCALANMALI'}"
        cv2.putText(out, etiket, (int(kutu[:, 0].min()), int(kutu[:, 1].min()) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, renk, 2)

        parcalar.append({
            "parca_no": len(parcalar) + 1,
            "uzun_kenar_mm": round(uzun_mm, 2),
            "kisa_kenar_mm": round(kisa_mm, 2),
            "alan_mm2": round(cv2.contourArea(cnt) / (ppm * ppm), 1),
            "uygun": uygun,
        })

    # 4) Özet
    n = len(parcalar)
    n_uygun = sum(p["uygun"] for p in parcalar)
    ozet = f"Kalibrasyon: {ppm:.2f} px/mm | Parca: {n} | 10 mm alti: {n_uygun}/{n}"
    cv2.putText(out, ozet, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, CAMGOBEGI, 2)
    if egim > EGIM_UYARI_ORANI:
        cv2.putText(out, "UYARI: Telefon egik, masaya paralel tutun", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, SARI, 2)
    return out, ppm, parcalar


def kaydet(ham, isaretli, ppm, parcalar):
    """Ham ve işaretli görüntüyü + ölçüm tablosunu (CSV) kaydeder."""
    os.makedirs(KAYIT_KLASORU, exist_ok=True)
    zaman = time.strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(os.path.join(KAYIT_KLASORU, f"{zaman}_ham.jpg"), ham)
    cv2.imwrite(os.path.join(KAYIT_KLASORU, f"{zaman}_olcum.jpg"), isaretli)
    csv_yolu = os.path.join(KAYIT_KLASORU, f"{zaman}_olcum.csv")
    with open(csv_yolu, "w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=["parca_no", "uzun_kenar_mm", "kisa_kenar_mm",
                                               "alan_mm2", "uygun", "px_per_mm"])
        yazici.writeheader()
        for p in parcalar:
            yazici.writerow({**p, "px_per_mm": round(ppm, 3) if ppm else ""})
    print(f"[KAYIT] {zaman}: {len(parcalar)} parça -> {csv_yolu}")


def main():
    ap = argparse.ArgumentParser(description="ArUco kalibrasyonlu partikül boyutu ölçümü")
    ap.add_argument("--foto", help="Canlı kamera yerine bu fotoğrafı ölç")
    args = ap.parse_args()
    pencere = "Partikul Boyutu Analizi (S: kaydet, Q: cikis)"

    if args.foto:
        frame = cv2.imread(args.foto)
        if frame is None:
            raise SystemExit(f"Fotoğraf okunamadı: {args.foto} (iPhone HEIC ise JPEG'e çevirin)")
        out, ppm, parcalar = olc(frame)
        for p in parcalar:
            print(p)
        cv2.imshow(pencere, out)
        if cv2.waitKey(0) & 0xFF == ord("s"):
            kaydet(frame, out, ppm, parcalar)
        cv2.destroyAllWindows()
        return

    from kamera import kamera_ac
    cap = kamera_ac()
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Kameradan görüntü alınamadı!")
            break
        out, ppm, parcalar = olc(frame)
        cv2.imshow(pencere, out)
        tus = cv2.waitKey(1) & 0xFF
        if tus == ord("s"):
            kaydet(frame, out, ppm, parcalar)
        elif tus == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
