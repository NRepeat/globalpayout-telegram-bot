import asyncio
from contextlib import asynccontextmanager, suppress

import uvicorn
from aiogram.types import BotCommand
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bot_app.config import __version__, settings
from bot_app.data_queries import db
from bot_app.misc import aiogram_bot_instance, log_out_from_telegram_api
from bot_app.rates_posting import rates_posting_scheduler
from bot_app.routes.route_rates import rates_router
from bot_app.routes.route_transaction import transaction_router
from bot_app.routes.system.bot_settings import root_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Пустой WEBHOOK_HOST — локальная разработка: без HTTPS-туннеля вебхук не
    # зарегистрировать, поэтому переходим на long-polling тем же диспетчером.
    # Прод с заданным WEBHOOK_HOST работает как раньше.
    polling_task = None
    if not settings.WEBHOOK_HOST:
        from aiogram import BaseMiddleware

        from bot_app.misc import multibot_dispatcher

        # В вебхуке db_connection хендлерам подкладывает FastAPI-роут через
        # feed_raw_update; у поллинга роута нет — даём соединение на каждый
        # апдейт middleware'ом, из того же пула.
        class DbConnectionMiddleware(BaseMiddleware):
            async def __call__(self, handler, event, data):
                async for conn in db.get_connection():
                    data["db_connection"] = conn
                    return await handler(event, data)

        multibot_dispatcher.update.outer_middleware(DbConnectionMiddleware())
        # пул — до первого апдейта, иначе гонка на старте
        await db.create_pool()
        await aiogram_bot_instance.delete_webhook(drop_pending_updates=False)
        polling_task = asyncio.create_task(
            multibot_dispatcher.start_polling(
                aiogram_bot_instance,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "chat_member",
                    "my_chat_member",
                ],
            )
        )
    else:
        bot_webhook_url = f"{settings.WEBHOOK_HOST}/bot-webhook/"
        current_webhook_info = await aiogram_bot_instance.get_webhook_info()
        if current_webhook_info.url != bot_webhook_url:
            await aiogram_bot_instance.set_webhook(
                bot_webhook_url,
                secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "chat_member",
                    "my_chat_member",
                ],
            )
    if settings.USE_LOCAL_BOT_API:
        await log_out_from_telegram_api()

    my_commands = await aiogram_bot_instance.get_my_commands()
    print(my_commands)
    commands_list = [
        BotCommand(command="start", description="Почати роботу"),
        BotCommand(command="rate", description="налаштування напрямів"),
        BotCommand(command="groups", description="Групи"),
        BotCommand(command="report", description="Звіт"),
        BotCommand(command="stats", description="Статистика"),
    ]
    # if my_commands != commands_list:
    await aiogram_bot_instance.set_my_commands(commands_list)

    await db.create_pool()
    rates_posting_task = asyncio.create_task(rates_posting_scheduler())
    yield
    if polling_task is not None:
        polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await polling_task
    rates_posting_task.cancel()
    with suppress(asyncio.CancelledError):
        await rates_posting_task
    await db.close()
    await aiogram_bot_instance.session.close()


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    version=__version__,
    swagger_ui_parameters={"syntaxHighlight": False},
    root_path=settings.FASTAPI_BASE_PATH,
    title="Yeezy Pay Applications Telegram Bot API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

app.include_router(root_router)
app.include_router(transaction_router)
app.include_router(rates_router)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.SERVER_ADDRESS, port=int(settings.SERVER_PORT))
