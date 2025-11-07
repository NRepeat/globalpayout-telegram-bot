from typing import Optional

from aiogram.types import Chat
from aiomysql import Connection, Cursor

from bot_app.schemas.tg_chat import SavedChat


async def save_chat(conn: Connection, aiogram_chat: Chat) -> SavedChat:
    query = "INSERT IGNORE INTO tg_chat (chat_tg_id, chat_title, chat_user_name, transaction_target) VALUES (%s, %s, %s, %s)"
    params = (
        aiogram_chat.id,
        aiogram_chat.title,
        f"@{aiogram_chat.username}" if aiogram_chat.username else None,
        False,
    )
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, params)
        await conn.commit()
        last_id = cur.lastrowid
    return SavedChat(
        record_id=last_id,
        chat_tg_id=aiogram_chat.id,
        chat_title=aiogram_chat.title,
        chat_user_name=f"@{aiogram_chat.username}" if aiogram_chat.username else None,
        transaction_target=False,
    )


async def update_chat_tg_id(conn: Connection, record_id: int, new_channel_tg_id: int):
    query = "UPDATE tg_chat SET chat_tg_id = %s WHERE record_id = %s"
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (new_channel_tg_id, record_id))
        await conn.commit()


async def get_chat_by_tg_id(conn: Connection, chat_tg_id: int) -> Optional[SavedChat]:
    query = "SELECT record_id, chat_tg_id, chat_title, chat_user_name, transaction_target FROM tg_chat WHERE chat_tg_id = %s"
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (chat_tg_id,))
        saved_chat = await cur.fetchone()
    if not saved_chat:
        return None
    return SavedChat(**saved_chat)


async def get_transaction_target_chat(conn: Connection) -> Optional[SavedChat]:
    query = "SELECT record_id, chat_tg_id, chat_title, chat_user_name, transaction_target FROM tg_chat WHERE transaction_target = 1"
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query)
        saved_chat = await cur.fetchone()
    if not saved_chat:
        return None
    return SavedChat(**saved_chat)
