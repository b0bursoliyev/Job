-- ============================================================
-- Migration 002: malumotlar jadvali
-- Transport vositalari ma'lumotlarini saqlash uchun
-- ============================================================

CREATE TABLE IF NOT EXISTS malumotlar (
    id                  SERIAL PRIMARY KEY,
    mashina_raqami      VARCHAR(20) NOT NULL UNIQUE,
    joriy_lokatsiya     VARCHAR(255) NOT NULL,
    latitude            DECIMAL(10, 7),
    longitude           DECIMAL(10, 7),
    holat               VARCHAR(50) NOT NULL DEFAULT 'bosh'
                            CHECK (holat IN ('bosh', 'band', 'texnik')),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indekslar
CREATE INDEX IF NOT EXISTS idx_malumotlar_holat
    ON malumotlar (holat);

CREATE INDEX IF NOT EXISTS idx_malumotlar_joriy_lokatsiya
    ON malumotlar (joriy_lokatsiya);

CREATE INDEX IF NOT EXISTS idx_malumotlar_mashina_raqami
    ON malumotlar (mashina_raqami);

-- GPS koordinatalar uchun (PostGIS mavjud bo'lsa qo'shish mumkin)
-- CREATE INDEX IF NOT EXISTS idx_malumotlar_gps
--     ON malumotlar USING GIST (ST_MakePoint(longitude, latitude));

CREATE TRIGGER trg_malumotlar_updated_at
    BEFORE UPDATE ON malumotlar
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE malumotlar IS 'Transport vositalari (mashinalar) malumotlari';
COMMENT ON COLUMN malumotlar.mashina_raqami IS 'Davlat raqam belgisi (masalan: 01 A 1234)';
COMMENT ON COLUMN malumotlar.joriy_lokatsiya IS 'Hozirgi joylashuv (viloyat/shahar)';
COMMENT ON COLUMN malumotlar.latitude IS 'GPS kenglik koordinatasi';
COMMENT ON COLUMN malumotlar.longitude IS 'GPS uzunlik koordinatasi';
COMMENT ON COLUMN malumotlar.holat IS 'Mashina holati: bosh | band | texnik';

-- Boshlang'ich test ma'lumotlari (demo uchun)
INSERT INTO malumotlar (mashina_raqami, joriy_lokatsiya, latitude, longitude, holat)
VALUES
    ('01 A 1234', 'Toshkent sh., Toshkent', 41.2995, 69.2401, 'bosh'),
    ('01 B 5678', 'Chirchiq, Toshkent', 41.4686, 69.5823, 'bosh'),
    ('10 A 9012', 'Samarqand sh., Samarqand', 39.6542, 66.9597, 'bosh'),
    ('20 V 3456', 'Buxoro sh., Buxoro', 39.7674, 64.4556, 'bosh'),
    ('30 G 7890', 'Namangan sh., Namangan', 41.0011, 71.6728, 'bosh'),
    ('40 D 1234', 'Andijon sh., Andijon', 40.7829, 72.3441, 'bosh'),
    ('50 E 5678', 'Farg''ona sh., Farg''ona', 40.3842, 71.7843, 'bosh'),
    ('60 Zh 9012', 'Qarshi sh., Qashqadaryo', 38.8564, 65.7915, 'bosh'),
    ('70 Z 3456', 'Termiz sh., Surxondaryo', 37.2242, 67.2783, 'bosh'),
    ('80 I 7890', 'Urganch sh., Xorazm', 41.5500, 60.6333, 'bosh'),
    ('90 K 1234', 'Navoiy sh., Navoiy', 40.0843, 65.3791, 'bosh'),
    ('95 L 5678', 'Guliston sh., Sirdaryo', 40.4897, 68.7764, 'bosh'),
    ('97 M 9012', 'Jizzax sh., Jizzax', 40.1158, 67.8422, 'bosh'),
    ('01 N 4567', 'Nukus sh., Qoraqalpog''iston', 42.4602, 59.6102, 'bosh'),
    ('10 O 8901', 'Kattaqo''rg''on, Samarqand', 39.8997, 66.2590, 'bosh')
ON CONFLICT (mashina_raqami) DO NOTHING;
