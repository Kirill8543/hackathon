from database.models import UserBase, OperationBase, TypeOperation, PayerNDS, RateNDS

from database.queries import AsyncORM


async def init_db():

    await AsyncORM.create_tables()
    # Проверка работы запросиксов теперь ну точно работает
    user = UserBase(max_id="123",
                    name="Кирилл",
                    tax_rate=5,
                    PayerNDS=PayerNDS.yes
                    )
    await AsyncORM.User.add(user)
    op = OperationBase(year=2026, type="доходы", cost=101001010,
                       user_id=1, month=9)
    await AsyncORM.Operation.add(op)
    op = OperationBase(year=2026, type="expenses", cost=1292103,
                       user_id=1, month=9)
    await AsyncORM.Operation.add(op)

    print(await AsyncORM.Operation.get_all(1))
    print(await AsyncORM.Operation.sum_income(1, 2026))
    print(await AsyncORM.Operation.avg_income(1, 2026))
    print(await AsyncORM.User.qet("123"))



if __name__ == '__main__':
    init_db()