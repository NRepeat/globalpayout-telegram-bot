import io
from datetime import datetime, timedelta

import pandas as pd
import pytz
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiomysql import Connection, Cursor

from bot_app.config import settings
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.markup.base import ReportPeriodSelection, get_report_period_markup
from bot_app.misc import aiogram_router


@aiogram_router.message(Command("report"))
async def show_report_periods(message: Message, db_connection: Connection):
    user = await get_user_by_id(db_connection, message.from_user.id)
    if not user:
        await save_user(db_connection, message.from_user)
        await message.answer("Виконання цієї дії дозволено лише старшим операторам")
        return

    if not user.senior_operator:
        await message.answer("Виконання цієї дії дозволено лише старшим операторам")
        return

    await message.answer(
        "Оберіть період для звіту:", reply_markup=get_report_period_markup()
    )


@aiogram_router.callback_query(ReportPeriodSelection.filter())
async def generate_report(
    callback: CallbackQuery,
    callback_data: ReportPeriodSelection,
    db_connection: Connection,
):
    user = await get_user_by_id(db_connection, callback.from_user.id)
    if not user:
        await save_user(db_connection, callback.from_user)
        await callback.answer("Виконання цієї дії дозволено лише старшим операторам")
        return

    if not user.senior_operator:
        await callback.answer("Виконання цієї дії дозволено лише старшим операторам")
        return
    await callback.answer()

    # Calculate date range with timezone
    tz = pytz.timezone(settings.TIME_ZONE)
    end_date = datetime.now(tz=tz)

    if callback_data.period == "today":
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif callback_data.period == "7days":
        start_date = end_date - timedelta(days=7)
    elif callback_data.period == "30days":
        start_date = end_date - timedelta(days=30)
    else:  # 90days
        start_date = end_date - timedelta(days=90)

    # Get data from database

    query = """
    SELECT 
        et.uuid as "ID транзакції",
        et.external_order_id as "Зовнішній ID",
        tg_user.user_id as "ID менеджера",
        tg_user.user_name as "Нікнейм менеджера",
        ds.status_code as "Статус",
        et.currency as "Валюта",
        et.amount as "Сума",
        et.card_number as "Номер картки",
        et.full_name as "ПІБ",
        et.created_at as "Дата створення",
        et.usdt_amount as "Сума в USDT"
    FROM exchange_transaction et
    LEFT JOIN data_tg_user tg_user ON et.manager_id = tg_user.user_id
    JOIN data_status ds ON et.status_id = ds.record_id
    WHERE et.created_at BETWEEN %s AND %s
    ORDER BY et.created_at DESC
    """
    async with db_connection.cursor() as cur:
        cur: Cursor
        await cur.execute(query, (start_date, end_date))
        data = await cur.fetchall()

    if not data:
        await callback.message.answer("Немає даних за вказаний період")
        return

    # Create DataFrame
    df = pd.DataFrame(data)

    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Звіт", index=False)

        # Auto-adjust columns width
        worksheet = writer.sheets["Звіт"]
        for idx, col in enumerate(df.columns):
            series = df[col]
            max_len = max(series.astype(str).map(len).max(), len(str(col))) + 1
            worksheet.set_column(idx, idx, max_len)

    output.seek(0)

    file = BufferedInputFile(
        output.getvalue(), filename=f"report_{callback_data.period}.xlsx"
    )

    # Send file
    period_names = {
        "today": "сьогодні",
        "7days": "останні 7 днів",
        "30days": "останні 30 днів",
        "90days": "останні 90 днів",
    }

    await callback.message.answer_document(
        document=file, caption=f"Звіт за період: {period_names[callback_data.period]}"
    )
    await callback.message.delete()
