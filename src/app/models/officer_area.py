from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class OfficerArea(Base):
    __tablename__ = "officer_area"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    rt: Mapped[int] = mapped_column(Integer, nullable=False)
    rw: Mapped[int] = mapped_column(Integer, nullable=False)
