from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from bot_app.data_queries import Connection
from bot_app.data_queries.chat import get_transaction_target_chat
from bot_app.data_queries.transaction import (
    get_transaction_by_uuid,
    update_posted_information,
    update_transaction_status,
)
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.markup.base import TransactionOperations
from bot_app.misc import aiogram_bot_instance, aiogram_router
from bot_app.schemas.transaction import TransactionResponse


@aiogram_router.callback_query(TransactionOperations.filter(F.action == "failed"))
@aiogram_router.callback_query(TransactionOperations.filter(F.action == "completed"))
async def mark_transaction_as_done(
    call: CallbackQuery, db_connection: Connection, callback_data: TransactionOperations
):
    if not await get_user_by_id(db_connection, call.from_user.id):
        await save_user(db_connection, call.from_user)

    transaction: TransactionResponse = await get_transaction_by_uuid(
        db_connection, callback_data.transaction_uuid
    )

    if transaction is None:
        await call.answer("Транзакція не знайдена", show_alert=True)
        return

    if transaction.manager_id != call.from_user.id:
        await call.answer("Ви не менеджер цієї транзакції", show_alert=True)
        return

    await update_transaction_status(
        db_connection, callback_data.transaction_uuid, callback_data.action
    )

    updated_transaction = await get_transaction_by_uuid(
        db_connection, callback_data.transaction_uuid
    )
    if updated_transaction is None:
        await call.answer("Транзакція не знайдена", show_alert=True)
        return

    transaction_text = await updated_transaction.get_telegram_formatted_application(
        db_connection
    )
    try:
        await call.message.edit_text(
            transaction_text,
            reply_markup=None,
        )
    except TelegramBadRequest as e:
        if (
            "message to edit not found" in e.message
            or "message can't be edited" in e.message
        ):
            tg_chat = await get_transaction_target_chat(db_connection)

            message = await aiogram_bot_instance.send_message(
                tg_chat.chat_tg_id,
                text=transaction_text,
            )
            await update_posted_information(
                db_connection,
                tg_chat,
                message.message_id,
                updated_transaction,
            )
        elif "message is not modified" in e.message:
            await call.answer(
                "Щось не так з оновленням статусу трансакції, зв’яжіться з адміністратором",
                show_alert=True,
            )
        else:
            raise
    finally:
        await call.answer()
