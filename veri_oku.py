import cv2
import os

# Kaggle'dan indirdiğiniz fotoğrafların bulunduğu klasör yolu
dataset_klasoru = "dataset/kaggle_atiklar/TRAIN/O" 

# Klasör yoksa uyarı ver
if not os.path.exists(dataset_klasoru):
    print(f"Lütfen '{dataset_klasoru}' klasörünü oluşturup içine resimleri atın.")
else:
    # Klasördeki tüm dosyaları listele
    resim_dosyalari = os.listdir(dataset_klasoru)
    basarili_okunan = 0
    
    print(f"Toplam {len(resim_dosyalari)} dosya bulundu. Okuma başlıyor...")

    for dosya_adi in resim_dosyalari:
        # Sadece geçerli resim dosyalarını işle
        if dosya_adi.lower().endswith(('.png', '.jpg', '.jpeg')):
            dosya_yolu = os.path.join(dataset_klasoru, dosya_adi)
            
            # Resmi OpenCV ile oku (BGR formatında)
            resim = cv2.imread(dosya_yolu)
            
            if resim is not None:
                # Yapay zeka eğitimi için standart boyuta getir (Örn: 224x224 piksel)
                # Çoğu CNN (Convolutional Neural Network) modeli kare fotoğraf ister
                yeni_boyut = cv2.resize(resim, (224, 224))
                
                # Resmi ekranda hızlıca göster
                cv2.imshow("Kaggle Dataset Okuma (Cikis: Q)", yeni_boyut)
                basarili_okunan += 1
                
                # Slayt gösterisi gibi geçmesi için 100ms bekle (0 yazarsanız tuş bekler)
                if cv2.waitKey(100) & 0xFF == ord('q'):
                    print("İşlem kullanıcı tarafından durduruldu.")
                    break
            else:
                print(f"Okuma hatası (Bozuk dosya): {dosya_adi}")
                
    print(f"İşlem bitti. {basarili_okunan} resim başarıyla işlendi ve boyutu eşitlendi.")
    cv2.destroyAllWindows()