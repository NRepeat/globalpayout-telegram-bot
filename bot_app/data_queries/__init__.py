import asyncio
import os
from collections.abc import AsyncGenerator
import aiomysql
from aiomysql import Connection, Pool
from bot_app.config import settings


class Database:
    def __init__(self):
        self._pool: Pool = None

    async def create_pool(self):
        if not self._pool:
            self._pool = await aiomysql.create_pool(
                host=settings.DB_HOST,
                port=int(settings.DB_PORT),
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                db=settings.DB_NAME,
                autocommit=True,
                minsize=1,
                maxsize=10,
                loop=asyncio.get_event_loop(),
            )

    async def close(self):
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()

    async def get_connection(self) -> AsyncGenerator[Connection, None]:
        if not self._pool:
            await self.create_pool()
        async with self._pool.acquire() as connection:
            connection: Connection
            connection.cursorclass = aiomysql.DictCursor  # Set DictCursor as default
            yield connection


db = Database()


async def get_db_connection() -> AsyncGenerator[Connection, None]:
    async for conn in db.get_connection():
        yield conn
