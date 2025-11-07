from typing import Optional

from aiogram.types import User
from aiomysql import Connection, Cursor

from bot_app.config import settings
from bot_app.schemas.user import SavedUser


async def save_user(conn: Connection, aiogram_user: User) -> SavedUser:
    query = "INSERT INTO data_tg_user (user_id, name, user_name, senior_operator, bot_admin) VALUES (%s, %s, %s, %s, %s)"
    params = (
        aiogram_user.id,
        aiogram_user.full_name,
        f"@{aiogram_user.username}" if aiogram_user.username else None,
        False,
        aiogram_user.id in settings.ADMINS_ID,
    )
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, params)
        await conn.commit()
    return SavedUser(
        user_id=aiogram_user.id,
        name=aiogram_user.full_name,
        user_name=f"@{aiogram_user.username}" if aiogram_user.username else None,
        senior_operator=False,
        bot_admin=aiogram_user.id in settings.ADMINS_ID,
    )


async def get_user_by_id(conn: Connection, user_id: str) -> Optional[SavedUser]:
    query = "SELECT user_id, name, user_name, senior_operator, bot_admin FROM data_tg_user WHERE user_id = %s"
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, user_id)
        saved_user = await cur.fetchone()
    if not saved_user:
        return None
    return SavedUser(**saved_user)
