import datetime as dt

from sqlalchemy.future import select
from sqlalchemy import func, and_
from database.database import engine, session_factory
from database.models import Base, OperationBase, UserBase, TypeOperation

class AsyncCore:
    pass
class AsyncORM:

    @staticmethod
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    class User:
        @staticmethod
        async def add(user: UserBase):
            async with session_factory() as session:
                session.add(user)
                await session.commit()

        @staticmethod
        async def qet(max_id):
            async with session_factory() as session:
                stmt = select(UserBase).where(UserBase.max_id == max_id)
                res = await session.execute(stmt)
                return res.one_or_none()

        @staticmethod
        async def delete(user_id):
            async with session_factory() as session:
                user = await session.get(UserBase, user_id)
                session.delete(user)
                await session.commit()




    class Operation:

        @staticmethod
        async def get_all(user_id):
            async with session_factory() as session:
                stmt = select(OperationBase).where(OperationBase.user_id == user_id)
                res = await session.execute(stmt)
                return res.all()

        @staticmethod
        async def add(operation: OperationBase):
            async with session_factory() as session:
                session.add(operation)
                await session.commit()

        @staticmethod
        async def delete(operation_id):
            async with session_factory() as session:
                operation = await session.get(OperationBase, operation_id)
                session.delete(operation)
                await session.commit()

        @staticmethod
        async def sum_income(user_id, year):
            async with session_factory() as session:
                stmt = select(func.sum(OperationBase.cost)) \
                    .where(and_(OperationBase.user_id == user_id, OperationBase.type == TypeOperation.income)) \
                    .group_by(OperationBase.user_id, OperationBase.year).having(OperationBase.year == year)
                res = await session.execute(stmt)
                return res.one_or_none()

        @staticmethod
        async def sum_expenses(user_id, year):
            async with session_factory() as session:
                stmt = select(func.sum(OperationBase.cost)) \
                    .where(and_(OperationBase.user_id == user_id, OperationBase.type == TypeOperation.expenses)) \
                    .group_by(OperationBase.user_id, OperationBase.year).having(OperationBase.year == year)
                res = await session.execute(stmt)
                return res.one_or_none()



