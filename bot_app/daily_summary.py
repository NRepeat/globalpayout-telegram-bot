"""Свой раздел суточной сводки для exchange-check.

Сводку по всем трём ботам собирает сервис, а не бот: у каждого своя база и свой
формат, и склеивать их в боте значит держать в нём знание о двух чужих
бизнесах. Присылаем готовые строки про себя — что считать своим объёмом,
решает тот, кто его считает.

Отправляем в 23:50, чуть раньше, чем greatbot забирает сводку (23:55), иначе
наш раздел не успеет доехать и в отчёте будет «не прислал».
"""

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiohttp
from aiomysql import Connection, Cursor

from bot_app.config import settings
from bot_app.data_queries import get_db_connection

logger = logging.getLogger(__name__)

SEND_AT = (23, 50)

DAY_QUERY = """
SELECT
    COALESCE(tg_user.user_name, CAST(t.manager_id AS CHAR), 'без оператора') AS manager,
    COALESCE(t.close_account, 'без площадки')                                AS account,
    COUNT(*)                                                                 AS cnt,
    COALESCE(SUM(COALESCE(t.usdt_amount, 0)), 0)                             AS amount
FROM exchange_transaction t
JOIN data_status ON t.status_id = data_status.record_id
LEFT JOIN data_tg_user tg_user ON t.manager_id = tg_user.user_id
WHERE data_status.status_code = 'completed'
  AND t.created_at >= CURRENT_DATE()
GROUP BY manager, account
"""

UNCLOSED_QUERY = """
SELECT COUNT(*) AS cnt
FROM exchange_transaction t
JOIN data_status ON t.status_id = data_status.record_id
WHERE data_status.status_code IN ('created', 'in_progress')
"""


def build_lines(rows, unclosed: int) -> list[str]:
    """Строки раздела: объём, разрез по операторам и по площадкам."""
    total_cnt = sum(int(r["cnt"]) for r in rows)
    total_amount = sum(float(r["amount"]) for r in rows)
    lines = [f"💰 Закрыто заявок: {total_cnt} на {total_amount:.2f} USDT"]

    by_manager: dict[str, list[float]] = {}
    by_account: dict[str, list[float]] = {}
    for row in rows:
        for bucket, key in ((by_manager, row["manager"]), (by_account, row["account"])):
            acc = bucket.setdefault(str(key), [0, 0.0])
            acc[0] += int(row["cnt"])
            acc[1] += float(row["amount"])

    for manager, (cnt, amount) in by_manager.items():
        lines.append(f"👤 {manager} — {cnt} заявок, {amount:.2f} USDT")
    for account, (cnt, amount) in by_account.items():
        lines.append(f"🏦 {account} — {cnt} заявок, {amount:.2f} USDT")
    if unclosed:
        lines.append(f"⚠️ Незакрытых заявок: {unclosed}")
    return lines


async def build_slice(conn: Connection) -> dict:
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(DAY_QUERY)
        rows = await cur.fetchall()
        await cur.execute(UNCLOSED_QUERY)
        unclosed_row = await cur.fetchone()
    unclosed = int(unclosed_row["cnt"] if unclosed_row else 0)
    return {
        "workspace": "globalpayout",
        "title": "GlobalPayout",
        "date": "",  # день считает сервис — у ботов свои часы и пояса
        "at": "",
        "lines": build_lines(rows, unclosed),
        "unclosed": unclosed,
    }


async def push_slice() -> None:
    if not settings.EXCHANGE_CHECK_URL:
        return
    slice_ = None
    async for conn in get_db_connection():
        slice_ = await build_slice(conn)
        break
    if slice_ is None:
        return
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{settings.EXCHANGE_CHECK_URL}/report/day",
            json=slice_,
            headers={"X-Secret": settings.EXCHANGE_CHECK_SECRET},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                logger.warning("Раздел сводки не принят: HTTP %s", resp.status)
                return
    logger.info("Раздел сводки отправлен: %s строк", len(slice_["lines"]))


async def daily_summary_scheduler() -> None:
    """Фоновая задача: раз в сутки шлём свой раздел сводки."""
    if not settings.EXCHANGE_CHECK_URL:
        logger.info("daily summary disabled (EXCHANGE_CHECK_URL is empty)")
        return
    tz = ZoneInfo(settings.TIME_ZONE)
    while True:
        now = datetime.now(tz)
        run_at = now.replace(hour=SEND_AT[0], minute=SEND_AT[1], second=0, microsecond=0)
        if run_at <= now:
            run_at += timedelta(days=1)
        await asyncio.sleep((run_at - now).total_seconds())
        try:
            await push_slice()
        except Exception:
            # отчёт не должен ронять бота — переживём до завтра
            logger.exception("daily summary push failed")
