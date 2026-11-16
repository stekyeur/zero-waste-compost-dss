import tensorflow as tf

dataset_yolu = "dataset/kaggle_atiklar/TRAIN"
batch_size = 32 # Modele tek seferde gönderilecek fotoğraf sayısı
img_boyutu = (224, 224)

print("Veri seti diskten parça parça (batch) okunacak şekilde ayarlanıyor...")

# Eğitim veriseti (Tüm verinin %80'i)
train_ds = tf.keras.utils.image_dataset_from_directory(
    dataset_yolu,
    validation_split=0.2, # %20'sini test için ayırıyoruz
    subset="training",
    seed=123, # Rastgelelik tohumu (tekrar edilebilir sonuçlar için)
    image_size=img_boyutu,
    batch_size=batch_size
)

# Doğrulama (Validation) veriseti (Tüm verinin %20'si)
val_ds = tf.keras.utils.image_dataset_from_directory(
    dataset_yolu,
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=img_boyutu,
    batch_size=batch_size
)

class_names = train_ds.class_names
print(f"Bulunan Sınıflar (Kategoriler): {class_names}")

# Performans optimizasyonu: Veri okunurken bir sonraki batch'i arka planda hazırla
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

print("RAM sorunu çözüldü! Veriler Yapay Zeka eğitimine girmek için hazır.")

from tensorflow.keras import layers, models

# 1. Yapa Zeka (CNN) Modelinin Mimarisini Kuruyoruz
print("CNN Modeli inşa ediliyor...")

num_classes = len(class_names) # 2 sınıfımız var: 'O' ve 'R'

model = models.Sequential([
  # Görüntü piksellerini 0-1 arasına çekme (Normalizasyon)
  layers.Rescaling(1./255, input_shape=(224, 224, 3)),
  
  # 1. Evrişim (Convolution) Katmanı: Görüntüdeki temel hatları (kenar, köşe) öğrenir
  layers.Conv2D(16, 3, padding='same', activation='relu'),
  layers.MaxPooling2D(),
  
  # 2. Evrişim Katmanı: Daha karmaşık dokuları öğrenir
  layers.Conv2D(32, 3, padding='same', activation='relu'),
  layers.MaxPooling2D(),
  
  # 3. Evrişim Katmanı: Nesnenin parçalarını tanımaya başlar
  layers.Conv2D(64, 3, padding='same', activation='relu'),
  layers.MaxPooling2D(),
  
  # Düzleştirme (Flatten): 2 boyutlu matrisleri tek boyutlu diziye çevirir
  layers.Flatten(),
  
  # Tam Bağlı (Dense) Katman: Öğrenilen özellikleri karar mekanizmasına iletir
  layers.Dense(128, activation='relu'),
  
  # Çıkış Katmanı: 2 nöron (Organik veya Geri Dönüştürülebilir kararını verir)
  layers.Dense(num_classes)
])

# 2. Modeli Derleme (Hangi yöntemle öğreneceğini seçme)
model.compile(optimizer='adam',
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])

# Modelin yapısını terminale yazdır
model.summary()

# 3. Modeli Eğitme
print("\n--- EĞİTİM BAŞLIYOR ---")
print("Not: CPU kullandığınız için her bir döngü (epoch) bilgisayarınızın hızına göre birkaç dakika sürebilir.")

epochs = 5 # Modeli veriler üzerinden 5 kez geçireceğiz (İleride artırılabilir)
history = model.fit(
  train_ds,
  validation_data=val_ds,
  epochs=epochs
)

# 4. Eğitilen Modeli Diske Kaydetme
model.save('atik_siniflandirma_modeli.keras')
print("\nBaşarılı! Model eğitildi ve 'atik_siniflandirma_modeli.keras' adıyla projenize kaydedildi.")