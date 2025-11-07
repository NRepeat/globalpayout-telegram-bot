from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot_app.data_queries import Connection
from bot_app.data_queries.transaction import get_stats_report
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.misc import aiogram_router


@aiogram_router.message(Command("stats"))
async def handle_stats(message: Message, db_connection: Connection, state: FSMContext):
    def amount_str(a: float) -> str:
        return f"{a:,.2f}".replace(",", " ").replace(".", ",")

    user = await get_user_by_id(db_connection, message.from_user.id)
    if not user:
        await save_user(db_connection, message.from_user)
        await message.answer("У вас немає прав")
        return

    if not user.bot_admin:
        await message.answer("У вас немає прав")
        return

    stats_report = await get_stats_report(db_connection)

    message_lines = [
        "📊 Статистика по менеджерам (тільки завершені заявки):",
    ]

    total_stats = {
        "today_count": 0,
        "today_amount": 0.0,
        "last7d_count": 0,
        "last7d_amount": 0.0,
        "last30d_count": 0,
        "last30d_amount": 0.0,
    }

    for row in stats_report:
        for key in total_stats:
            total_stats[key] += row.get(key, 0)

        manager_data = await get_user_by_id(db_connection, row["user_id"])

        message_lines.append(
            f"\n👤 {manager_data.linked_name_and_username()}\n"
            f"▫️ <b>Сьогодні:</b> {row['today_count']} заявок на {amount_str(row['today_amount'])} USDT\n"
            f"▫️ <b>7 днів:</b> {row['last7d_count']} заявок на {amount_str(row['last7d_amount'])} USDT\n"
            f"▫️ <b>30 днів:</b> {row['last30d_count']} заявок на {amount_str(row['last30d_amount'])} USDT"
        )

    message_lines.append(
        f"\n📈 <b>ЗАГАЛЬНА СТАТИСТИКА:</b>\n"
        f"▫️ <b>Сьогодні:</b> {total_stats['today_count']} заявок на {amount_str(total_stats['today_amount'])} USDT\n"
        f"▫️ <b>7 днів:</b> {total_stats['last7d_count']} заявок на {amount_str(total_stats['last7d_amount'])} USDT\n"
        f"▫️ <b>30 днів:</b> {total_stats['last30d_count']} заявок на {amount_str(total_stats['last30d_amount'])} USDT"
    )

    await message.answer("\n".join(message_lines)[:4096], disable_web_page_preview=True)
