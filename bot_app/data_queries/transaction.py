import datetime
import uuid
from decimal import Decimal
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
        recipient_name, payment_note, payout_email, revtag,
        wallet_address, bank_name, photo, bank_account,
        country, sort_code, account_number, phone, idram_account,
        ifsc, upi_id, paytm_wallet, pix_keys, cpf, cvu_cbu,
        separate_direction, telegram,
        usdt_amount, rates
    )
    VALUES (
        %s, %s, (select record_id from data_status where status_code = %s),
        %s, %s, %s, %s,
        %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s,
        %s, %s
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
        transaction.wallet_address,
        transaction.bank_name,
        transaction.photo,
        transaction.bank_account,
        transaction.country,
        transaction.sort_code,
        transaction.account_number,
        transaction.phone,
        transaction.idram_account,
        transaction.ifsc,
        transaction.upi_id,
        transaction.paytm_wallet,
        transaction.pix_keys,
        transaction.cpf,
        transaction.cvu_cbu,
        transaction.separate_direction,
        transaction.telegram,
        transaction.usdt_amount,
        transaction.rates,
    )

    async with conn.cursor() as cur:
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
        recipient_name, payment_note, payout_email, revtag,
        wallet_address, bank_name, photo, bank_account,
        country, sort_code, account_number, phone, idram_account,
        ifsc, upi_id, paytm_wallet, pix_keys, cpf, cvu_cbu,
        separate_direction, telegram,
        usdt_amount, rates
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


async def get_close_fee(conn: Connection, account: str) -> Decimal:
    """Комиссия площадки из справочника close_fees. Отсутствие строки — 0,
    не блокирует закрытие (partner:<имя> обычно без строки)."""
    query = "SELECT fee FROM close_fees WHERE account = %s"
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (account,))
        row = await cur.fetchone()
    return row["fee"] if row else Decimal(0)


async def close_transaction(
    conn: Connection,
    transaction_uuid: str,
    account: str,
    rate,
    fee,
    order_id: str | None,
):
    """Финал закрытия: все поля close_* и статус completed одним UPDATE —
    отмена на любом шаге до этого не оставляет половины данных.
    rate/fee — Decimal или строка из сервиса сверки, в БД это DECIMAL.
    Дубль close_order_id (уникальный индекс) поднимет IntegrityError.
    Закрываем только из in_progress: если заявку успели пометить «Невдалий»,
    дожатый визард не должен воскресить её в completed. False — не закрылась."""
    query = """
    UPDATE exchange_transaction SET
        close_account = %s, close_rate = %s, close_fee = %s, close_order_id = %s,
        status_id = (SELECT record_id FROM data_status WHERE status_code = 'completed')
    WHERE uuid = %s
      AND status_id = (SELECT record_id FROM data_status WHERE status_code = 'in_progress')
    """
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (account, str(rate), str(fee), order_id, transaction_uuid))
        await conn.commit()
        return cur.rowcount > 0


async def release_transaction(
    conn: Connection, transaction_uuid: str, manager_id: int
) -> bool:
    """Відмова від заявки: знімаємо менеджера і повертаємо статус 'created',
    щоб її міг узяти інший оператор.

    Тільки з 'in_progress': вже сплачену або невдалу відмова воскрешати не
    повинна. False — заявка не в роботі або її веде інший оператор.
    """
    query = """
    UPDATE exchange_transaction SET
        manager_id = NULL,
        status_id = (SELECT record_id FROM data_status WHERE status_code = 'created')
    WHERE uuid = %s
      AND manager_id = %s
      AND status_id = (SELECT record_id FROM data_status WHERE status_code = 'in_progress')
    """
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (transaction_uuid, manager_id))
        await conn.commit()
        return cur.rowcount > 0


async def get_posted_message(conn: Connection, transaction_uuid: str):
    """Де лежить картка у спільному чаті: (chat_tg_id, message_id).

    `posted_in_chat_id` зберігає record_id з tg_chat, а не telegram-id, тому
    без джойна адресу не зібрати.
    """
    query = """
    SELECT c.chat_tg_id AS chat_tg_id, t.posted_message_id AS message_id
    FROM exchange_transaction t
    JOIN tg_chat c ON c.record_id = t.posted_in_chat_id
    WHERE t.uuid = %s
    """
    async with conn.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (transaction_uuid,))
        row = await cur.fetchone()
    if not row or not row["message_id"]:
        return None
    return int(row["chat_tg_id"]), int(row["message_id"])
