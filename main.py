"""Бот «Светофор НДС» для MAX — один файл.

Импортирует логику из logic.py (Payments, AsyncORM, модели).
Запуск: python bot.py  (long polling, без домена и SSL).

ИСПРАВЛЕНО: kb() и main_kb() теперь всегда возвращают list[Attachment],
а не одиночный Attachment. Это Fixes ошибку:
  'tuple' object has no attribute 'model_dump'
"""

import asyncio
import logging
import os
import datetime as dt
from enum import Enum
from decimal import Decimal
from typing import Optional

from maxapi import Bot, Dispatcher, F
from maxapi.types import (
    MessageCreated, BotStarted, MessageCallback, Command,
    CallbackButton, ButtonsPayload, Attachment,
)
from maxapi.enums.intent import Intent

import database
from core.config import settings
from services.logic import Payments
from database.models import (UserBase, OperationBase,
    TypeOperation, RateNDS,)
from database.queries import AsyncORM

# ═══════════════════════════════════════════════════════════
#  Настройка
# ═══════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
bot = Bot(token=settings.VK_MAX_TOKEN)
dp = Dispatcher()

LIMIT = 20_000_000
YEAR_TRACK = 2026

MONTHS = [
    "", "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]
MONTHS_PRED = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

# ═══════════════════════════════════════════════════════════
#  FSM — состояния пользователя
# ═══════════════════════════════════════════════════════════
class S(Enum):
    INCOME_2025    = "income_2025"
    WAIT_INCOME    = "wait_income"
    WAIT_WHAT_IF   = "wait_what_if"
    WAIT_VAT_PRICE = "wait_vat_price"
    MENU           = "menu"

class FSM:
    def __init__(self):
        self._st: dict[str, S] = {}
        self._data: dict[str, dict] = {}

    def get(self, uid: str) -> Optional[S]:
        return self._st.get(uid)

    def set(self, uid: str, s: S):
        self._st[uid] = s

    def put(self, uid: str, k: str, v):
        self._data.setdefault(uid, {})[k] = v

    def fetch(self, uid: str, k: str = ""):
        d = self._data.get(uid, {})
        return d.get(k) if k else d

    def clear(self, uid: str):
        self._st.pop(uid, None)
        self._data.pop(uid, None)

fsm = FSM()

# ═══════════════════════════════════════════════════════════
#  Клавиатуры — ВСЕГДА возвращают list[Attachment]
#  (не одиночный Attachment! — иначе maxapi падает с
#   'tuple' object has no attribute 'model_dump')
# ═══════════════════════════════════════════════════════════
def _btn(text: str, payload: str, intent=Intent.DEFAULT) -> CallbackButton:
    return CallbackButton(text=text, payload=payload, intent=intent)

def kb(*rows) -> list:
    """Каждый row — список (text, payload). Возвращает list[Attachment]."""
    buttons = [[_btn(t, p) for t, p in row] for row in rows]
    return [Attachment(
        type="inline_keyboard",
        payload=ButtonsPayload(buttons=buttons),
    )]

def main_kb() -> list:
    return kb(
        [("Внести доход", "add_income"), ("Что если?", "what_if")],
        [("Календарь", "calendar"), ("Источники", "sources")],
    )

# ═══════════════════════════════════════════════════════════
#  Утилиты форматирования
# ═══════════════════════════════════════════════════════════
def fmt_money(n) -> str:
    """13_200_000 -> '13,2 млн ₽', 500_000 -> '500 000 ₽'."""
    n = int(n or 0)
    if n >= 1_000_000:
        s = f"{n / 1_000_000:.1f}".replace(".0", "")
        return f"{s} млн ₽"
    return f"{n:,} ₽".replace(",", " ")

def pbar(percent: float) -> str:
    filled = min(int(round(percent / 10)), 10)
    return "▓" * filled + "░" * (10 - filled)

def semafor(percent: float) -> str:
    if percent >= 90:
        return "🔴"
    if percent >= 70:
        return "🟡"
    return "🟢"

def safe_int(text: str) -> Optional[int]:
    try:
        return int(text.replace(" ", "").replace("\xa0", "").replace("₽", ""))
    except (ValueError, TypeError):
        return None

# ═══════════════════════════════════════════════════════════
#  Обёртки над logic.py
# ═══════════════════════════════════════════════════════════
async def ensure_user(max_id: str, name: str = "Пользователь") -> bool:
    user = await AsyncORM.User.qet(max_id)
    if user:
        return False
    await AsyncORM.User.add(UserBase(max_id=max_id, name=name, tax_rate=0))
    return True

async def get_internal_id(max_id: str) -> int:
    return await AsyncORM.User.get_id(max_id)

async def save_income(max_id: str, month: int, year: int, amount: int):
    uid = await get_internal_id(max_id)
    await AsyncORM.Operation.add(OperationBase(
        user_id=uid, type="income",
        month=month, year=year, cost=amount,
    ))

async def update_rate(max_id: str, rate: int):
    """Обновляем tax_rate напрямую."""
    await AsyncORM.User.update(max_id, rate)

async def get_rate(max_id: str) -> int:
    user = await AsyncORM.User.qet(max_id)
    return user.tax_rate if user else 0

async def nds_status(max_id: str) -> dict:
    """Безопасный расчёт статуса лимита НДС."""
    try:
        uid = await get_internal_id(max_id)
        year = dt.date.today().year
        income = await AsyncORM.Operation.sum_income(uid, year)
        avg = await AsyncORM.Operation.avg_income(uid, year)

        income = int(income or 0)
        avg = float(avg or 0)
        percent = income / LIMIT * 100

        if avg > 0 and income < LIMIT:
            months_left = (LIMIT - income) / avg
        else:
            months_left = 0

        exceeded = income >= LIMIT
        return {
            "percent": percent,
            "income": income,
            "avg": avg,
            "months_left": months_left,
            "exceeded": exceeded,
        }
    except Exception as e:
        logging.error(f"nds_status: {e}")
        return {"percent": 0, "income": 0, "avg": 0,
                "months_left": 0, "exceeded": False}

async def next_unfilled_month(max_id: str, year: int = YEAR_TRACK) -> Optional[int]:
    """Найти следующий незаполненный месяц."""
    try:
        uid = await get_internal_id(max_id)
        ops = await AsyncORM.Operation.get_all(uid)
        filled = set()
        for row in ops:
            obj = row[0] if isinstance(row, tuple) or hasattr(row, "__getitem__") else row
            if hasattr(obj, "year") and obj.year == year \
               and obj.type == TypeOperation.income:
                filled.add(obj.month)
        today = dt.date.today()
        start = today.month if today.year == year else 1
        for m in range(start, 13):
            if m not in filled:
                return m
        return None
    except Exception as e:
        logging.error(f"next_unfilled_month: {e}")
        return None

# ═══════════════════════════════════════════════════════════
#  Экран 3: Светофор
# ═══════════════════════════════════════════════════════════
async def show_semafor(max_id: str, chat_id: int):
    st = await nds_status(max_id)
    pct = st["percent"]
    inc = st["income"]
    avg = st["avg"]
    ml = st["months_left"]

    if st["exceeded"]:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔴 Лимит НДС превышен!\n"
                f"{pbar(100)}  {fmt_money(inc)} из 20 млн\n\n"
                f"Вы стали плательщиком НДС.\n"
                f"Выберите ставку — кнопкой ниже."
            ),
            attachments=kb(
                [("5%, без вычета", "rate_5"), ("22%, с вычетом", "rate_22")],
                [("Не знаю, объясните", "rate_explain")],
                [("Календарь", "calendar")],
            ),
        )
        return

    remaining = LIMIT - inc
    if avg > 0 and ml > 0:
        cur_m = dt.date.today().month
        fore_m = int(cur_m + ml)
        if fore_m > 12:
            fore_m -= 12
        nds_m = fore_m + 1
        if nds_m > 12:
            nds_m = 1
        forecast = (
            f"Прогноз: при среднем {fmt_money(avg)}/мес лимит "
            f"превышен в {MONTHS_PRED[fore_m]} → НДС с 1 {MONTHS_PRED[nds_m]} {YEAR_TRACK}"
        )
    elif avg > 0 and ml == 0:
        forecast = "Прогноз: лимит будет превышен в этом году"
    else:
        forecast = "Прогноз: пока нет данных — внесите доход"

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"{semafor(pct)} Лимит НДС: {pct:.0f}% использовано\n"
            f"{pbar(pct)}  {fmt_money(inc)} из 20 млн\n\n"
            f"Осталось без НДС: {fmt_money(remaining)}\n"
            f"{forecast}"
        ),
        attachments=main_kb(),
    )

# ═══════════════════════════════════════════════════════════
#  Экран 7: Календарь
# ═══════════════════════════════════════════════════════════
async def show_calendar(max_id: str, chat_id: int):
    lines = ["Ваши ближайшие сроки:\n"]

    usn_dates = []
    for label, m in [("аванс по УСН за 1 квартал", 4),
                     ("аванс по УСН за полугодие", 7),
                     ("аванс по УСН за 9 месяцев", 10)]:
        try:
            d = Payments.next_workday(dt.date(YEAR_TRACK, m, 28))
            if isinstance(d, dt.date):
                usn_dates.append((d, label))
                continue
        except Exception:
            pass
        usn_dates.append((dt.date(YEAR_TRACK, m, 28), label))
    for d, lbl in usn_dates:
        if d >= dt.date.today():
            ru_m = MONTHS_PRED[d.month]
            lines.append(f"📅 {d.day} {ru_m} {d.year} — {lbl}")

    try:
        fd = Payments.Fixed.date()
        fc = Payments.Fixed.cost()
        if isinstance(fd, dt.date) and fd >= dt.date.today():
            lines.append(f"📅 {fd.day} {MONTHS_PRED[fd.month]} {fd.year} — "
                         f"фиксированные взносы, {fmt_money(fc)}")
        else:
            raise Exception
    except Exception:
        lines.append(f"📅 28 декабря — фиксированные взносы, 57 390 ₽")

    lines.append("📅 1 июля — доп. 1% с дохода свыше 300 000 ₽ (если применимо)")

    rate = await get_rate(max_id)
    if rate > 0:
        lines.append("")
        lines.append("НДС:")
        decl_months = [(1, 25), (4, 25), (7, 25), (10, 25)]
        for mq, day in decl_months:
            try:
                d = dt.date(YEAR_TRACK, mq, day)
                if d >= dt.date.today():
                    lines.append(f"📅 {day} {MONTHS_PRED[mq]} — "
                                 f"декларация по НДС за квартал (электронно, через ЭДО)")
                    break
            except Exception:
                pass
        lines.append("📅 28 числа × 3 мес. — уплата НДС равными долями")

    await bot.send_message(
        chat_id=chat_id,
        text="\n".join(lines),
        attachments=kb(
            [("✅ Сделано: УСН", "done_usn"),
             ("✅ Сделано: взносы", "done_fixed")],
            [("◀️ Назад", "back_menu")],
        ),
    )

# ═══════════════════════════════════════════════════════════
#  Экран 8: Источники
# ═══════════════════════════════════════════════════════════
SOURCES = (
    "📋 Источники и допущения\n\n"
    "Все цифры и правила — из методических рекомендаций ФНС\n"
    "по НДС для УСН (2026) и раздела «УСН» на nalog.gov.ru.\n\n"
    "Актуально на 25.09.2026.\n\n"
    "⚠️ Это справочный расчёт, не консультация.\n\n"
    "Допущения:\n"
    "• Порог цвета: 🟢 < 70%, 🟡 70–90%, 🔴 > 90%\n"
    "• Лимит — 20 млн ₽ за календарный год\n"
    "• Доходы по патенту в расчёт лимита не входят\n"
    "• Не учитываются: ИП с сотрудниками,\n"
    "  ставки 0%/10%, крупные обороты 272,5–490,5 млн ₽"
)

# ═══════════════════════════════════════════════════════════
#  Экран 0: /start
# ═══════════════════════════════════════════════════════════
@dp.bot_started()
async def on_started(event: BotStarted):
    chat_id = event.chat.chat_id if hasattr(event, "chat") \
        else event.from_user.user_id
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "Привет! Я помогу ИП на УСН понять, когда наступит НДС, "
            "и не забыть про сроки.\n\n"
            "⚠️ Это справочный расчёт, не консультация.\n\n"
            "Начнём?"
        ),
        attachments=kb([("Начать", "start_ob")]),
    )

@dp.message_created(Command("start"))
async def cmd_start(event: MessageCreated):
    chat_id = event.message.recipient.chat_id
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "Привет! Я помогу ИП на УСН понять, когда наступит НДС, "
            "и не забыть про сроки.\n\n"
            "⚠️ Это справочный расчёт, не консультация.\n\n"
            "Начнём?"
        ),
        attachments=kb([("Начать", "start_ob")]),
    )

# ═══════════════════════════════════════════════════════════
#  Обработка inline-кнопок
# ═══════════════════════════════════════════════════════════
@dp.message_callback()
async def on_callback(event: MessageCallback):
    payload = event.callback.payload
    max_id = str(event.from_user.user_id)
    chat_id = event.message.recipient.chat_id

    try:
        await event.answer(notification="")
    except Exception:
        pass

    # ── Онбординг ──
    if payload == "start_ob":
        await bot.send_message(
            chat_id=chat_id,
            text="Вы ИП и применяете УСН?",
            attachments=kb([("Да", "usn_yes"), ("Нет", "usn_no")]),
        )

    elif payload == "usn_yes":
        await bot.send_message(
            chat_id=chat_id,
            text="Совмещаете УСН с патентом?",
            attachments=kb([("Да", "pat_yes"), ("Нет", "pat_no")]),
        )

    elif payload == "usn_no":
        await bot.send_message(
            chat_id=chat_id,
            text="Пока умею работать только с ИП на УСН 🙏\n"
                 "Если у вас УСН — нажмите /start и начните заново.",
        )

    elif payload == "pat_yes":
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ Доходы по патенту в расчёт лимита НДС пока не входят.\n"
                 "Я буду учитывать только доходы по УСН.\n",
        )
        await _ask_2025(chat_id, max_id)

    elif payload == "pat_no":
        await _ask_2025(chat_id, max_id)

    # ── Главное меню ──
    elif payload == "back_menu":
        await show_semafor(max_id, chat_id)

    # ── Ввод дохода ──
    elif payload == "add_income":
        m = await next_unfilled_month(max_id)
        if m is None:
            await bot.send_message(
                chat_id=chat_id,
                text="Все месяцы 2026 года заполнены! 🎉",
                attachments=main_kb(),
            )
            await show_semafor(max_id, chat_id)
        else:
            fsm.set(max_id, S.WAIT_INCOME)
            fsm.put(max_id, "month", m)
            await bot.send_message(
                chat_id=chat_id,
                text=f"Введите доход за {MONTHS[m]} 2026, ₽\n\n"
                     f"(просто числом, например: 1500000)",
                attachments=kb([("◀️ Отмена", "back_menu")]),
            )

    elif payload == "skip_income":
        fsm.set(max_id, S.MENU)
        await show_semafor(max_id, chat_id)

    # ── Что если ──
    elif payload == "what_if":
        fsm.set(max_id, S.WAIT_WHAT_IF)
        await bot.send_message(
            chat_id=chat_id,
            text="Введите сумму гипотетического поступления, ₽\n\n"
                 "(это не сохранится — только расчёт)",
            attachments=kb([("◀️ Отмена", "back_menu")]),
        )

    # ── Выбор ставки ──
    elif payload == "rate_5":
        await update_rate(max_id, 5)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ Ставка НДС: 5% (без вычета «входного» НДС)\n\n"
                "Применяется минимум 12 кварталов подряд.\n\n"
                "Теперь можно посчитать цену с НДС:"
            ),
            attachments=kb(
                [("Калькулятор НДС", "vat_calc")],
                [("◀️ В меню", "back_menu")],
            ),
        )

    elif payload == "rate_22":
        await update_rate(max_id, 22)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ Ставка НДС: 22% (с вычетом «входного» НДС)\n\n"
                "Применяется минимум 12 кварталов подряд.\n\n"
                "Теперь можно посчитать цену с НДС:"
            ),
            attachments=kb(
                [("Калькулятор НДС", "vat_calc")],
                [("◀️ В меню", "back_menu")],
            ),
        )

    elif payload == "rate_explain":
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🔹 5% — без вычета «входного» НДС\n"
                "Проще в учёте: не отслеживать НДС поставщиков.\n"
                "Выгодно при небольших закупках.\n\n"
                "🔹 22% — с вычетом «входного» НДС\n"
                "Выгоднее при крупных закупках: вычитаете НДС,\n"
                "уплаченный поставщикам. Сложнее: нужны счета-фактуры.\n\n"
                "Обе ставки — минимум 12 кварталов подряд.\n"
                "⚠️ Финальный выбор обсудите с бухгалтером."
            ),
            attachments=kb(
                [("5%, без вычета", "rate_5"), ("22%, с вычетом", "rate_22")],
                [("◀️ Назад", "back_menu")],
            ),
        )

    # ── Калькулятор НДС ──
    elif payload == "vat_calc":
        rate = await get_rate(max_id)
        if rate == 0:
            await bot.send_message(
                chat_id=chat_id,
                text="Сначала выберите ставку НДС.",
                attachments=kb(
                    [("5%", "rate_5"), ("22%", "rate_22")],
                    [("◀️ Назад", "back_menu")],
                ),
            )
        else:
            fsm.set(max_id, S.WAIT_VAT_PRICE)
            await bot.send_message(
                chat_id=chat_id,
                text=f"Введите цену без НДС, ₽\n\n(ваша ставка: {rate}%)",
                attachments=kb([("◀️ Отмена", "back_menu")]),
            )

    # ── Календарь ──
    elif payload == "calendar":
        await show_calendar(max_id, chat_id)

    elif payload.startswith("done_"):
        labels = {
            "done_usn": "Аванс по УСН",
            "done_fixed": "Фиксированные взносы",
            "done_nds_decl": "Декларация по НДС",
            "done_nds_pay": "Уплата НДС",
        }
        lbl = labels.get(payload, "Напоминание")
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ «{lbl}» отмечено. Напоминание отключено.",
            attachments=kb([("◀️ Назад", "back_menu")]),
        )

    # ── Источники ──
    elif payload == "sources":
        await bot.send_message(
            chat_id=chat_id,
            text=SOURCES,
            attachments=kb([("◀️ Назад", "back_menu")]),
        )


# ═══════════════════════════════════════════════════════════
#  Вспомогательная — запрос дохода 2025
# ═══════════════════════════════════════════════════════════
async def _ask_2025(chat_id: int, max_id: str):
    fsm.set(max_id, S.INCOME_2025)
    await bot.send_message(
        chat_id=chat_id,
        text="Какой был ваш доход за 2025 год, ₽ (примерно)?\n\n"
             "(просто числом, например: 5000000)",
    )

# ═══════════════════════════════════════════════════════════
#  Обработка текстовых сообщений
# ═══════════════════════════════════════════════════════════
@dp.message_created()
async def on_text(event: MessageCreated):
    max_id = str(event.from_user.user_id)
    chat_id = event.message.recipient.chat_id
    text = (event.message.body.text or "").strip()
    if not text:
        return

    state = fsm.get(max_id)

    # ── Ввод дохода за 2025 ──
    if state == S.INCOME_2025:
        inc = safe_int(text)
        if inc is None:
            await bot.send_message(
                chat_id=chat_id,
                text="Не понял число. Введите доход за 2025 числом, "
                     "например: 5000000",
            )
            return

        await ensure_user(max_id)

        if inc >= LIMIT:
            # Ветка Б — уже плательщик
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"Доход за 2025 — {fmt_money(inc)}.\n"
                    f"Это ≥ 20 млн ₽ — с 01.01.2026 вы уже плательщик НДС.\n\n"
                    f"Выберите ставку:"
                ),
                attachments=kb(
                    [("5%, без вычета", "rate_5"), ("22%, с вычетом", "rate_22")],
                    [("Не знаю, объясните", "rate_explain")],
                ),
            )
        else:
            # Ветка А — отслеживаем 2026
            fsm.set(max_id, S.WAIT_INCOME)
            m = await next_unfilled_month(max_id) or 1
            fsm.put(max_id, "month", m)
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"Доход за 2025 — {fmt_money(inc)}.\n"
                    f"Это меньше 20 млн ₽ — НДС пока не платите.\n\n"
                    f"Давайте отслеживать 2026.\n"
                    f"Введите доход за {MONTHS[m]} 2026, ₽"
                ),
                attachments=kb([("Пропустить", "skip_income")]),
            )

    # ── Ввод дохода за месяц ──
    elif state == S.WAIT_INCOME:
        amount = safe_int(text)
        if amount is None:
            await bot.send_message(
                chat_id=chat_id,
                text="Не понял число. Введите доход числом, например: 1500000",
            )
            return

        month = fsm.fetch(max_id, "month") or dt.date.today().month
        try:
            await save_income(max_id, month, YEAR_TRACK, amount)
        except Exception as e:
            logging.error(f"save_income: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text="Ошибка сохранения. Попробуйте ещё раз.",
            )
            return

        fsm.set(max_id, S.MENU)

        st = await nds_status(max_id)
        if st["exceeded"]:
            next_m = month + 1 if month < 12 else 1
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"Записал: {fmt_money(amount)} за {MONTHS[month]} ✅\n\n"
                    f"🔴 Доход превысил 20 млн ₽!\n"
                    f"С 1 {MONTHS_PRED[next_m]} {YEAR_TRACK} "
                    f"вы становитесь плательщиком НДС.\n\n"
                    f"Выберите ставку:"
                ),
                attachments=kb(
                    [("5%, без вычета", "rate_5"),
                     ("22%, с вычетом", "rate_22")],
                    [("Не знаю, объясните", "rate_explain")],
                ),
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=f"Записал: {fmt_money(amount)} за {MONTHS[month]} ✅",
            )
            await show_semafor(max_id, chat_id)

    # ── Что если ──
    elif state == S.WAIT_WHAT_IF:
        amount = safe_int(text)
        if amount is None:
            await bot.send_message(
                chat_id=chat_id,
                text="Не понял число. Введите сумму числом, например: 2000000",
            )
            return

        cur = await nds_status(max_id)
        new_inc = cur["income"] + amount
        new_pct = min(new_inc / LIMIT * 100, 100)

        if cur["avg"] > 0 and cur["months_left"] > 0:
            new_rem = max(LIMIT - new_inc, 0)
            new_ml = new_rem / cur["avg"] if new_rem > 0 else 0
            diff = int(cur["months_left"] - new_ml)
            if new_inc >= LIMIT:
                diff_text = "Лимит будет превышен!"
            elif diff > 0:
                diff_text = f"Лимит превысите на {diff} мес. раньше"
            elif diff < 0:
                diff_text = f"Срок превышения позже на {abs(diff)} мес."
            else:
                diff_text = "Сроки не изменятся"
        else:
            diff_text = "Недостаточно данных"

        fsm.set(max_id, S.MENU)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"Если поступит {fmt_money(amount)}:\n\n"
                f"{semafor(new_pct)} Лимит: {new_pct:.0f}%\n"
                f"{pbar(new_pct)}  {fmt_money(new_inc)} из 20 млн\n\n"
                f"Было: {cur['percent']:.0f}%\n"
                f"{diff_text}\n\n"
                f"(сумма не сохранена)"
            ),
            attachments=main_kb(),
        )

    # ── Калькулятор НДС ──
    elif state == S.WAIT_VAT_PRICE:
        price = safe_int(text)
        if price is None:
            await bot.send_message(
                chat_id=chat_id,
                text="Не понял число. Введите цену числом, например: 10000",
            )
            return

        rate = await get_rate(max_id)
        if rate == 0:
            await bot.send_message(
                chat_id=chat_id,
                text="Сначала выберите ставку НДС.",
                attachments=kb(
                    [("5%", "rate_5"), ("22%", "rate_22")],
                    [("◀️ Назад", "back_menu")],
                ),
            )
            return

        r = Decimal(rate)
        p = Decimal(price)
        vat = (p * r / 100).quantize(Decimal("1.00"))
        with_vat = (p + vat).quantize(Decimal("1.00"))

        fsm.set(max_id, S.MENU)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"Цена без НДС: {fmt_money(p)}\n"
                f"Ставка: {rate}%\n\n"
                f"Сумма НДС: {fmt_money(vat)}\n"
                f"Цена с НДС: {fmt_money(with_vat)}\n\n"
                f"⚠️ Без учёта вычетов входного НДС.\n"
                f"Финальную цену обсудите с бухгалтером."
            ),
            attachments=kb(
                [("Ещё расчёт", "vat_calc")],
                [("◀️ В меню", "back_menu")],
            ),
        )

    # ── Нет состояния ──
    else:
        user = await AsyncORM.User.qet(max_id)
        if user:
            await show_semafor(max_id, chat_id)
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="Нажмите /start, чтобы начать.",
            )

# ═══════════════════════════════════════════════════════════
#  Запуск
# ═══════════════════════════════════════════════════════════
async def main():
    logging.info("Бот «Светофор НДС» запускается…")
    await database.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
