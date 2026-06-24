"""
Malumotlar modeli — transport vositalari ma'lumotlari.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, DateTime, Integer, Numeric, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.database import Base


class Malumot(Base):
    __tablename__ = "malumotlar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mashina_raqami: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    joriy_lokatsiya: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    holat: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="bosh",
        server_default="bosh",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relation
    takliflar: Mapped[List["AgentTaklif"]] = relationship(
        "AgentTaklif", back_populates="mashina"
    )

    __table_args__ = (
        CheckConstraint(
            "holat IN ('bosh', 'band', 'texnik')",
            name="chk_malumot_holat",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Malumot(id={self.id}, "
            f"raqam='{self.mashina_raqami}', "
            f"lokatsiya='{self.joriy_lokatsiya}', "
            f"holat='{self.holat}')>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mashina_raqami": self.mashina_raqami,
            "joriy_lokatsiya": self.joriy_lokatsiya,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "holat": self.holat,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
