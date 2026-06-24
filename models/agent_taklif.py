"""
AgentTaklif modeli — AI agent matching log va takliflari.
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy import (
    String, DateTime, Integer, Text, Numeric,
    ForeignKey, func, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base


class AgentTaklif(Base):
    __tablename__ = "agent_takliflari"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    zapros_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("zaproslar.id", ondelete="CASCADE"), nullable=False
    )
    mashina_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("malumotlar.id", ondelete="CASCADE"), nullable=False
    )

    # Matching ma'lumotlari
    mos_ball: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agent_izohi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Vaqt logi
    zapros_yaratilgan_vaqti: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    agent_taklif_bergan_vaqti: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    kechikish_soniya: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 3), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    zapros: Mapped["Zapros"] = relationship("Zapros", back_populates="takliflar")
    mashina: Mapped["Malumot"] = relationship("Malumot", back_populates="takliflar")

    __table_args__ = (
        CheckConstraint(
            "mos_ball BETWEEN 0 AND 100",
            name="chk_taklif_mos_ball",
        ),
        UniqueConstraint("zapros_id", "mashina_id", name="uq_zapros_mashina"),
    )

    def __repr__(self) -> str:
        return (
            f"<AgentTaklif(id={self.id}, "
            f"zapros_id={self.zapros_id}, "
            f"mashina_id={self.mashina_id}, "
            f"ball={self.mos_ball}%)>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "zapros_id": self.zapros_id,
            "mashina_id": self.mashina_id,
            "mos_ball": self.mos_ball,
            "agent_izohi": self.agent_izohi,
            "zapros_yaratilgan_vaqti": (
                self.zapros_yaratilgan_vaqti.isoformat()
                if self.zapros_yaratilgan_vaqti else None
            ),
            "agent_taklif_bergan_vaqti": (
                self.agent_taklif_bergan_vaqti.isoformat()
                if self.agent_taklif_bergan_vaqti else None
            ),
            "kechikish_soniya": (
                float(self.kechikish_soniya)
                if self.kechikish_soniya else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
