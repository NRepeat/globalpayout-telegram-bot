from contextlib import asynccontextmanager

import uvicorn
from aiogram.types import BotCommand
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bot_app.config import __version__, settings
from bot_app.data_queries import db
from bot_app.misc import aiogram_bot_instance, log_out_from_telegram_api
from bot_app.routes.route_rates import rates_router
from bot_app.routes.route_transaction import transaction_router
from bot_app.routes.system.bot_settings import root_router


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    yield
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
