import enum
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import String, ForeignKey, Enum, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class TypeOperation(enum.Enum):
    # Здесь можно добавить еще что-нибудь. Условно обязательный платёж
    income = "доходы"
    expenses = "расходы"


class Base(DeclarativeBase):
    pass

class UserBase(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    tax_rate: Mapped[int]



class CalendarBase(Base):
    __tablename__ = "calendar"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    type: Mapped[TypeOperation] = mapped_column(Enum(TypeOperation))
    cost: Mapped[int]

