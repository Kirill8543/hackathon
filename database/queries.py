from database.database import engine, session_factory
from database.models import Base, OperationBase, UserBase

class AsyncCore:
    pass
class AsyncORM:
    @staticmethod
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)


    @staticmethod
    async def add_user(user: UserBase):
        async with session_factory as session:
            await session.add(user)

    @staticmethod
    async def qet_user(max_id):
        async with session_factory as session:
            await session.query(UserBase).filter_by(max_id=max_id).one_or_none()

    @staticmethod
    async def get_operation(user: UserBase):
        async with session_factory as session:
            await session.query(OperationBase).filter_by(user_id=user.id).all()

    @staticmethod
    async def add_operation(operation: OperationBase):
        async with session_factory as session:
            await session.add(operation)

    @staticmethod
    async def sum_income(user: UserBase):
        pass

