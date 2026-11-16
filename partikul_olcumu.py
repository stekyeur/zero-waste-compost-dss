import cv2
import numpy as np

# OpenCV 4.7+ uyumlu ArUco tanımlamaları
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

# Telefonunuzdan açtığınız ArUco marker'ın fiziksel boyutu (mm)
MARKER_SIZE_MM = 30.0 

cap = cv2.VideoCapture(0) # 0, varsayılan web kamerasıdır

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)
    
    pixels_per_mm = None
    
    # Eğer ArUco marker tespit edildiyse oran hesapla
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        
        c = corners[0][0]
        pixel_width = np.linalg.norm(c[0] - c[1])
        pixels_per_mm = pixel_width / MARKER_SIZE_MM
        
        cv2.putText(frame, f"Kalibrasyon: {pixels_per_mm:.2f} px/mm", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    else:
        cv2.putText(frame, "ArUco Marker Bekleniyor...", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Kalibrasyon sağlandıysa diğer nesneleri ölç
    if pixels_per_mm is not None:
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        # Koyu arka plan üzerinde açık renkli nesneler için eşikleme
        _, thresh = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY_INV)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 1000:  # Çok küçük gürültüleri yoksay
                rect = cv2.minAreaRect(cnt)
                box = cv2.boxPoints(rect)
                box = np.int32(box)
                
                (w_pix, h_pix) = rect[1]
                if w_pix > 0 and h_pix > 0:
                    w_mm = w_pix / pixels_per_mm
                    h_mm = h_pix / pixels_per_mm
                    
                    # ArUco marker'ın kendisini ölçmemek için filtre
                    if abs(w_mm - MARKER_SIZE_MM) < 5 and abs(h_mm - MARKER_SIZE_MM) < 5:
                        continue
                        
                    # Kompost Tebliği 10 mm sınırı kontrolü
                    max_dim = max(w_mm, h_mm)
                    color = (0, 255, 0) if max_dim <= 10.0 else (0, 0, 255)
                    durum = "UYGUN" if max_dim <= 10.0 else "PARCALANMALI"
                    
                    cv2.drawContours(frame, [box], 0, color, 2)
                    cv2.putText(frame, f"{max_dim:.1f}mm - {durum}", 
                                (box[0][0], box[0][1] - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.imshow("Partikul Boyutu Analizi (10 mm Kriteri)", frame)
    
    # Çıkmak için 'q' tuşuna basın
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()