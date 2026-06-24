-- ============================================================
-- Migration 003: agent_takliflari jadvali
-- AI agent tavsiyalari va ishlash logi
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_takliflari (
    id                      SERIAL PRIMARY KEY,
    zapros_id               INTEGER NOT NULL
                                REFERENCES zaproslar(id)
                                ON DELETE CASCADE,
    mashina_id              INTEGER NOT NULL
                                REFERENCES malumotlar(id)
                                ON DELETE CASCADE,
    mos_ball                INTEGER NOT NULL DEFAULT 0
                                CHECK (mos_ball BETWEEN 0 AND 100),
    agent_izohi             TEXT,
    zapros_yaratilgan_vaqti TIMESTAMP WITH TIME ZONE NOT NULL,
    agent_taklif_bergan_vaqti TIMESTAMP WITH TIME ZONE NOT NULL,
    kechikish_soniya        DECIMAL(8, 3),  -- Latency (soniya)
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Bir zapros uchun bir mashina faqat bir marta tavsiya qilinishi
    UNIQUE (zapros_id, mashina_id)
);

-- Indekslar
CREATE INDEX IF NOT EXISTS idx_agent_takliflari_zapros_id
    ON agent_takliflari (zapros_id);

CREATE INDEX IF NOT EXISTS idx_agent_takliflari_mashina_id
    ON agent_takliflari (mashina_id);

CREATE INDEX IF NOT EXISTS idx_agent_takliflari_mos_ball
    ON agent_takliflari (mos_ball DESC);

CREATE INDEX IF NOT EXISTS idx_agent_takliflari_kechikish
    ON agent_takliflari (kechikish_soniya);

CREATE INDEX IF NOT EXISTS idx_agent_takliflari_created_at
    ON agent_takliflari (created_at DESC);

CREATE TRIGGER trg_agent_takliflari_updated_at
    BEFORE UPDATE ON agent_takliflari
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE agent_takliflari IS 'AI agent matching tavsiyalari va ishlash logi';
COMMENT ON COLUMN agent_takliflari.zapros_id IS 'Tavsiya berilgan zapros ID si';
COMMENT ON COLUMN agent_takliflari.mashina_id IS 'Tavsiya qilingan mashina ID si';
COMMENT ON COLUMN agent_takliflari.mos_ball IS 'Matching aniqligi bali (0-100)';
COMMENT ON COLUMN agent_takliflari.agent_izohi IS 'Agent bergan batafsil izoh';
COMMENT ON COLUMN agent_takliflari.zapros_yaratilgan_vaqti IS 'Zapros qachon yaratilgani';
COMMENT ON COLUMN agent_takliflari.agent_taklif_bergan_vaqti IS 'Agent qachon tavsiya bergani';
COMMENT ON COLUMN agent_takliflari.kechikish_soniya IS 'Zaprosdan javobgacha ketgan vaqt (soniya)';

-- Analitika uchun View
CREATE OR REPLACE VIEW v_agent_samaradorlik AS
SELECT
    DATE(at2.created_at)                        AS sana,
    COUNT(*)                                     AS jami_takliflar,
    ROUND(AVG(at2.mos_ball), 2)                  AS ortacha_ball,
    ROUND(AVG(at2.kechikish_soniya), 3)          AS ortacha_kechikish,
    MIN(at2.kechikish_soniya)                    AS eng_tez,
    MAX(at2.kechikish_soniya)                    AS eng_sekin,
    COUNT(CASE WHEN at2.mos_ball >= 80 THEN 1 END) AS yuqori_moslik,
    COUNT(CASE WHEN at2.mos_ball < 50 THEN 1 END)  AS past_moslik
FROM agent_takliflari at2
GROUP BY DATE(at2.created_at)
ORDER BY sana DESC;

COMMENT ON VIEW v_agent_samaradorlik IS 'Agent kunlik samaradorligi statistikasi';
