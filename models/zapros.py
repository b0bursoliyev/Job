"""
Zaproslar modeli — yuk tashish so'rovlari.
"""

from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import String, Date, DateTime, Integer, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base


class Zapros(Base):
    __tablename__ = "zaproslar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    yuk_ortish_joyi: Mapped[str] = mapped_column(String(255), nullable=False)
    yuk_tushirish_joyi: Mapped[str] = mapped_column(String(255), nullable=False)
    yuklash_sanasi: Mapped[date] = mapped_column(Date, nullable=False)
    holat: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relation
    takliflar: Mapped[List["AgentTaklif"]] = relationship(
        "AgentTaklif", back_populates="zapros", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "holat IN ('pending', 'matched', 'cancelled')",
            name="chk_zapros_holat",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Zapros(id={self.id}, "
            f"ortish='{self.yuk_ortish_joyi}', "
            f"holat='{self.holat}')>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "yuk_ortish_joyi": self.yuk_ortish_joyi,
            "yuk_tushirish_joyi": self.yuk_tushirish_joyi,
            "yuklash_sanasi": str(self.yuklash_sanasi),
            "holat": self.holat,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
