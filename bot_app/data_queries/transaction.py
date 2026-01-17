import datetime
import uuid
from uuid import UUID

import pytz
from aiomysql import Connection, Cursor

from bot_app.config import settings
from bot_app.schemas.tg_chat import SavedChat
from bot_app.schemas.transaction import NewTransaction, TransactionResponse

#

# ...


async def new_transaction(
    conn: Connection, transaction: NewTransaction
) -> TransactionResponse | None:
    now_time_with_timezone = datetime.datetime.now(tz=pytz.timezone(settings.TIME_ZONE))
    new_transaction_uuid = str(uuid.uuid4())

    query = """
  INSERT INTO exchange_transaction (
        uuid, external_order_id, status_id,
        currency, currency_xml_code, amount, created_at,
        card_number, full_name,
        method_type, service_name, iban, inn,
        recipient_name, payment_note, payout_email, revtag
  )
  VALUES (
        %s, %s, (select record_id from data_status where status_code = %s),
        %s, %s, %s, %s,
        %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s
    )
  """

    params = (
        new_transaction_uuid,
        transaction.external_order_id,
        "created",
        transaction.currency,
        transaction.currency_xml_code,
        transaction.amount,
        now_time_with_timezone,
        transaction.card_number,
        transaction.full_name,
        transaction.method_type,
        transaction.service_name,
        transaction.iban,
        transaction.inn,
        transaction.recipient_name,
        transaction.payment_note,
        transaction.payout_email,
        transaction.revtag,
    )

    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, params)
        await conn.commit()

    return await get_transaction_by_uuid(conn, new_transaction_uuid)


async def get_transaction_by_uuid(
    conn: Connection, transaction_uuid: str
) -> TransactionResponse | None:
    query = """
    SELECT
        uuid, external_order_id, data_status.status_code,
        currency, manager_id, currency_xml_code, amount, full_name,
        card_number, created_at,
        method_type, service_name, iban, inn,
        recipient_name, payment_note, payout_email, revtag
    FROM exchange_transaction
    JOIN data_status ON exchange_transaction.status_id = data_status.record_id
    WHERE uuid = %s
    """
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (transaction_uuid,))
        transaction = await cur.fetchone()
    if not transaction:
        return None
    return TransactionResponse(**transaction)


async def update_posted_information(
    conn: Connection,
    tg_chat: SavedChat,
    posted_message_id: int,
    transaction: TransactionResponse,
):
    query = """
    UPDATE exchange_transaction SET posted_in_chat_id = %s, posted_message_id = %s WHERE uuid = %s
    """
    params = (
        tg_chat.record_id,
        posted_message_id,
        transaction.uuid,
    )
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, params)
        await conn.commit()


async def update_transaction_status(
    conn: Connection, transaction_uuid: UUID, status_code: str
):
    query = """
    UPDATE exchange_transaction SET status_id = (SELECT record_id FROM data_status WHERE status_code = %s) WHERE uuid = %s
    """
    params = (
        status_code,
        transaction_uuid,
    )
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, params)
        await conn.commit()


async def update_transaction_usdt_value(
    conn: Connection, transaction_uuid: UUID, usdt_amount: float
):
    query = """
    UPDATE exchange_transaction SET usdt_amount = %s WHERE uuid = %s
    """
    params = (
        usdt_amount,
        str(transaction_uuid),
    )
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, params)
        await conn.commit()


async def set_transaction_manager(
    conn: Connection, transaction_uuid: UUID, manager_id: int
):
    select_existing_manager = """
    SELECT manager_id FROM exchange_transaction WHERE uuid = %s
"""

    query = """
    UPDATE exchange_transaction SET manager_id = %s WHERE uuid = %s
    """
    params = (
        manager_id,
        transaction_uuid,
    )
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(select_existing_manager, (str(transaction_uuid),))
        existing_manager: dict = await cur.fetchone()

        if existing_manager.get("manager_id"):
            raise ValueError("Транзакція вже має менеджера")

        await cur.execute(query, params)
        await conn.commit()

    await update_transaction_status(conn, transaction_uuid, "in_progress")
    return await get_transaction_by_uuid(conn, transaction_uuid)


async def get_stats_report(conn: Connection):
    query = """
    SELECT
    tg_user.user_id,
    COUNT(CASE WHEN created_at >= CURRENT_DATE() THEN 1 END) AS today_count,
    COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE() THEN COALESCE(usdt_amount, 0) END), 0) AS today_amount,
    COUNT(CASE WHEN created_at >= CURRENT_DATE() - INTERVAL 6 DAY THEN 1 END) AS last7d_count,
    COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE() - INTERVAL 6 DAY THEN COALESCE(usdt_amount, 0) END), 0) AS last7d_amount,
    COUNT(CASE WHEN created_at >= CURRENT_DATE() - INTERVAL 29 DAY THEN 1 END) AS last30d_count,
    COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE() - INTERVAL 29 DAY THEN COALESCE(usdt_amount, 0) END), 0) AS last30d_amount
    FROM exchange_transaction
    JOIN data_status ON exchange_transaction.status_id = data_status.record_id
    LEFT JOIN data_tg_user tg_user ON exchange_transaction.manager_id = tg_user.user_id
    WHERE data_status.status_code = 'completed'
    GROUP BY tg_user.user_id ORDER BY last30d_amount DESC;
    """
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query)
        stats = await cur.fetchall()
    return stats
