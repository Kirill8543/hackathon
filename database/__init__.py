from database.models import UserBase, OperationBase, TypeOperation
from database.queries import AsyncORM


async def init_db():

    await AsyncORM.create_tables()



if __name__ == '__main__':
    init_db()