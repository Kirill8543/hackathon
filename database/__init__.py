from database.models import UserBase, OperationBase, TypeOperation

from database.queries import AsyncORM


async def init_db():

    await AsyncORM.create_tables()
    # Проверка работы запросиксов теперь ну точно работает
    # user = UserBase(max_id="123",
    #                 name="Кирилл",
    #                 tax_rate=10)
    # await AsyncORM.add_user(user)
    # op = OperationBase(year=2026, type=TypeOperation.income, cost=101001010,
    #                    user_id=1, month=9)
    # await AsyncORM.add_operation(op)
    # op = OperationBase(year=2026, type=TypeOperation.income, cost=1292103,
    #                    user_id=1, month=9)
    # await AsyncORM.add_operation(op)
    #
    # print(await AsyncORM.get_operations(1))
    # print(await AsyncORM.sum_income(1, 2026))


if __name__ == '__main__':
    init_db()