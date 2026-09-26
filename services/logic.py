import datetime as dt
from database.queries import AsyncORM


class Payments():
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



