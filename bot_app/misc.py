from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import TokenBasedRequestHandler

from bot_app.config import settings
from bot_app.exchange_methods import BoxExchanger


async def log_out_from_telegram_api():
    temp_bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        await temp_bot.get_me()
    except TelegramBadRequest as e:
        if "Logged out" in e.message:
            await temp_bot.session.close()
            return
        raise
    try:
        await temp_bot.log_out()
    finally:
        await temp_bot.session.close()


aiogram_router = Router()
# Rates autoposting chat: all bot commands are ignored there, only the cron posts (ARG-58)
aiogram_router.message.filter(F.chat.id != settings.RATES_POSTING_CHAT_ID)

if settings.USE_LOCAL_BOT_API:
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(settings.LOCAL_BOT_API, is_local=True)
    )
else:
    session = AiohttpSession()
bot_settings = {
    "session": session,
    "default": DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True),
}

# TODO think about redis if we will need any states at all?
storage = MemoryStorage()
aiogram_bot_instance = Bot(settings.TELEGRAM_BOT_TOKEN, **bot_settings)

# Create dispatcher for handling multiple bots
multibot_dispatcher = Dispatcher(storage=storage)
multibot_dispatcher.include_router(aiogram_router)

# Register handler for processing updates from different bots
webhook_handler = TokenBasedRequestHandler(
    dispatcher=multibot_dispatcher,
    bot_settings=bot_settings,
)
box_exchanger_client = BoxExchanger()
