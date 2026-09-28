import datetime as dt
from database.queries import AsyncORM
from database.models import RateNDS
from decimal import Decimal

class Payments:



    # По хорошему надо реализовать функцию которая любую дату переделывет в близжайший рабочий день
    class Fixed:
        @staticmethod
        def date():
            """
            Возвращает дату уплаты фиксированного платежа
            """
            today = dt.date.today()
            month = 12
            day = 28

            date = dt.date(today.year, month, day)

            if date.isoweekday() == 6:
                date = dt.date(today.year, month, day - 1)
            elif date.isoweekday() == 7:
                date = dt.date(today.year, month, day + 1)
            if date < today:
                date = dt.date(today.year + 1, date.month, date.day)
            return date

        @staticmethod
        def cost() -> Decimal:
            """
            Возвращает фиксированную плату
            """
            # По хорошему мы должны спрашивать сколько человек находился в статусе ИП и от этого считать фиксу, но мне лень
            return Decimal(57390)

    class FixedAdd:
        @staticmethod
        def date():
            """
            Возвращает дату дополнительной части
            уплаты фиксированного платежа
            """
            today = dt.date.today()
            month = 12
            day = 28

            date = dt.date(today.year, month, day)

            if date.isoweekday() == 6:
                date = dt.date(today.year, month, day - 1)
            elif date.isoweekday() == 7:
                date = dt.date(today.year, month, day + 1)

            return date

        @staticmethod
        async def cost(max_id) -> Decimal:
            """
            Считает дополнительную фиксированную плату, если пересечен порог в 300 тыс.

            Если не пересечен порог, то возвращает 0
            """
            income = await AsyncORM.Operation.sum_income(await AsyncORM.User.get_id(max_id),
                                                         dt.date.today().year)
            cost = Decimal("0.0")
            if income > 300000:
                cost = (income - 300000) * Decimal("0.01")
                if cost > 321818:
                    cost = Decimal(321818)
            return cost


    class NDS:
        @staticmethod
        def date_declaration():
            """
            Возвращает близжаюсшую дату сдачи декларации по НДС за квартал
            """
            pass

        @staticmethod
        def date_payment():
            """
            Возвращает дату уплаты НДС равными долями за три месяца (непонятно ниче)
            """
            pass

        @staticmethod
        async def check_nds(max_id) -> tuple:
            """
            Возвращает процент использования лимита ндс, использованную сумму денег,
            дату перехода лимита в 20 млн (по среднему)

            (percent, cost_sum, average_cost, month)

            Если порог пересечен:

            (percent, cost_sum, average_cost)
            """
            income = await AsyncORM.Operation.sum_income(await AsyncORM.User.get_id(max_id),
                                                         dt.date.today().year)
            avg_income = await AsyncORM.Operation.avg_income(await AsyncORM.User.get_id(max_id),
                                                             dt.date.today().year)
            avg_income = Decimal(avg_income)
            avg_income = avg_income.quantize(Decimal("1.00"))

            percent = (Decimal(income) / 20*10**6) * 100
            percent = percent.quantize(Decimal("1.00"))

            month = round((20*10**10 - income) / avg_income, 0)

            if month > 12 or month > 12 - dt.date.today().month:
                month = 0

            return (percent, income, avg_income, month)


        @staticmethod
        async def cost_with_nds(max_id, cost):
            """
            Считает цену с ндс
            """
            user = await AsyncORM.User.qet(max_id)
            cost = cost * (1 + Decimal(user.tax_rate) / 100)
            return cost.quantize(Decimal("1.00"))


    class USN:
        @staticmethod
        def date_prepayment():
            """
            Возвращает ближайшую дату уплаты аванса усн
            """
            today = dt.date.today()
            month = today.month // 4 * 4 + 4
            day = 28
            if month == 12:
                month = 4

            date = dt.date(today.year, month, day)

            if date.isoweekday() == 6:
                date = dt.date(today.year, month, day - 1)
            elif date.isoweekday() == 7:
                date = dt.date(today.year, month, day + 1)

            return date





















