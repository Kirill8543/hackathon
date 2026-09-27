import datetime as dt
from database.queries import AsyncORM


class Payments:
    user_id: int

    @staticmethod
    def _get_next_working_day(date: dt.date) -> dt.date:
        """
        Переносит дату на следующий рабочий день, если она выпадает на выходной.
        (Суббота -> Понедельник, Воскресенье -> Понедельник).
        Примечание: для учета официальных праздников РФ рекомендуется использовать
        внешнюю библиотеку, например, production_calendar.
        """
        if date.isoweekday() == 6:  # Суббота
            return date + dt.timedelta(days=2)
        elif date.isoweekday() == 7:  # Воскресенье
            return date + dt.timedelta(days=1)
        return date

    @staticmethod
    def date_prepayment_usn() -> dt.date:
        """
        Возвращает ближайшую дату уплаты аванса УСН (28 число месяца, следующего за кварталом).
        """
        today = dt.date.today()
        month = (today.month // 4) * 4 + 4
        day = 28

        if month > 12:
            month = 4
            year = today.year + 1
        else:
            year = today.year

        date = dt.date(year, month, day)
        return Payments._get_next_working_day(date)

    @staticmethod
    def date_fix_payment() -> dt.date:
        """
        Возвращает дату уплаты фиксированного платежа (до 31 декабря, обычно 28-е).
        """
        today = dt.date.today()
        month, day = 12, 28

        date = dt.date(today.year, month, day)
        date = Payments._get_next_working_day(date)

        if date < today:
            date = dt.date(today.year + 1, month, day)
            date = Payments._get_next_working_day(date)

        return date

    @staticmethod
    def date_add_fix_payment() -> dt.date:
        """
        Возвращает дату уплаты дополнительной части фиксированного платежа
        (1% с дохода свыше 300 тыс.) — 1 июля года, следующего за отчетным.
        """
        today = dt.date.today()
        date = dt.date(today.year + 1, 7, 1)
        return Payments._get_next_working_day(date)

    @staticmethod
    def date_declaration_nds() -> dt.date:
        """
        Возвращает ближайшую дату сдачи декларации по НДС за квартал
        (25 число месяца, следующего за кварталом).
        """
        today = dt.date.today()
        quarter_month = ((today.month - 1) // 3) * 3 + 3
        year = today.year

        next_month = quarter_month + 1
        if next_month > 12:
            next_month = 1
            year += 1

        date = Payments._get_next_working_day(dt.date(year, next_month, 25))

        if date < today:
            next_month += 3
            if next_month > 12:
                next_month -= 12
                year += 1
            date = Payments._get_next_working_day(dt.date(year, next_month, 25))

        return date

    @staticmethod
    def date_payment_nds() -> tuple[dt.date, dt.date, dt.date]:
        """
        Возвращает кортеж из трех дат уплаты НДС равными долями за три месяца,
        следующих за отчетным кварталом (28 число каждого месяца).
        """
        today = dt.date.today()
        quarter_month = ((today.month - 1) // 3) * 3 + 3
        year = today.year

        dates = []
        for i in range(1, 4):
            month = quarter_month + i
            y = year
            if month > 12:
                month -= 12
                y += 1
            dates.append(Payments._get_next_working_day(dt.date(y, month, 28)))

        # Если весь цикл платежей за этот квартал уже прошел, сдвигаем на следующий
        if dates[-1] < today:
            dates = []
            for i in range(1, 4):
                month = quarter_month + i + 3
                y = year
                while month > 12:
                    month -= 12
                    y += 1
                dates.append(Payments._get_next_working_day(dt.date(y, month, 28)))

        return tuple(dates)

    async def check_nds(self) -> tuple:
        """
        Возвращает процент использования лимита НДС, использованную сумму денег,
        дату перехода лимита в 20 млн (по среднему).

        (percent, cost_sum, average_cost, date)
        Если порог пересечен: (percent, cost_sum, average_cost)
        """
        limit = 20000000

        cost_sum = await AsyncORM.get_total_income(self.user_id) if hasattr(AsyncORM, 'get_total_income') else 0
        average_cost = await AsyncORM.get_average_monthly_income(self.user_id) if hasattr(AsyncORM, 'get_average_monthly_income') else 0

        percent = round((cost_sum / limit) * 100, 2) if limit > 0 else 0.0

        if cost_sum >= limit:
            return percent, cost_sum, average_cost

        if average_cost > 0:
            months_left = (limit - cost_sum) / average_cost
            target_date = dt.date.today() + dt.timedelta(days=int(months_left * 30.44))
        else:
            target_date = None

        return percent, cost_sum, average_cost, target_date

    async def add_fix_payment(self) -> int:
        """
        Считает дополнительную фиксированную плату, если пересечен порог в 300 тыс.
        Если не пересечен порог, возвращает 0.
        """
        limit = 300000

        income = await AsyncORM.get_total_income(self.user_id) if hasattr(AsyncORM, 'get_total_income') else 0

        if income > limit:
            extra = int((income - limit) * 0.01)
            return extra

        return 0

    @staticmethod
    def fix_payment() -> int:
        """
        Возвращает базовую фиксированную плату.
        """
        return 57390

    @staticmethod
    def cost_with_nds(cost: float | int) -> float:
        """
        Считает цену с НДС (20%).
        Примечание: добавлен аргумент `cost`, так как статический метод не может
        вычислить стоимость без входных данных.
        """
        return round(cost * 1.2, 2)