"""
Avtomatik Zapros Generator Xizmati.

Kuniga 400+ zapros yaratadi (1-10 daqiqa oraliqda).
APScheduler ishlatiladi.
"""

import random
import logging
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config.database import SessionLocal
from models.zapros import Zapros
from agents.matching_agent import zapros_uchun_taklif_ber

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# O'zbekiston joylashuv ma'lumotlari
# ─────────────────────────────────────────

MANZILLAR = [
    # Toshkent viloyati
    "Toshkent sh., Toshkent",
    "Chirchiq, Toshkent",
    "Olmaliq, Toshkent",
    "Angren, Toshkent",
    "Bekobod, Toshkent",
    "Yangiyo'l, Toshkent",
    # Samarqand viloyati
    "Samarqand sh., Samarqand",
    "Kattaqo'rg'on, Samarqand",
    "Ishtixon, Samarqand",
    "Urgut, Samarqand",
    # Buxoro viloyati
    "Buxoro sh., Buxoro",
    "Kogon, Buxoro",
    "G'ijduvon, Buxoro",
    "Romitan, Buxoro",
    # Namangan viloyati
    "Namangan sh., Namangan",
    "Chortoq, Namangan",
    "Pop, Namangan",
    "Uychi, Namangan",
    # Andijon viloyati
    "Andijon sh., Andijon",
    "Asaka, Andijon",
    "Xo'jaobod, Andijon",
    "Shahrixon, Andijon",
    # Farg'ona viloyati
    "Farg'ona sh., Farg'ona",
    "Marg'ilon, Farg'ona",
    "Qo'qon, Farg'ona",
    "Quva, Farg'ona",
    # Qashqadaryo viloyati
    "Qarshi sh., Qashqadaryo",
    "Shahrisabz, Qashqadaryo",
    "G'uzor, Qashqadaryo",
    "Muborak, Qashqadaryo",
    # Surxondaryo viloyati
    "Termiz sh., Surxondaryo",
    "Denov, Surxondaryo",
    "Sho'rchi, Surxondaryo",
    "Uzun, Surxondaryo",
    # Xorazm viloyati
    "Urganch sh., Xorazm",
    "Xiva, Xorazm",
    "Pitnak, Xorazm",
    "Gurlan, Xorazm",
    # Navoiy viloyati
    "Navoiy sh., Navoiy",
    "Zarafshon, Navoiy",
    "Uchquduq, Navoiy",
    # Sirdaryo viloyati
    "Guliston sh., Sirdaryo",
    "Yangiyer, Sirdaryo",
    "Shirin, Sirdaryo",
    # Jizzax viloyati
    "Jizzax sh., Jizzax",
    "G'allaorol, Jizzax",
    "Paxtakor, Jizzax",
    # Qoraqalpog'iston
    "Nukus sh., Qoraqalpog'iston",
    "Mo'ynoq, Qoraqalpog'iston",
    "Turtkul, Qoraqalpog'iston",
    "Xo'jayli, Qoraqalpog'iston",
]


def tasodifiy_manzil(istisno: str = None) -> str:
    """Tasodifiy manzil tanlaydi (istisno bundan tashqari)."""
    manzillar = [m for m in MANZILLAR if m != istisno]
    return random.choice(manzillar)


def tasodifiy_sana() -> date:
    """Bugundan 1-14 kun ichidagi tasodifiy sana."""
    kunlar = random.randint(1, 14)
    return date.today() + timedelta(days=kunlar)


# ─────────────────────────────────────────
# Zapros yaratish va agent ishga tushirish
# ─────────────────────────────────────────

def yangi_zapros_yarat_va_agent_ishga_tushir():
    """
    Yangi zapros yaratadi va darhol AI agentni ishga tushiradi.
    Bu funksiya scheduler tomonidan chaqiriladi.
    """
    db = SessionLocal()
    try:
        ortish_joyi = tasodifiy_manzil()
        tushirish_joyi = tasodifiy_manzil(istisno=ortish_joyi)
        yuklash_sanasi = tasodifiy_sana()

        zapros = Zapros(
            yuk_ortish_joyi=ortish_joyi,
            yuk_tushirish_joyi=tushirish_joyi,
            yuklash_sanasi=yuklash_sanasi,
            holat="pending",
        )
        db.add(zapros)
        db.commit()
        db.refresh(zapros)

        zapros_id = zapros.id
        logger.info(
            f"[Generator] Yangi zapros #{zapros_id}: "
            f"{ortish_joyi} → {tushirish_joyi} | {yuklash_sanasi}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"[Generator] Zapros yaratishda xato: {e}")
        return
    finally:
        db.close()

    # Agent ishga tushirish (DB sessiyasi yopilgandan keyin)
    try:
        natija = zapros_uchun_taklif_ber(zapros_id)
        if natija["muvaffaqiyat"]:
            mashina = natija.get("tanlangan_mashina", {})
            logger.info(
                f"[Generator] ✓ Zapros #{zapros_id} ulashtirildi → "
                f"{mashina.get('mashina_raqami')} | "
                f"Ball: {natija['mos_ball']}% | "
                f"Kechikish: {natija.get('kechikish_soniya', 0):.3f}s"
            )
        else:
            logger.warning(
                f"[Generator] ✗ Zapros #{zapros_id} ulashtirilmadi: "
                f"{natija.get('xato')}"
            )
    except Exception as e:
        logger.error(f"[Generator] Agent xatosi (zapros #{zapros_id}): {e}")


# ─────────────────────────────────────────
# Scheduler xizmati
# ─────────────────────────────────────────

class ZaprosGeneratorXizmati:
    """
    APScheduler asosidagi avtomatik zapros generator.

    Har 1-10 daqiqada yangi zapros yaratadi.
    Kuniga minimum 400 ta zapros = ~3.6 daqiqada bir zapros.
    """

    def __init__(
        self,
        min_interval_daqiqa: int = 1,
        max_interval_daqiqa: int = 10,
    ):
        self.min_interval = min_interval_daqiqa * 60   # sekundga o'girish
        self.max_interval = max_interval_daqiqa * 60
        self.scheduler = BackgroundScheduler(
            job_defaults={"misfire_grace_time": 30}
        )
        self._joriy_interval = self._tasodifiy_interval()

    def _tasodifiy_interval(self) -> int:
        return random.randint(self.min_interval, self.max_interval)

    def _ish(self):
        """Scheduler chaqiradigan asosiy funksiya."""
        yangi_zapros_yarat_va_agent_ishga_tushir()
        # Keyingi interval tasodifiy
        yangi_interval = self._tasodifiy_interval()
        self.scheduler.reschedule_job(
            "zapros_generator",
            trigger=IntervalTrigger(seconds=yangi_interval),
        )
        logger.debug(f"[Scheduler] Keyingi zapros {yangi_interval}s dan keyin.")

    def ishga_tushir(self):
        """Schedulerni ishga tushiradi."""
        self.scheduler.add_job(
            func=self._ish,
            trigger=IntervalTrigger(seconds=self._joriy_interval),
            id="zapros_generator",
            name="Zapros Generator",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            f"[Scheduler] Zapros generator ishga tushdi. "
            f"Interval: {self.min_interval//60}-{self.max_interval//60} daqiqa."
        )

    def to_xtat(self):
        """Schedulerni to'xtatadi."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("[Scheduler] Zapros generator to'xtatildi.")

    def holat(self) -> dict:
        """Joriy holat ma'lumotlari."""
        jobs = self.scheduler.get_jobs()
        return {
            "ishlamoqda": self.scheduler.running,
            "ish_soni": len(jobs),
            "ishlar": [
                {
                    "id": j.id,
                    "nomi": j.name,
                    "keyingi_ishlash": str(j.next_run_time),
                }
                for j in jobs
            ],
        }
