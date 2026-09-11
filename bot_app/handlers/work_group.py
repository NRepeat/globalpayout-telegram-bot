"""Особиста робоча група оператора.

Заявка публікується у спільному чаті, але робота по ній — вибір площадки,
ID ордера, квитанція — має йти у групі того, хто її взяв: у спільному чаті
все це бачать усі, включно з іншими операторами.

Команда називається так само, як у сусідніх ботів (`/register` у greatbot,
`/start_work_group` у klim-bot), щоб у спільній групі не було трьох різних
імен для однієї дії.
"""

from aiogram.filters import Command
from aiogram.types import Message

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id, save_user, set_work_group
from bot_app.misc import aiogram_router


@aiogram_router.message(Command("register", "start_work_group"))
async def handle_register_work_group(message: Message, db_connection: Connection):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Команда працює тільки в групі")
        return

    # кожен реєструє групу собі: це не про доступ до чужих грошей, а про те,
    # де людині зручно працювати
    user = await get_user_by_id(db_connection, message.from_user.id)
    if not user:
        user = await save_user(db_connection, message.from_user)

    await set_work_group(db_connection, message.from_user.id, message.chat.id)
    await message.answer(
        "✅ Робоча група зареєстрована — узяті вами заявки приходитимуть сюди.\n"
        f"Chat ID: <code>{message.chat.id}</code>"
    )


@aiogram_router.message(Command("my_work_group"))
async def handle_show_work_group(message: Message, db_connection: Connection):
    user = await get_user_by_id(db_connection, message.from_user.id)
    if not user or not user.work_group_chat_id:
        await message.answer(
            "❌ Робоча група не задана — заявки залишаються у спільному чаті.\n"
            "Виконайте /register у потрібній групі."
        )
        return
    await message.answer(
        f"Ваша робоча група: <code>{user.work_group_chat_id}</code>\n"
        f"Цей чат: <code>{message.chat.id}</code>"
    )
