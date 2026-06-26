"""
LangGraph asosidagi Yuk Tashish Matching Agent.

Graf holatlari:
  zapros_olish → mashinalarni_qidirish → ai_baholash → natijani_saqlash → tugash

Har bir yangi zapros uchun:
  1. Zaprosni o'qiydi
  2. Mavjud bo'sh mashinalarni topadi
  3. Ollama AI yordamida eng mos mashinani aniqlaydi
  4. Natijani agent_takliflari jadvaliga yozadi
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import TypedDict, Optional, List, Annotated
from decimal import Decimal

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from config.database import SessionLocal
from models.zapros import Zapros
from models.malumot import Malumot
from models.agent_taklif import AgentTaklif

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Agent holat sxemasi (State Schema)
# ─────────────────────────────────────────

class AgentHolat(TypedDict):
    """LangGraph grafining har bir qadamdan o'tadigan holat obyekti."""
    zapros_id: int
    zapros: Optional[dict]
    mavjud_mashinalar: List[dict]
    tanlangan_mashina: Optional[dict]
    mos_ball: int
    agent_izohi: str
    zapros_yaratilgan_vaqti: Optional[datetime]
    agent_taklif_bergan_vaqti: Optional[datetime]
    kechikish_soniya: Optional[float]
    xato: Optional[str]
    muvaffaqiyat: bool


# ─────────────────────────────────────────
# Graf tugunlari (Node Functions)
# ─────────────────────────────────────────

def zapros_olish(holat: AgentHolat) -> AgentHolat:
    """
    1-qadam: Zaprosni PostgreSQL dan o'qiydi.
    """
    logger.info(f"[Agent] Zapros #{holat['zapros_id']} o'qilmoqda...")
    db: Session = SessionLocal()
    try:
        zapros = db.query(Zapros).filter(Zapros.id == holat["zapros_id"]).first()
        if not zapros:
            return {**holat, "xato": f"Zapros #{holat['zapros_id']} topilmadi!", "muvaffaqiyat": False}

        logger.info(f"[Agent] Zapros topildi: {zapros.yuk_ortish_joyi} → {zapros.yuk_tushirish_joyi}")
        return {
            **holat,
            "zapros": zapros.to_dict(),
            "zapros_yaratilgan_vaqti": zapros.created_at,
            "xato": None,
        }
    except Exception as e:
        logger.error(f"[Agent] Zapros o'qishda xato: {e}")
        return {**holat, "xato": str(e), "muvaffaqiyat": False}
    finally:
        db.close()


def mashinalarni_qidirish(holat: AgentHolat) -> AgentHolat:
    """
    2-qadam: Bo'sh mashinalarni ortish joyi bo'yicha qidiradi.
    Avval bir xil viloyatdagilarni, keyin barchani qaytaradi.
    """
    if holat.get("xato"):
        return holat

    ortish_joyi = holat["zapros"]["yuk_ortish_joyi"]
    viloyat = ortish_joyi.split(",")[-1].strip() if "," in ortish_joyi else ortish_joyi

    logger.info(f"[Agent] Bo'sh mashinalar qidirilmoqda... (viloyat: {viloyat})")

    db: Session = SessionLocal()
    try:
        # Avval bir xil viloyatdagi mashinalar
        bir_xil_viloyat = (
            db.query(Malumot)
            .filter(
                Malumot.holat == "bosh",
                Malumot.joriy_lokatsiya.ilike(f"%{viloyat}%"),
            )
            .limit(5)
            .all()
        )

        # Kerakli bo'lsa boshqa viloyatdagilarni ham qo'shamiz
        boshqa = (
            db.query(Malumot)
            .filter(
                Malumot.holat == "bosh",
                ~Malumot.joriy_lokatsiya.ilike(f"%{viloyat}%"),
            )
            .limit(10)
            .all()
        )

        jami = bir_xil_viloyat + boshqa
        mashinalar = [m.to_dict() for m in jami]

        logger.info(
            f"[Agent] Topilgan mashinalar: {len(bir_xil_viloyat)} ta yaqin, "
            f"{len(boshqa)} ta uzoq"
        )

        if not mashinalar:
            return {
                **holat,
                "xato": "Hech qanday bo'sh mashina topilmadi!",
                "muvaffaqiyat": False,
            }

        return {**holat, "mavjud_mashinalar": mashinalar}
    except Exception as e:
        logger.error(f"[Agent] Mashina qidirishda xato: {e}")
        return {**holat, "xato": str(e), "muvaffaqiyat": False}
    finally:
        db.close()


def ai_baholash(holat: AgentHolat) -> AgentHolat:
    """
    3-qadam: Ollama AI yordamida eng mos mashinani tanlaydi va baholaydi.
    LangChain ChatOllama modeli ishlatiladi.
    """
    if holat.get("xato"):
        return holat

    zapros = holat["zapros"]
    mashinalar = holat["mavjud_mashinalar"]

    logger.info(f"[Agent] AI baholash boshlandi ({len(mashinalar)} ta mashina)...")

    llm = ChatOllama(
        model=os.getenv("AGENT_MODEL", "llama3.2:3b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        num_predict=800,
        temperature=0,
    )

    tizim_xabari = SystemMessage(content="""Sen yuk tashish sohasida ishlaydigan AI agentsisan.
Vazifang: berilgan zapros uchun mavjud mashinalar orasidan eng mosini tanlash.

Baholash mezonlari (muhimlik tartibida):
1. Geografik yaqinlik — mashina ortish joyiga qanchalik yaqin?
2. Mashina holati — faqat "bosh" holatdagi mashinalar
3. Umumiy mos kelishi

Javobni FAQAT quyidagi JSON formatida ber, boshqa hech narsa yozma:
{
  "tanlangan_mashina_id": <id raqam>,
  "mos_ball": <0-100 orasida butun son>,
  "izoh": "<qisqa izoh, o'zbek tilida>"
}""")

    mashinalar_matni = "\n".join([
        f"  ID:{m['id']} | {m['mashina_raqami']} | {m['joriy_lokatsiya']}"
        for m in mashinalar
    ])

    inson_xabari = HumanMessage(content=f"""ZAPROS:
  Yuk ortish joyi: {zapros['yuk_ortish_joyi']}
  Yuk tushirish joyi: {zapros['yuk_tushirish_joyi']}
  Yuklash sanasi: {zapros['yuklash_sanasi']}

MAVJUD BO'SH MASHINALAR:
{mashinalar_matni}

Eng mos mashinani tanla va JSON formatida javob ber.""")

    try:
        javob = llm.invoke([tizim_xabari, inson_xabari])
        raw = javob.content
        if isinstance(raw, list):
            matn = " ".join(
                b["text"] for b in raw if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            matn = str(raw)
        matn = matn.strip()

        if "```json" in matn:
            matn = matn.split("```json")[1].split("```")[0].strip()
        elif "```" in matn:
            matn = matn.split("```")[1].split("```")[0].strip()

        natija = json.loads(matn)
        tanlangan_id = natija.get("tanlangan_mashina_id")
        mos_ball = min(100, max(0, int(natija.get("mos_ball", 50))))
        izoh = natija.get("izoh", "")

        # Tanlangan mashinani topish
        tanlangan = next(
            (m for m in mashinalar if m["id"] == tanlangan_id), mashinalar[0]
        )

        logger.info(
            f"[Agent] AI tanladi: #{tanlangan['id']} {tanlangan['mashina_raqami']} "
            f"— ball: {mos_ball}%"
        )

        return {
            **holat,
            "tanlangan_mashina": tanlangan,
            "mos_ball": mos_ball,
            "agent_izohi": izoh,
        }

    except json.JSONDecodeError as e:
        logger.error(f"[Agent] JSON parse xato: {e} | Javob: {matn}")
        # Fallback: eng yaqin mashinani ol
        tanlangan = mashinalar[0]
        return {
            **holat,
            "tanlangan_mashina": tanlangan,
            "mos_ball": 60,
            "agent_izohi": "Fallback: eng birinchi bo'sh mashina tanlandi",
        }
    except Exception as e:
        logger.error(f"[Agent] AI baholashda xato: {e}")
        return {**holat, "xato": str(e), "muvaffaqiyat": False}


def natijani_saqlash(holat: AgentHolat) -> AgentHolat:
    """
    4-qadam: Matching natijasini agent_takliflari jadvaliga yozadi
    va zapros holatini 'matched' ga o'zgartiradi.
    """
    if holat.get("xato"):
        return holat

    taklif_vaqti = datetime.now(timezone.utc)
    zapros_vaqti = holat["zapros_yaratilgan_vaqti"]

    # Kechikish hisoblash
    if zapros_vaqti:
        if zapros_vaqti.tzinfo is None:
            zapros_vaqti = zapros_vaqti.replace(tzinfo=timezone.utc)
        kechikish = (taklif_vaqti - zapros_vaqti).total_seconds()
    else:
        kechikish = 0.0

    logger.info(
        f"[Agent] Natija saqlanmoqda... kechikish: {kechikish:.3f}s"
    )

    db: Session = SessionLocal()
    try:
        # AgentTaklif yaratish
        taklif = AgentTaklif(
            zapros_id=holat["zapros_id"],
            mashina_id=holat["tanlangan_mashina"]["id"],
            mos_ball=holat["mos_ball"],
            agent_izohi=holat["agent_izohi"],
            zapros_yaratilgan_vaqti=zapros_vaqti,
            agent_taklif_bergan_vaqti=taklif_vaqti,
            kechikish_soniya=Decimal(str(round(kechikish, 3))),
        )
        db.add(taklif)

        # Zapros holatini yangilash
        zapros = db.query(Zapros).filter(Zapros.id == holat["zapros_id"]).first()
        if zapros:
            zapros.holat = "matched"

        # Mashinani "band" qilish
        mashina = db.query(Malumot).filter(
            Malumot.id == holat["tanlangan_mashina"]["id"]
        ).first()
        if mashina:
            mashina.holat = "band"

        db.commit()

        logger.info(
            f"[Agent] ✓ Saqlandi | Zapros #{holat['zapros_id']} → "
            f"Mashina #{holat['tanlangan_mashina']['id']} | "
            f"Ball: {holat['mos_ball']}% | "
            f"Kechikish: {kechikish:.3f}s"
        )

        return {
            **holat,
            "agent_taklif_bergan_vaqti": taklif_vaqti,
            "kechikish_soniya": kechikish,
            "muvaffaqiyat": True,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[Agent] Saqlashda xato: {e}")
        return {**holat, "xato": str(e), "muvaffaqiyat": False}
    finally:
        db.close()


def xato_boshqarish(holat: AgentHolat) -> AgentHolat:
    """
    Xato holati — logga yozadi va zaprosni 'cancelled' qilmaydi
    (keyingi urinish uchun qoldiradi).
    """
    logger.error(
        f"[Agent] Zapros #{holat['zapros_id']} uchun xato: {holat.get('xato')}"
    )
    return {**holat, "muvaffaqiyat": False}


# ─────────────────────────────────────────
# Yo'naltiruvchi funksiya (Router)
# ─────────────────────────────────────────

def xato_tekshirish(holat: AgentHolat) -> str:
    """Har bir qadamdan keyin xato bor-yo'qligini tekshiradi."""
    if holat.get("xato"):
        return "xato"
    return "davom_et"


# ─────────────────────────────────────────
# LangGraph grafini qurish
# ─────────────────────────────────────────

def agent_graf_yaratish() -> StateGraph:
    """
    LangGraph asosidagi matching agent grafini quradi.

    Graf sxemasi:
    ┌─────────────────┐
    │  zapros_olish   │
    └────────┬────────┘
             │ (xato?) ──→ xato_boshqarish → END
             ▼
    ┌─────────────────────────┐
    │  mashinalarni_qidirish  │
    └────────┬────────────────┘
             │ (xato?) ──→ xato_boshqarish → END
             ▼
    ┌─────────────────┐
    │   ai_baholash   │
    └────────┬────────┘
             │ (xato?) ──→ xato_boshqarish → END
             ▼
    ┌───────────────────┐
    │  natijani_saqlash │
    └────────┬──────────┘
             ▼
            END
    """
    graf = StateGraph(AgentHolat)

    # Tugunlarni qo'shish
    graf.add_node("zapros_olish", zapros_olish)
    graf.add_node("mashinalarni_qidirish", mashinalarni_qidirish)
    graf.add_node("ai_baholash", ai_baholash)
    graf.add_node("natijani_saqlash", natijani_saqlash)
    graf.add_node("xato_boshqarish", xato_boshqarish)

    # Boshlang'ich tugun
    graf.set_entry_point("zapros_olish")

    # Shartli o'tishlar (conditional edges)
    graf.add_conditional_edges(
        "zapros_olish",
        xato_tekshirish,
        {"davom_et": "mashinalarni_qidirish", "xato": "xato_boshqarish"},
    )
    graf.add_conditional_edges(
        "mashinalarni_qidirish",
        xato_tekshirish,
        {"davom_et": "ai_baholash", "xato": "xato_boshqarish"},
    )
    graf.add_conditional_edges(
        "ai_baholash",
        xato_tekshirish,
        {"davom_et": "natijani_saqlash", "xato": "xato_boshqarish"},
    )

    # So'nggi tugunlar
    graf.add_edge("natijani_saqlash", END)
    graf.add_edge("xato_boshqarish", END)

    return graf.compile()


# ─────────────────────────────────────────
# Asosiy interfeys funksiyasi
# ─────────────────────────────────────────

def zapros_uchun_taklif_ber(zapros_id: int) -> dict:
    """
    Berilgan zapros ID si uchun LangGraph agentini ishga tushiradi.

    Args:
        zapros_id: Qayta ishlanadigan zapros ID si

    Returns:
        Agent yakuniy holati (natija yoki xato ma'lumotlari)
    """
    app = agent_graf_yaratish()

    boshlangich_holat: AgentHolat = {
        "zapros_id": zapros_id,
        "zapros": None,
        "mavjud_mashinalar": [],
        "tanlangan_mashina": None,
        "mos_ball": 0,
        "agent_izohi": "",
        "zapros_yaratilgan_vaqti": None,
        "agent_taklif_bergan_vaqti": None,
        "kechikish_soniya": None,
        "xato": None,
        "muvaffaqiyat": False,
    }

    yakuniy_holat = app.invoke(boshlangich_holat)
    return yakuniy_holat
