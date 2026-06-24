"""
Yuk Tashish AI Matching Tizimi — Asosiy kirish nuqtasi.

Ishga tushirish:
    python main.py                    # Oddiy rejim
    python main.py --demo             # Demo: 5 ta zapros yaratib sinab ko'rish
    python main.py --migrate          # Faqat migratsiya
    python main.py --stats            # Statistika ko'rish
"""

import os
import sys
import time
import signal
import logging
import argparse
from datetime import datetime, date, timedelta
import random

from dotenv import load_dotenv

load_dotenv()

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("yuk_tashish.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║       Yuk Tashish AI Matching Tizimi                        ║
║       LangGraph + Claude AI + PostgreSQL                    ║
╚══════════════════════════════════════════════════════════════╝
""")


def migratsiya_qil():
    """Barcha jadvallarni yaratadi."""
    from config.database import init_db, engine
    import psycopg2
    from urllib.parse import urlparse

    logger.info("Migratsiya boshlanmoqda...")
    try:
        init_db()
        logger.info("✓ Barcha jadvallar yaratildi (SQLAlchemy ORM)")

        # SQL migratsiya fayllarini ham ishga tushiramiz
        db_url = os.getenv("DATABASE_URL", "")
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
        )
        cursor = conn.cursor()

        migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
        sql_fayllar = sorted([
            f for f in os.listdir(migration_dir)
            if f.endswith(".sql")
        ])

        for fayl in sql_fayllar:
            fayl_yoli = os.path.join(migration_dir, fayl)
            with open(fayl_yoli, "r", encoding="utf-8") as f:
                sql = f.read()
            try:
                cursor.execute(sql)
                conn.commit()
                logger.info(f"✓ {fayl} bajarildi")
            except Exception as e:
                conn.rollback()
                logger.warning(f"  {fayl} — {e} (o'tkazib yuborildi)")

        cursor.close()
        conn.close()
        logger.info("✓ Migratsiya muvaffaqiyatli yakunlandi!")

    except Exception as e:
        logger.error(f"✗ Migratsiya xatosi: {e}")
        raise


def demo_rejim():
    """Demo: bir necha zapros yaratib agentni sinab ko'radi."""
    from config.database import SessionLocal, init_db
    from models.zapros import Zapros
    from agents.matching_agent import zapros_uchun_taklif_ber

    logger.info("Demo rejim boshlanmoqda...")
    init_db()

    manzillar = [
        ("Toshkent sh., Toshkent", "Samarqand sh., Samarqand"),
        ("Namangan sh., Namangan", "Farg'ona sh., Farg'ona"),
        ("Buxoro sh., Buxoro", "Qarshi sh., Qashqadaryo"),
        ("Urganch sh., Xorazm", "Nukus sh., Qoraqalpog'iston"),
        ("Termiz sh., Surxondaryo", "Jizzax sh., Jizzax"),
    ]

    for i, (ortish, tushirish) in enumerate(manzillar, 1):
        print(f"\n{'─'*60}")
        print(f"Demo zapros #{i}: {ortish} → {tushirish}")

        db = SessionLocal()
        try:
            zapros = Zapros(
                yuk_ortish_joyi=ortish,
                yuk_tushirish_joyi=tushirish,
                yuklash_sanasi=date.today() + timedelta(days=random.randint(1, 7)),
                holat="pending",
            )
            db.add(zapros)
            db.commit()
            db.refresh(zapros)
            zapros_id = zapros.id
        finally:
            db.close()

        natija = zapros_uchun_taklif_ber(zapros_id)

        if natija["muvaffaqiyat"]:
            mashina = natija["tanlangan_mashina"]
            print(f"  ✓ Tanlangan mashina : {mashina['mashina_raqami']}")
            print(f"  ✓ Lokatsiya         : {mashina['joriy_lokatsiya']}")
            print(f"  ✓ Mos ball          : {natija['mos_ball']}%")
            print(f"  ✓ Agent izohi       : {natija['agent_izohi']}")
            print(f"  ✓ Kechikish         : {natija['kechikish_soniya']:.3f}s")
        else:
            print(f"  ✗ Xato: {natija.get('xato')}")

        time.sleep(1)

    print(f"\n{'═'*60}")
    print("Demo yakunlandi! PostgreSQL da natijalarni tekshiring:")
    print("  SELECT * FROM agent_takliflari ORDER BY id DESC LIMIT 5;")


def statistika_korsatish():
    """DB dan joriy statistikani ko'rsatadi."""
    from config.database import SessionLocal
    from models.zapros import Zapros
    from models.malumot import Malumot
    from models.agent_taklif import AgentTaklif
    from sqlalchemy import func

    db = SessionLocal()
    try:
        jami_zapros = db.query(func.count(Zapros.id)).scalar()
        pending = db.query(func.count(Zapros.id)).filter(Zapros.holat == "pending").scalar()
        matched = db.query(func.count(Zapros.id)).filter(Zapros.holat == "matched").scalar()
        jami_mashina = db.query(func.count(Malumot.id)).scalar()
        bosh_mashina = db.query(func.count(Malumot.id)).filter(Malumot.holat == "bosh").scalar()
        jami_taklif = db.query(func.count(AgentTaklif.id)).scalar()
        avg_ball = db.query(func.avg(AgentTaklif.mos_ball)).scalar()
        avg_kechikish = db.query(func.avg(AgentTaklif.kechikish_soniya)).scalar()

        print(f"""
╔══════════════════════════════════════╗
║         Tizim Statistikasi          ║
╠══════════════════════════════════════╣
║  Zaproslar jadvali:                 ║
║    Jami          : {jami_zapros:<17} ║
║    Kutilmoqda    : {pending:<17} ║
║    Ulashtirildi  : {matched:<17} ║
╠══════════════════════════════════════╣
║  Malumotlar jadvali:                ║
║    Jami mashina  : {jami_mashina:<17} ║
║    Bo'sh mashina : {bosh_mashina:<17} ║
╠══════════════════════════════════════╣
║  Agent takliflari:                  ║
║    Jami taklif   : {jami_taklif:<17} ║
║    O'rtacha ball : {f'{avg_ball:.1f}%' if avg_ball else '—':<17} ║
║    O'rt. kechikish: {f'{avg_kechikish:.3f}s' if avg_kechikish else '—':<16} ║
╚══════════════════════════════════════╝""")
    finally:
        db.close()


def asosiy_rejim():
    """
    Asosiy ishga tushirish rejimi.
    Scheduler avtomatik zapros yaratib, agentni ishga tushiradi.
    """
    from config.database import init_db
    from services.zapros_generator import ZaprosGeneratorXizmati

    init_db()
    logger.info("✓ Ma'lumotlar bazasi tayyor")

    min_interval = int(os.getenv("ZAPROS_INTERVAL_MIN", 1))
    max_interval = int(os.getenv("ZAPROS_INTERVAL_MAX", 10))

    generator = ZaprosGeneratorXizmati(
        min_interval_daqiqa=min_interval,
        max_interval_daqiqa=max_interval,
    )
    generator.ishga_tushir()

    # Graceful shutdown
    def to_xtat(signum, frame):
        logger.info("To'xtatish signali qabul qilindi...")
        generator.to_xtat()
        logger.info("Tizim to'xtatildi. Xayr!")
        sys.exit(0)

    signal.signal(signal.SIGINT, to_xtat)
    signal.signal(signal.SIGTERM, to_xtat)

    logger.info("Tizim ishlamoqda. To'xtatish uchun Ctrl+C bosing.")
    logger.info(f"Interval: har {min_interval}-{max_interval} daqiqada bir zapros.")

    while True:
        time.sleep(30)
        statistika_korsatish()


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────

if __name__ == "__main__":
    banner()

    parser = argparse.ArgumentParser(
        description="Yuk Tashish AI Matching Tizimi"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Demo rejim: 5 ta zapros yaratib sinab ko'rish"
    )
    parser.add_argument(
        "--migrate", action="store_true",
        help="Faqat migratsiya va chiqish"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Statistika ko'rsatish"
    )

    args = parser.parse_args()

    if args.migrate:
        migratsiya_qil()
    elif args.demo:
        migratsiya_qil()
        demo_rejim()
    elif args.stats:
        statistika_korsatish()
    else:
        migratsiya_qil()
        asosiy_rejim()
