from database.database import engine, session_factory
from database.models import Base, CalendarBase, UserBase

class AsyncCore:
    pass
class AsyncORM:
    @staticmethod
    async def create_tables():
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

