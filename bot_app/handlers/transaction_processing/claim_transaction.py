import logging
from contextlib import suppress

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile

from bot_app.data_queries import Connection
from bot_app.data_queries.chat import get_transaction_target_chat
from bot_app.data_queries.transaction import (
    get_transaction_by_uuid,
    set_transaction_manager,
    update_posted_information,
)
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.markup.base import TransactionOperations, finish_transaction_processing
from bot_app.misc import aiogram_bot_instance, aiogram_router
from bot_app.schemas.transaction import TransactionResponse

logger = logging.getLogger(__name__)


@aiogram_router.callback_query(TransactionOperations.filter(F.action == "claim"))
async def add_new_channel(
    call: CallbackQuery, db_connection: Connection, callback_data: TransactionOperations
):
    if not await get_user_by_id(db_connection, call.from_user.id):
        await save_user(db_connection, call.from_user)

    try:
        await set_transaction_manager(
            db_connection, callback_data.transaction_uuid, call.from_user.id
        )
    except ValueError as e:
        await call.answer(str(e), show_alert=True)
        return

    transaction: TransactionResponse = await get_transaction_by_uuid(
        db_connection, callback_data.transaction_uuid
    )

    if transaction is None:
        await call.answer("Транзакція не знайдена", show_alert=True)
        return

    transaction_text = await transaction.get_telegram_formatted_application(
        db_connection
    )

    # Особиста група оператора: заявка переїжджає туди, у спільному чаті
    # залишається помітка «взята». Якщо переїзд не вдався — працюємо на місці,
    # заявку губити не можна.
    if await move_to_work_group(call, db_connection, callback_data, transaction_text):
        await call.answer()
        return

    try:
        # карточка — фото, текст живёт в подписи
        await call.message.edit_caption(
            caption=transaction_text,
            reply_markup=finish_transaction_processing(callback_data.transaction_uuid),
        )
    except TelegramBadRequest as e:
        if (
            "message to edit not found" in e.message
            or "message can't be edited" in e.message
            or "there is no caption" in e.message
        ):
            tg_chat = await get_transaction_target_chat(db_connection)

            message = await aiogram_bot_instance.send_photo(
                tg_chat.chat_tg_id,
                photo=FSInputFile("bot_app/assets/placeholder.png"),
                caption=transaction_text,
                reply_markup=finish_transaction_processing(
                    callback_data.transaction_uuid
                ),
            )
            await update_posted_information(
                db_connection,
                tg_chat,
                message.message_id,
                transaction,
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


async def move_to_work_group(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: TransactionOperations,
    transaction_text: str,
) -> bool:
    """Перенести взяту заявку в особисту групу оператора.

    True — заявка переїхала, далі робота йде там. False — групи немає або
    надіслати не вдалося: тоді працюємо у спільному чаті, як раніше. Втратити
    заявку через ненастроєну чи недоступну групу не можна.
    """
    user = await get_user_by_id(db_connection, call.from_user.id)
    work_group = user.work_group_chat_id if user else None
    if not work_group or work_group == call.message.chat.id:
        return False

    # Фото беремо з картки у спільному чаті — у операторській групі має бути
    # та сама квитанція/заглушка, інакше editMessageMedia на фіналі впаде.
    photo = call.message.photo[-1].file_id if call.message.photo else None
    try:
        await aiogram_bot_instance.send_photo(
            work_group,
            photo=photo or FSInputFile("bot_app/assets/placeholder.png"),
            caption=transaction_text,
            reply_markup=finish_transaction_processing(callback_data.transaction_uuid),
        )
    except TelegramBadRequest as e:
        # найчастіше — бота не додали в групу; кажемо оператору прямо, інакше
        # виглядає як «кнопка не працює»
        logger.warning("work group %s unavailable: %s", work_group, e.message)
        await call.answer(
            "Не вдалося надіслати заявку у вашу робочу групу — працюємо тут. "
            "Перевірте, що бот доданий у групу.",
            show_alert=True,
        )
        return False

    # У спільному чаті лишається слід: заявка взята, кнопок більше немає
    with suppress(TelegramBadRequest):
        await call.message.edit_caption(
            caption=f"{transaction_text}\n\n🔒 Взята — робота у групі оператора",
            reply_markup=None,
        )
    return True
