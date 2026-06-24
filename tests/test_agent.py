"""
Agent va generator uchun testlar.

Ishga tushirish:
    python -m pytest tests/ -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date, datetime, timezone
from decimal import Decimal


# ─────────────────────────────────────────
# Unit testlar (DB va AI mock bilan)
# ─────────────────────────────────────────

class TestZaprosGenerator:
    """ZaprosGeneratorXizmati testlari."""

    def test_tasodifiy_manzil(self):
        """Tasodifiy manzil qaytarilishi."""
        from services.zapros_generator import tasodifiy_manzil, MANZILLAR

        manzil = tasodifiy_manzil()
        assert manzil in MANZILLAR

    def test_tasodifiy_manzil_istisno(self):
        """Istisno manzil qaytarilmasligi."""
        from services.zapros_generator import tasodifiy_manzil

        istisno = "Toshkent sh., Toshkent"
        for _ in range(20):
            manzil = tasodifiy_manzil(istisno=istisno)
            assert manzil != istisno

    def test_tasodifiy_sana(self):
        """Sana bugundan keyin bo'lishi."""
        from services.zapros_generator import tasodifiy_sana

        sana = tasodifiy_sana()
        assert sana > date.today()
        assert sana <= date.today().replace(year=date.today().year + 1)


class TestAgentGraf:
    """LangGraph agent tugunlari testlari."""

    def test_zapros_olish_topilmadi(self):
        """Mavjud bo'lmagan zapros ID si uchun xato qaytarish."""
        from agents.matching_agent import zapros_olish

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("agents.matching_agent.SessionLocal", return_value=mock_db):
            holat = {
                "zapros_id": 99999,
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
            natija = zapros_olish(holat)

        assert natija["xato"] is not None
        assert natija["muvaffaqiyat"] is False

    def test_xato_tekshirish_xato_bor(self):
        """Xato mavjud bo'lganda 'xato' qaytarish."""
        from agents.matching_agent import xato_tekshirish

        holat = {"xato": "Test xatosi", "muvaffaqiyat": False}
        assert xato_tekshirish(holat) == "xato"

    def test_xato_tekshirish_xato_yoq(self):
        """Xato yo'q bo'lganda 'davom_et' qaytarish."""
        from agents.matching_agent import xato_tekshirish

        holat = {"xato": None, "muvaffaqiyat": False}
        assert xato_tekshirish(holat) == "davom_et"

    def test_agent_graf_yaratish(self):
        """Graf muvaffaqiyatli yaratilishi."""
        from agents.matching_agent import agent_graf_yaratish

        graf = agent_graf_yaratish()
        assert graf is not None

    def test_kechikish_hisoblash(self):
        """Kechikish vaqti to'g'ri hisoblanishi."""
        from datetime import timedelta

        boshlanish = datetime.now(timezone.utc)
        tugash = boshlanish + timedelta(seconds=2.5)
        kechikish = (tugash - boshlanish).total_seconds()

        assert abs(kechikish - 2.5) < 0.01


class TestModellar:
    """SQLAlchemy modellari testlari."""

    def test_zapros_to_dict(self):
        """Zapros to_dict() to'g'ri ishlashi."""
        from models.zapros import Zapros

        z = Zapros(
            id=1,
            yuk_ortish_joyi="Toshkent sh., Toshkent",
            yuk_tushirish_joyi="Samarqand sh., Samarqand",
            yuklash_sanasi=date(2025, 12, 31),
            holat="pending",
        )
        d = z.to_dict()

        assert d["id"] == 1
        assert d["yuk_ortish_joyi"] == "Toshkent sh., Toshkent"
        assert d["holat"] == "pending"

    def test_malumot_to_dict(self):
        """Malumot to_dict() to'g'ri ishlashi."""
        from models.malumot import Malumot

        m = Malumot(
            id=1,
            mashina_raqami="01 A 1234",
            joriy_lokatsiya="Toshkent sh., Toshkent",
            latitude=Decimal("41.2995"),
            longitude=Decimal("69.2401"),
            holat="bosh",
        )
        d = m.to_dict()

        assert d["mashina_raqami"] == "01 A 1234"
        assert d["latitude"] == pytest.approx(41.2995, rel=1e-4)
        assert d["holat"] == "bosh"

    def test_agent_taklif_to_dict(self):
        """AgentTaklif to_dict() to'g'ri ishlashi."""
        from models.agent_taklif import AgentTaklif

        vaqt = datetime.now(timezone.utc)
        t = AgentTaklif(
            id=1,
            zapros_id=10,
            mashina_id=5,
            mos_ball=87,
            agent_izohi="Eng yaqin mashina tanlandi",
            zapros_yaratilgan_vaqti=vaqt,
            agent_taklif_bergan_vaqti=vaqt,
            kechikish_soniya=Decimal("1.234"),
        )
        d = t.to_dict()

        assert d["mos_ball"] == 87
        assert d["kechikish_soniya"] == pytest.approx(1.234, rel=1e-3)


# ─────────────────────────────────────────
# Integration test (real DB kerak)
# ─────────────────────────────────────────

@pytest.mark.integration
class TestIntegration:
    """
    Real PostgreSQL va Anthropic API bilan testlar.
    Ishga tushirish: pytest -m integration
    """

    def test_tam_agent_oqimi(self):
        """
        To'liq agent oqimini sinab ko'rish:
        Zapros yaratish → Agent ishga tushirish → Natijani tekshirish
        """
        from config.database import SessionLocal, init_db
        from models.zapros import Zapros
        from models.agent_taklif import AgentTaklif
        from agents.matching_agent import zapros_uchun_taklif_ber

        init_db()
        db = SessionLocal()

        try:
            zapros = Zapros(
                yuk_ortish_joyi="Toshkent sh., Toshkent",
                yuk_tushirish_joyi="Samarqand sh., Samarqand",
                yuklash_sanasi=date(2025, 12, 31),
                holat="pending",
            )
            db.add(zapros)
            db.commit()
            db.refresh(zapros)
            zapros_id = zapros.id
        finally:
            db.close()

        natija = zapros_uchun_taklif_ber(zapros_id)

        assert natija["muvaffaqiyat"] is True
        assert natija["mos_ball"] > 0
        assert natija["tanlangan_mashina"] is not None
        assert natija["kechikish_soniya"] > 0

        # DB da taklif mavjudligini tekshirish
        db = SessionLocal()
        try:
            taklif = (
                db.query(AgentTaklif)
                .filter(AgentTaklif.zapros_id == zapros_id)
                .first()
            )
            assert taklif is not None
            assert taklif.mos_ball == natija["mos_ball"]
        finally:
            db.close()
