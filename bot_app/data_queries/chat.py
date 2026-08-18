from typing import Optional

from aiogram.types import Chat
from aiomysql import Connection, Cursor

from bot_app.schemas.tg_chat import SavedChat


async def _next_record_id(cur: Cursor) -> int:
    """tg_chat.record_id is a plain BIGINT primary key, not AUTO_INCREMENT,
    so every INSERT has to carry its own id."""
    await cur.execute("SELECT COALESCE(MAX(record_id), -1) + 1 AS next_id FROM tg_chat")
    row = await cur.fetchone()
    return row["next_id"] if isinstance(row, dict) else row[0]


async def save_chat(conn: Connection, aiogram_chat: Chat) -> SavedChat:
    query = "INSERT IGNORE INTO tg_chat (record_id, chat_tg_id, chat_title, chat_user_name, transaction_target) VALUES (%s, %s, %s, %s, %s)"
    async with conn.cursor() as cur:
        cur: Cursor
        record_id = await _next_record_id(cur)
        params = (
            record_id,
            aiogram_chat.id,
            aiogram_chat.title,
            f"@{aiogram_chat.username}" if aiogram_chat.username else None,
            False,
        )
        await cur.execute(query, params)
        await conn.commit()
    return SavedChat(
        record_id=record_id,
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


async def set_transaction_target(conn: Connection, aiogram_chat: Chat) -> None:
    """Make this chat the only target for new transactions."""
    upsert_query = """
    INSERT INTO tg_chat (record_id, chat_tg_id, chat_title, chat_user_name, transaction_target)
    VALUES (%s, %s, %s, %s, 1)
    ON DUPLICATE KEY UPDATE
        chat_title = VALUES(chat_title),
        chat_user_name = VALUES(chat_user_name),
        transaction_target = 1
    """
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute("UPDATE tg_chat SET transaction_target = 0")
        params = (
            await _next_record_id(cur),
            aiogram_chat.id,
            aiogram_chat.title,
            f"@{aiogram_chat.username}" if aiogram_chat.username else None,
        )
        await cur.execute(upsert_query, params)
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
