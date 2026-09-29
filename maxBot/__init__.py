import asyncio
from maxbot_api_client_python import API, Config
from maxbot_chatbot_python import Bot, MapStateManager

from core.config import settings, Settings

CONFIG = Config(
    base_url="https://platform-api2.max.ru/",
    token= Settings.VK_MAX_TOKEN,
    ratelimiter=25,
    timeout=35
)

async def chatBotMax():

    async with API(CONFIG) as api_client:
        bot = Bot(api_client)
        bot.state_manager = MapStateManager(init_data={})

        # Пример обработки команды /start с вызовом вашей БД
        @bot.router.message(command="start")
        async def handle_start(message, context):
            user_id = message.sender.id

            # Вызов вашего существующего сервиса
            user_exists = await UserService.check_user(user_id)
            if not user_exists:
                await UserService.register_new_user(user_id, message.sender.name)

            await message.reply("Привет! Вы успешно авторизованы в системе.")

        # Пример обработки обычного текста (интеграция с сервисной логикой)
        @bot.router.message()
        async def handle_any_message(message, context):
            # Передаем текст в вашу бизнес-логику
            result = await OrderService.search_product(text=message.text)

            if result:
                await message.reply(f"Найден товар: {result.name} за {result.price} руб.")
            else:
                await message.reply("По вашему запросу ничего не найдено.")

        # Запуск Long Polling для прослушивания обновлений
        polling_task = asyncio.create_task(bot.start_polling())
        try:
            await polling_task
        except asyncio.CancelledError:
            pass