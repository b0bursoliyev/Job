# Yuk Tashish AI Matching Tizimi

**LangGraph + Ollama (Gemma 4) + PostgreSQL** asosidagi avtomatik yuk tashish matching tizimi.

---

## Arxitektura

```
┌─────────────────────────────────────────────────────────┐
│                  APScheduler (Fon xizmati)              │
│         Har 1–10 daqiqada yangi zapros yaratadi         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│               PostgreSQL (Ma'lumotlar bazasi)           │
│  ┌──────────────┐ ┌────────────────┐ ┌───────────────┐ │
│  │  zaproslar   │ │   malumotlar   │ │agent_takliflari│ │
│  │  (so'rovlar) │ │  (mashinalar)  │ │   (log/natija) │ │
│  └──────────────┘ └────────────────┘ └───────────────┘ │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph Matching Agent                   │
│                                                         │
│  zapros_olish → mashinalarni_qidirish → ai_baholash     │
│                                      → natijani_saqlash │
│                                                         │
│  (Ollama Gemma 4 orqali AI qaror)                    │
└─────────────────────────────────────────────────────────┘
```

---

## O'rnatish

### 1. Talablar

- Python 3.11+
- PostgreSQL 14+
- Ollama (local LLM server)

### 2. Muhit sozlash

```bash
# Virtual muhit
python -m venv venv
source venv/bin/activate        # Linux/Mac
# yoki
venv\Scripts\activate           # Windows

# Kutubxonalar
pip install -r requirements.txt
# yoki
pip install -e .
```

### 3. PostgreSQL sozlash

```sql
-- PostgreSQL ga kiring va DB yarating
CREATE DATABASE yuk_tashish_db;
CREATE USER yuk_user WITH PASSWORD 'parol123';
GRANT ALL PRIVILEGES ON DATABASE yuk_tashish_db TO yuk_user;
```

### 4. Ollama sozlash

```bash
# Ollama o'rnatish (Linux/macOS)
curl -fsSL https://ollama.com/install.sh | sh

# Model yuklash
ollama pull gemma4:12b

# Server ishga tushirish
ollama serve
```

### 5. .env fayl

```bash
cp .env.example .env
# .env faylni tahrirlang:
```

```env
DATABASE_URL=postgresql://yuk_user:parol123@localhost:5433/yuk_tashish_db
OLLAMA_BASE_URL=http://localhost:11434
AGENT_MODEL=gemma4:12b
ZAPROS_INTERVAL_MIN=1
ZAPROS_INTERVAL_MAX=10
```

---

## Ishga tushirish

```bash
# Migratsiya (jadvallarni yaratish)
python main.py --migrate

# Demo rejim (5 ta zapros, sinab ko'rish)
python main.py --demo

# Asosiy rejim (uzluksiz ishlaydi)
python main.py

# Statistika
python main.py --stats
```

---

## LangGraph Graf Sxemasi

```
START
  │
  ▼
[zapros_olish]
  │ xato? ──→ [xato_boshqarish] → END
  │
  ▼
[mashinalarni_qidirish]
  │ xato? ──→ [xato_boshqarish] → END
  │
  ▼
[ai_baholash]  ← OLLAMA GEMMA 4
  │ xato? ──→ [xato_boshqarish] → END
  │
  ▼
[natijani_saqlash]
  │
  ▼
 END
```

---

## Ma'lumotlar Bazasi Sxemasi

### zaproslar
| Ustun | Tur | Izoh |
|-------|-----|------|
| id | SERIAL PK | Avtomatik ID |
| yuk_ortish_joyi | VARCHAR(255) | Yuk ortish manzili |
| yuk_tushirish_joyi | VARCHAR(255) | Yuk tushirish manzili |
| yuklash_sanasi | DATE | Rejalashtirilgan sana |
| holat | VARCHAR(50) | pending / matched / cancelled |
| created_at | TIMESTAMPTZ | Yaratilgan vaqt |
| updated_at | TIMESTAMPTZ | Yangilangan vaqt |

### malumotlar
| Ustun | Tur | Izoh |
|-------|-----|------|
| id | SERIAL PK | Avtomatik ID |
| mashina_raqami | VARCHAR(20) UNIQUE | Davlat raqam belgisi |
| joriy_lokatsiya | VARCHAR(255) | Hozirgi joylashuv |
| latitude | DECIMAL(10,7) | GPS kenglik |
| longitude | DECIMAL(10,7) | GPS uzunlik |
| holat | VARCHAR(50) | bosh / band / texnik |

### agent_takliflari
| Ustun | Tur | Izoh |
|-------|-----|------|
| id | SERIAL PK | Avtomatik ID |
| zapros_id | FK | zaproslar.id |
| mashina_id | FK | malumotlar.id |
| mos_ball | INTEGER(0-100) | Matching aniqligi |
| agent_izohi | TEXT | AI izohi |
| zapros_yaratilgan_vaqti | TIMESTAMPTZ | Zapros vaqti |
| agent_taklif_bergan_vaqti | TIMESTAMPTZ | Taklif vaqti |
| kechikish_soniya | DECIMAL(8,3) | Latency (sek) |

---

## Foydali SQL So'rovlar

```sql
-- Bugungi zaproslar soni
SELECT COUNT(*) FROM zaproslar
WHERE DATE(created_at) = CURRENT_DATE;

-- Ulashtirilmagan zaproslar
SELECT * FROM zaproslar WHERE holat = 'pending'
ORDER BY created_at ASC;

-- Agent samaradorligi (view)
SELECT * FROM v_agent_samaradorlik LIMIT 7;

-- Eng yaxshi matching ballari
SELECT
  z.yuk_ortish_joyi,
  m.mashina_raqami,
  at2.mos_ball,
  at2.kechikish_soniya
FROM agent_takliflari at2
JOIN zaproslar z ON z.id = at2.zapros_id
JOIN malumotlar m ON m.id = at2.mashina_id
ORDER BY at2.mos_ball DESC
LIMIT 10;
```

---

## Testlar

```bash
# Unit testlar (DB siz)
python -m pytest tests/ -v -k "not integration"

# Integration testlar (real DB kerak)
python -m pytest tests/ -v -m integration
```

---

## Loyiha Strukturasi

```
yuk_tashish/
├── main.py                         # Asosiy kirish nuqtasi
├── requirements.txt                # Python kutubxonalari
├── .env.example                    # Muhit o'zgaruvchilari namunasi
├── config/
│   ├── __init__.py
│   └── database.py                 # PostgreSQL ulanish
├── migrations/
│   ├── 001_create_zaproslar.sql
│   ├── 002_create_malumotlar.sql
│   └── 003_create_agent_takliflari.sql
├── models/
│   ├── __init__.py
│   ├── zapros.py                   # Zaproslar modeli
│   ├── malumot.py                  # Malumotlar modeli
│   └── agent_taklif.py             # AgentTakliflari modeli
├── agents/
│   ├── __init__.py
│   └── matching_agent.py           # LangGraph AI Agent
├── services/
│   ├── __init__.py
│   └── zapros_generator.py         # Avtomatik zapros generator
└── tests/
    ├── __init__.py
    └── test_agent.py               # Unit va integration testlar
```
