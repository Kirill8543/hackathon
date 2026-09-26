import datetime as dt
from database.queries import AsyncORM


class Payments:
    user_id: int

    # По хорошему надо реализовать функцию которая любую дату переделывет в близжайший рабочий день
    @staticmethod
    def date_prepayment_usn():
        """
        Возвращает ближайшую дату уплаты аванса усн
        """
        today = dt.date.today()
        month = today.month//4*4 + 4
        day = 28
        if month == 12:
            month = 4

        date = dt.date(today.year, month, day)

        if date.isoweekday() == 6:
            date = dt.date(today.year, month, day - 1)
        elif date.isoweekday() == 7:
            date = dt.date(today.year, month, day + 1)

        return date

    @staticmethod
    def date_fix_payment():
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
    def date_add_fix_payment():
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
    def date_declaration_nds():
        """
        Возвращает близжаюсшую дату сдачи декларации по НДС за квартал
        """
        pass

    @staticmethod
    def date_payment_nds():
        """
        Возвращает дату уплаты НДС равными долями за три месяца (непонятно ниче)
        """
        pass

    def check_nds(self) -> tuple:
        """
        Возвращает процент использования лимита ндс, использованную сумму денег,
        дату перехода лимита в 20 млн (по среднему)

        (percent, cost_sum, average_cost, date)

        Если порог пересечен:

        (percent, cost_sum, average_cost)
        """
        pass


    def add_fix_payment(self) -> int:
        """
        Считает дополнительную фиксированную плату, если пересечен порог в 300 тыс.

        Если не пересечен порог, то возвращает 0
        """
        pass

    @staticmethod
    def fix_payment() -> int:
        """
        Возвращает фиксированную плату
        """
        # По хорошему мы должны спрашивать сколько человек находился в статусе ИП и от этого считать фиксу, но мне лень
        return 57390

    @staticmethod
    def cost_with_nds() -> int:
        """
        Считает цену с ндс
        """
        pass



