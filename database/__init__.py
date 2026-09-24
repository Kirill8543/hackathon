from database.queries import AsyncORM


def init_db():
    AsyncORM.create_tables()



if __name__ == '__main__':
    init_db()