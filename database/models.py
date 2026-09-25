import enum
from datetime import date

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import String, ForeignKey, Enum, Text, Date
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
    max_id: Mapped[str] # Я хз че макс дает в качестве айдишника у себя надо чекнуть
    name: Mapped[str]
    tax_rate: Mapped[int]



class OperationBase(Base):
    __tablename__ = "operation"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    type: Mapped[TypeOperation] = mapped_column(Enum(TypeOperation))
    month: Mapped[int]  # Даты не нужны нужны месяцы, а как их адекватно сохранять хз, можно enum бахнуть, но пока будут циферки
    cost: Mapped[int]

