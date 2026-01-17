from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.misc import aiogram_router


@aiogram_router.message(Command("start"))
async def handle_start(message: Message, db_connection: Connection, state: FSMContext):
    print("start",message)
    await state.clear()
    if not await get_user_by_id(db_connection, message.from_user.id):
        await save_user(db_connection, message.from_user)
    await message.answer("start")
