# 🚦 Светофор НДС

Бот для платформы **MAX**, который помогает ИП на УСН отслеживать приближение к лимиту НДС (20 млн ₽ в год) и не забывать о сроках платежей.

## Возможности

- **Онбординг** — определяет статус ИП (УСН, патент), фиксирует доход за прошлый год
- **Светофор** — наглядный прогресс-бар: 🟢 (< 70%) → 🟡 (70–90%) → 🔴 (> 90%) от лимита 20 млн ₽
- **Ввод дохода помесячно** — бот подсказывает следующий незаполненный месяц
- **Что если** — гипотетический расчёт: как разовое поступление сдвинет срок перехода на НДС
- **Выбор ставки НДС** — 5% (без вычета) или 22% (с вычетом входного НДС)
- **Калькулятор НДС** — считает цену с НДС от введённой суммы
- **Календарь** — ближайшие сроки: авансы по УСН, фиксированные взносы, доп. 1%, декларации и уплата НДС
- **Источники** — ссылки на методические рекомендации ФНС

## Технологии

| Компонент | Технология |
|---|---|
| Мессенджер | MAX (VK Max) |
| Библиотека бота | [maxapi](https://github.com/love-apples/maxapi) |
| База данных | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (async) |
| Конфигурация | Pydantic Settings + `settings.env` |
| Контейнеризация | Docker + Docker Compose |

## Структура проекта

```
svetofor-nds/
├── bot.py                  # основной файл бота (хендлеры, FSM, клавиатуры)
├── services/
│   └── logic.py            # бизнес-логика: расчёт дат, НДС, взносов
├── core/
│   └── config.py           # Pydantic Settings (чтение settings.env)
├── database/
│   ├── database.py         # engine, session_factory
│   ├── models.py           # SQLAlchemy-модели (UserBase, OperationBase)
│   └── queries.py          # AsyncORM — CRUD-операции
├── settings.env            # конфигурация (токены, параметры БД)
├── requirements.txt        # Python-зависимости
├── Dockerfile              # образ бота
├── docker-compose.yml      # оркестрация: бот + PostgreSQL
├── .dockerignore
└── README.md
```

## Быстрый старт

### Локально (без Docker)

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Заполнить settings.env
cp settings.env.example settings.env
#    указать VK_MAX_TOKEN и параметры БД

# 3. Создать таблицы (один раз)
python -c "import asyncio; from database.queries import AsyncORM; asyncio.run(AsyncORM.create_tables())"

# 4. Запустить бота
python bot.py
```

### Через Docker

```bash
# 1. Заполнить settings.env
cp settings.env.example settings.env

# 2. Поднять бота + БД
docker compose up -d --build

# 3. Смотреть логи
docker compose logs -f bot

# 4. Остановить
docker compose down
```

При первом запуске Docker автоматически:
- создаёт PostgreSQL-контейнер с пользователем и базой
- поднимает бот-контейнер, который создаёт таблицы в БД
- устанавливает сертификаты Минцифры для доступа к API MAX

## Конфигурация

### settings.env

```env
# Токен бота MAX
VK_MAX_TOKEN=ваш_токен_из_business_max_ru

# Параметры базы данных (локально)
DB_HOST=localhost
DB_PORT=5432
DB_USER=svetofor
DB_PASS=svetofor_secret
DB_NAME=svetofor_db
```

В Docker параметры БД перекрываются в `docker-compose.yml` — `DB_HOST` меняется на `db` (имя контейнера). Менять `settings.env` для Docker не нужно.

### Переменные окружения (приоритет выше settings.env)

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `VK_MAX_TOKEN` | Токен бота MAX | — |
| `DB_HOST` | Адрес PostgreSQL | `localhost` |
| `DB_PORT` | Порт PostgreSQL | `5432` |
| `DB_USER` | Пользователь БД | `svetofor` |
| `DB_PASS` | Пароль БД | `svetofor_secret` |
| `DB_NAME` | Имя базы | `svetofor_db` |
| `SSL_CERT_FILE` | Путь к SSL-сертификатам | системный |
| `REQUESTS_CA_BUNDLE` | То же для requests | системный |

## FSM-состояния

| Состояние | Описание |
|---|---|
| `INCOME_2025` | Ввод дохода за 2025 год (онбординг) |
| `WAIT_INCOME` | Ввод дохода за месяц 2026 |
| `WAIT_WHAT_IF` | Ввод гипотетической суммы |
| `WAIT_VAT_PRICE` | Ввод цены без НДС для калькулятора |
| `MENU` | Главное меню (светофор) |

## Логика работы

```
Пользователь нажимает «Начать»
  → Онбординг: УСН? → Патент? → Доход за 2025?
  → Если доход < 20 млн: отслеживание 2026 (Ветка А)
  → Если доход ≥ 20 млн: выбор ставки НДС (Ветка Б)

Ветка А:
  Ввод дохода помесячно → Светофор → обновление прогресса
  При превышении лимита → выбор ставки НДС → калькулятор

Ветка Б:
  Выбор ставки → калькулятор НДС → календарь с НДС-сроками
```

## Команды бота

| Команда | Действие |
|---|---|
| `/start` | Перезапуск онбординга |

Остальное взаимодействие — через inline-кнопки.

## Известные баги в `logic.py`

В `services/logic.py` есть несколько багов, которые `bot.py` обходит безопасными обёртками:

| Баг | Описание |
|---|---|
| `next_workday` | `payment_date = dt.timedelta(days=1)` перезаписывает дату вместо `+=` |
| `check_nds` | `Decimal(income) / 20*10**6` даёт число в миллиарды процентов |
| `check_nds` | Падает на `Decimal(None)`, если данных за год нет |
| `User.update` | `session.get` по не-первичному ключу + несуществующее поле `NDS_payer` |
| `create_tables` | `drop_all` удаляет все данные при каждом запуске |

## Сертификаты Минцифры

API MAX (`platform-api2.max.ru`) требует российские SSL-сертификаты. В Docker они устанавливаются автоматически. На локальной машине:

```bash
# Скачать
wget https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt
wget https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt

# Установить (Windows: двойной клик → Локальный компьютер → Доверенные корневые)
# Или через переменные окружения:
export SSL_CERT_FILE=/путь/к/russian_trusted_root_ca_pem.crt
export REQUESTS_CA_BUNDLE=/путь/к/russian_trusted_root_ca_pem.crt
```

## Лицензия

Проект создан для внутреннего использования.

---

⚠️ Бот предоставляет справочный расчёт, а не налоговую консультацию. Финальные решения обсуждайте с бухгалтером.
