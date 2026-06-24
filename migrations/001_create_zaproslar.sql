-- ============================================================
-- Migration 001: zaproslar jadvali
-- Yuk tashish zaproslarini saqlash uchun
-- ============================================================

CREATE TABLE IF NOT EXISTS zaproslar (
    id              SERIAL PRIMARY KEY,
    yuk_ortish_joyi  VARCHAR(255) NOT NULL,
    yuk_tushirish_joyi VARCHAR(255) NOT NULL,
    yuklash_sanasi   DATE NOT NULL,
    holat            VARCHAR(50) NOT NULL DEFAULT 'pending'
                        CHECK (holat IN ('pending', 'matched', 'cancelled')),
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indekslar (tez qidirish uchun)
CREATE INDEX IF NOT EXISTS idx_zaproslar_holat
    ON zaproslar (holat);

CREATE INDEX IF NOT EXISTS idx_zaproslar_yuk_ortish_joyi
    ON zaproslar (yuk_ortish_joyi);

CREATE INDEX IF NOT EXISTS idx_zaproslar_created_at
    ON zaproslar (created_at DESC);

-- updated_at ni avtomatik yangilash uchun trigger funksiyasi
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_zaproslar_updated_at
    BEFORE UPDATE ON zaproslar
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE zaproslar IS 'Yuk tashish zaproslarini saqlaydi';
COMMENT ON COLUMN zaproslar.yuk_ortish_joyi IS 'Yukning ortish manzili';
COMMENT ON COLUMN zaproslar.yuk_tushirish_joyi IS 'Yukning tushirish manzili';
COMMENT ON COLUMN zaproslar.yuklash_sanasi IS 'Yuklash rejalashtirilgan sana';
COMMENT ON COLUMN zaproslar.holat IS 'Zapros holati: pending | matched | cancelled';
