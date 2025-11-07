from typing import Optional

from aiomysql import Connection, Cursor


async def get_access_key(conn: Connection, key: str) -> Optional[str]:
    query = "SELECT api_key FROM api_allowed_keys WHERE api_key = %s "
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (key,))
        access_key = await cur.fetchone()
    return access_key
