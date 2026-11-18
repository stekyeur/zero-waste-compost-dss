-- =============================================================
--  ZeroWaste - kompost_olcumleri tablosu güncellemesi
--  Supabase panel > SQL Editor > New query > bu dosyanın içeriğini yapıştırıp "Run".
--  Birden fazla çalıştırmak zararsızdır.
-- =============================================================

-- ESP32'nin yeni gönderdiği alanlar için sütunlar
alter table public.kompost_olcumleri
  add column if not exists olcum_zamani  timestamptz,
  add column if not exists cihaz         text,
  add column if not exists olcum_no      integer,
  add column if not exists sicaklik_hava real,      -- DHT11 hava sıcaklığı (°C)
  add column if not exists nem_hava      real,      -- DHT11 bağıl nem (%)
  add column if not exists nem_ham       integer,   -- toprak nemi ham ADC (0-4095)
  add column if not exists gaz_ham       integer,   -- MQ135 ham ADC
  add column if not exists gaz_mv        integer,   -- MQ135 çıkış gerilimi (mV)
  add column if not exists ph_ham        integer,   -- pH modülü ham ADC
  add column if not exists ph_mv         integer;   -- pH modülü çıkış gerilimi (mV)

-- Henüz ölçülmeyen alanlar (tartım, görüntü işleme, kalibrasyon bekleyenler) boş kalabilsin
alter table public.kompost_olcumleri
  alter column bilesen_sinifi        drop not null,
  alter column kutle                 drop not null,
  alter column sicaklik              drop not null,
  alter column nem                   drop not null,
  alter column co2                   drop not null,
  alter column nh3                   drop not null,
  alter column ph                    drop not null,
  alter column c_n_orani             drop not null,
  alter column partikul_boyutu       drop not null,
  alter column uygulanan_formulasyon drop not null;

-- Kontrol: tablonun güncel sütunlarını listele
select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public' and table_name = 'kompost_olcumleri'
order by ordinal_position;
