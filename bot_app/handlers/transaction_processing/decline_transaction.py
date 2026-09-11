"""Відмова від заявки: оператор віддає її назад у спільний чат.

Без цього заявка, яку взяли помилково або не змогли виплатити, висить за
оператором до кінця дня — інший її просто не бачить. Так само це працює у
greatbot і klim-bot.

Порядок дій навмисний: спочатку пишемо в базу (точка неповернення), потім
best-effort правимо повідомлення. Якщо телеграм не відповість, заявка все одно
вільна — а не «відпущена наполовину».
"""

import logging
from contextlib import suppress

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile

from bot_app.data_queries import Connection
from bot_app.data_queries.chat import get_transaction_target_chat
from bot_app.data_queries.transaction import (
    get_posted_message,
    get_transaction_by_uuid,
    release_transaction,
    update_posted_information,
)
from bot_app.markup.base import TransactionOperations, claim_transaction_markup
from bot_app.misc import aiogram_bot_instance, aiogram_router

logger = logging.getLogger(__name__)


@aiogram_router.callback_query(TransactionOperations.filter(F.action == "decline"))
async def decline_transaction(
    call: CallbackQuery, db_connection: Connection, callback_data: TransactionOperations
):
    uuid = callback_data.transaction_uuid
    released = await release_transaction(db_connection, uuid, call.from_user.id)
    if not released:
        # чужа заявка або вже не в роботі — мовчати не можна, кнопка виглядає
        # робочою
        await call.answer(
            "Відмовитись не вийшло: заявка не у вас у роботі або вже закрита.",
            show_alert=True,
        )
        return

    transaction = await get_transaction_by_uuid(db_connection, uuid)
    if transaction is None:
        await call.answer("Транзакція не знайдена", show_alert=True)
        return
    text = await transaction.get_telegram_formatted_application(db_connection)

    posted = await get_posted_message(db_connection, uuid)
    common_chat = posted[0] if posted else None

    # Копію в робочій групі прибираємо — заявка більше не наша
    if call.message.chat.id != common_chat:
        with suppress(TelegramBadRequest):
            await call.message.delete()

    # Повертаємо картку у спільний чат з кнопкою «Взяти»
    restored = False
    if posted:
        chat_id, message_id = posted
        with suppress(TelegramBadRequest):
            await aiogram_bot_instance.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                reply_markup=claim_transaction_markup(uuid),
            )
            restored = True

    if not restored:
        # повідомлення у спільному чаті не знайшлося (видалили, застаріло) —
        # публікуємо заново, інакше заявка стане невидимою для всіх
        tg_chat = await get_transaction_target_chat(db_connection)
        if tg_chat is None:
            logger.error("decline: цільовий чат не заданий, заявка %s невидима", uuid)
            await call.answer(
                "Заявка звільнена, але цільовий чат не заданий — попередьте адміністратора.",
                show_alert=True,
            )
            return
        message = await aiogram_bot_instance.send_photo(
            tg_chat.chat_tg_id,
            photo=FSInputFile("bot_app/assets/placeholder.png"),
            caption=text,
            reply_markup=claim_transaction_markup(uuid),
        )
        await update_posted_information(
            db_connection, tg_chat, message.message_id, transaction
        )

    await call.answer("Заявка повернена у спільний чат")
