from aiogram.filters import Command
from aiogram.types import Message

from bot_app.config import settings
from bot_app.data_queries import Connection
from bot_app.data_queries.chat import get_transaction_target_chat, set_transaction_target
from bot_app.data_queries.user import get_user_by_id
from bot_app.misc import aiogram_router


# `register_main` — то же имя команды, что у greatbot и klim-bot: когда все
# три бота сидят в одной группе, разные имена для одного действия путают.
@aiogram_router.message(Command("set_transaction_chat", "register_main"))
async def handle_set_transaction_chat(message: Message, db_connection: Connection):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Команда працює тільки в групі")
        return

    # Только владельцы: команда уводит весь поток новых заявок в другой чат.
    # Ошибка чатом здесь дороже, чем отсутствие команды у админов.
    if message.from_user.id not in settings.owner_ids:
        await message.answer("⛔ Команда доступна лише власникам")
        return

    await set_transaction_target(db_connection, message.chat)
    await message.answer(
        f"✅ Нові заявки надходитимуть сюди\nChat ID: <code>{message.chat.id}</code>"
    )


@aiogram_router.message(Command("transaction_chat"))
async def handle_show_transaction_chat(message: Message, db_connection: Connection):
    user = await get_user_by_id(db_connection, message.from_user.id)
    if not user or not user.bot_admin:
        await message.answer("У вас немає прав")
        return

    target_chat = await get_transaction_target_chat(db_connection)
    if target_chat is None:
        await message.answer(
            "❌ Цільовий чат не заданий — заявки не публікуються.\n"
            "Виконайте /set_transaction_chat у потрібній групі."
        )
        return

    await message.answer(
        f"Цільовий чат: {target_chat.chat_title}\n"
        f"Chat ID: <code>{target_chat.chat_tg_id}</code>\n"
        f"Цей чат: <code>{message.chat.id}</code>"
    )
