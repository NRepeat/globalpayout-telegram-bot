from aiogram.filters import PROMOTED_TRANSITION, ChatMemberUpdatedFilter, Filter
from aiogram.types import (
    ChatMemberUpdated,
    Message,
)

from bot_app.data_queries import Connection
from bot_app.data_queries.chat import get_chat_by_tg_id, save_chat, update_chat_tg_id
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.misc import aiogram_bot_instance, aiogram_router
from bot_app.schemas.tg_chat import SavedChat


class ChatMigration(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.migrate_to_chat_id is not None


@aiogram_router.my_chat_member(ChatMemberUpdatedFilter(PROMOTED_TRANSITION))
async def on_bot_promoted(update: ChatMemberUpdated, db_connection: Connection):
    if update.chat.type not in ["supergroup", "group"]:
        return
    tg_chat_data: SavedChat = await save_chat(
        db_connection,
        update.chat,
    )
    try:
        await aiogram_bot_instance.send_message(
            update.from_user.id,
            f"✅ Чат {tg_chat_data.chat_title} успішно додано в панель адміністратора",
        )
    except Exception:
        pass


@aiogram_router.message(ChatMigration())
async def get_migration_from_chat_id(message: Message, db_connection: Connection):
    tg_chat_data: SavedChat = await get_chat_by_tg_id(
        db_connection, message.migrate_from_chat_id
    )
    if tg_chat_data is None:
        return

    await update_chat_tg_id(
        db_connection, tg_chat_data.record_id, message.migrate_to_chat_id
    )


@aiogram_router.chat_member()
async def on_user_join(update: ChatMemberUpdated, db_connection: Connection):
    user = await get_user_by_id(db_connection, update.new_chat_member.user.id)
    if not user:
        await save_user(db_connection, update.new_chat_member.user)
        return
