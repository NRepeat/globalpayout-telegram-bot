import asyncio
import logging
from contextlib import suppress

import aiohttp
from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InputMediaDocument,
    InputMediaPhoto,
    Message,
)
from pymysql.err import IntegrityError, MySQLError

from bot_app.config import settings
from bot_app.data_queries import Connection
from bot_app.data_queries.chat import get_transaction_target_chat
from bot_app.data_queries.transaction import (
    close_transaction,
    get_close_fee,
    get_posted_message,
    get_transaction_by_uuid,
    update_posted_information,
    update_transaction_status,
)
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.markup.base import (
    CloseAccountSelection,
    TransactionOperations,
    cancel_state_entering_markup,
    close_account_type_markup,
    close_exchanges_markup,
)
from bot_app.misc import aiogram_bot_instance, aiogram_router
from bot_app.schemas.transaction import TransactionResponse
from bot_app.states import CloseTransaction
from bot_app.utils import parse_close_order_input, parse_close_rate

log = logging.getLogger(__name__)

# Тексты шагов — единый флоу закрытия во всех ботах (эталон — greatbot),
# поэтому по-русски, как и готовые ответы сервиса сверки.
ASK_RECEIPT = "📎 Отправьте квитанцию выплаты (фото)"
ASK_ACCOUNT = "🏦 Где закрыта заявка?"
ASK_PARTNER = "🤝 Имя партнёра"
ASK_RATE = "📊 Курс закрытия"
# Площадки с автосверкой: там спрашиваем ID ордера и берём курс с комиссией из
# него. Остальным биржам P2P-API нам не дают — они идут ручным курсом бухгалтера.
AUTO_CHECKED = ("binance", "bybit")


def display_account(account: str) -> str:
    """`binance` → `Binance`: то же имя, что на кнопке."""
    return account.capitalize()


def ask_order(account: str) -> str:
    return f"🧾 ID P2P-ордера {display_account(account)}"


def checking(account: str) -> str:
    return f"⏳ Сверяю с {display_account(account)}…"
UNAVAILABLE = "⚠️ Сервис сверки недоступен, попробуйте ещё раз или «курс N»."
# Ручной курс — точка доверия: цифру никто не сверяет, поэтому право на неё
# только у бухгалтеров (BOOKKEEPER_TG_IDS). Закрытие по ID ордера — всем.
NOT_BOOKKEEPER = (
    "⛔ Ручной курс может вводить только бухгалтер. "
    "Закройте по ID ордера или позовите бухгалтера."
)


async def _refresh_card(
    db_connection: Connection,
    chat_id: int,
    message_id: int,
    transaction: TransactionResponse,
    extra: str = "",
):
    """Перерисовать карточку заявки и снять кнопки. Карточка — фото
    (плейсхолдер или уже квитанция), текст живёт в подписи. Если карточку
    удалили — перепостить в целевой чат (тот же ход, что был у claim)."""
    text = await transaction.get_telegram_formatted_application(db_connection)
    if extra:
        text += f"\n{extra}"
    try:
        await aiogram_bot_instance.edit_message_caption(
            chat_id=chat_id, message_id=message_id, caption=text, reply_markup=None
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
                caption=text,
            )
            await update_posted_information(
                db_connection, tg_chat, message.message_id, transaction
            )
        elif "message is not modified" not in e.message:
            raise


async def _refresh_common_card(
    db_connection: Connection,
    worked_chat_id: int,
    transaction: TransactionResponse,
):
    """Обновить карточку-заглушку в общем чате.

    Когда заявка уезжает в рабочую группу оператора, в общем чате остаётся
    карточка с пометкой «взята». Её правят один раз — при взятии, поэтому
    после закрытия она висела со статусом `in_progress`, и по общему чату
    было не понять, что заявка уже закрыта.

    Строку закрытия (площадка, курс, комиссия, ордер) сюда не несём: она
    касается только того, кто закрывал, и живёт в его чате.
    """
    posted = await get_posted_message(db_connection, str(transaction.uuid))
    if not posted:
        return
    chat_id, message_id = posted
    if chat_id == worked_chat_id:
        return  # работали прямо в общем чате — карточка уже обновлена
    text = await transaction.get_telegram_formatted_application(db_connection)
    with suppress(TelegramBadRequest):
        await aiogram_bot_instance.edit_message_caption(
            chat_id=chat_id, message_id=message_id, caption=text, reply_markup=None
        )


async def _prompt(state: FSMContext, chat_id: int, text: str, markup) -> None:
    """Одно живое сообщение-подсказка на весь визард: старое удаляем,
    новое запоминаем — переписка в чате не растёт."""
    data = await state.get_data()
    if old := data.get("prompt_message_id"):
        with suppress(TelegramBadRequest):
            await aiogram_bot_instance.delete_message(chat_id, old)
    message = await aiogram_bot_instance.send_message(chat_id, text, reply_markup=markup)
    await state.update_data(prompt_message_id=message.message_id)


async def _trash(state: FSMContext, message_id: int) -> None:
    """Запомнить сообщение оператора (фото, курс, ID): после финала весь
    ввод визарда выметается из чата — как в greatbot, остаётся только
    карточка с квитанцией."""
    data = await state.get_data()
    ids = data.get("trash_ids") or []
    ids.append(message_id)
    await state.update_data(trash_ids=ids)


@aiogram_router.callback_query(TransactionOperations.filter(F.action == "failed"))
async def mark_transaction_as_failed(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: TransactionOperations,
    state: FSMContext,
):
    if not await get_user_by_id(db_connection, call.from_user.id):
        await save_user(db_connection, call.from_user)

    transaction = await get_transaction_by_uuid(
        db_connection, callback_data.transaction_uuid
    )
    if transaction is None:
        await call.answer("Транзакція не знайдена", show_alert=True)
        return
    if transaction.manager_id != call.from_user.id:
        await call.answer("Ви не менеджер цієї транзакції", show_alert=True)
        return

    # «Невдалий» посреди визарда закрытия этой же заявки: снести визард,
    # иначе дожатый последний шаг вернёт failed-заявку в completed
    data = await state.get_data()
    if data.get("transaction_uuid") == callback_data.transaction_uuid:
        if prompt_id := data.get("prompt_message_id"):
            with suppress(TelegramBadRequest):
                await aiogram_bot_instance.delete_message(
                    call.message.chat.id, prompt_id
                )
        await state.clear()

    await update_transaction_status(
        db_connection, callback_data.transaction_uuid, "failed"
    )
    updated = await get_transaction_by_uuid(
        db_connection, callback_data.transaction_uuid
    )
    await _refresh_card(
        db_connection, call.message.chat.id, call.message.message_id, updated
    )
    await _refresh_common_card(db_connection, call.message.chat.id, updated)
    await call.answer()


@aiogram_router.callback_query(TransactionOperations.filter(F.action == "completed"))
async def start_close_flow(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: TransactionOperations,
    state: FSMContext,
):
    """«Сплачений» больше не закрывает заявку сразу: сначала обязательные шаги
    закрытия (квитанция → площадка → курс). Карточку не трогаем до финала —
    отмена возвращает всё как было."""
    if not await get_user_by_id(db_connection, call.from_user.id):
        await save_user(db_connection, call.from_user)

    transaction = await get_transaction_by_uuid(
        db_connection, callback_data.transaction_uuid
    )
    if transaction is None:
        await call.answer("Транзакція не знайдена", show_alert=True)
        return
    if transaction.manager_id != call.from_user.id:
        await call.answer("Ви не менеджер цієї транзакції", show_alert=True)
        return

    await state.clear()
    await state.set_state(CloseTransaction.receipt)
    await state.update_data(
        transaction_uuid=str(transaction.uuid),
        card_chat_id=call.message.chat.id,
        card_message_id=call.message.message_id,
    )
    await _prompt(
        state, call.message.chat.id, ASK_RECEIPT, cancel_state_entering_markup()
    )
    await call.answer()


@aiogram_router.message(CloseTransaction.receipt, F.photo | F.document)
async def receipt_received(message: Message, state: FSMContext):
    # Квитанцию запоминаем file_id'ом: в финале она уедет ответом на карточку,
    # а оригинал оператора удалится вместе с остальной перепиской визарда
    if message.photo:
        receipt = ("photo", message.photo[-1].file_id)
    else:
        receipt = ("document", message.document.file_id)
    await state.update_data(receipt=receipt)
    await _trash(state, message.message_id)
    await state.set_state(CloseTransaction.account)
    await _prompt(state, message.chat.id, ASK_ACCOUNT, close_account_type_markup())


@aiogram_router.message(CloseTransaction.receipt)
async def receipt_missing(message: Message, state: FSMContext):
    await _prompt(state, message.chat.id, ASK_RECEIPT, cancel_state_entering_markup())


@aiogram_router.callback_query(CloseTransaction.account, CloseAccountSelection.filter())
async def choose_close_account(
    call: CallbackQuery,
    callback_data: CloseAccountSelection,
    state: FSMContext,
):
    action = callback_data.action
    # [Биржи] ⇄ [◀ Назад] — листание экранов выбора, состояние не меняется
    if action in ("exchanges", "back"):
        markup = (
            close_exchanges_markup()
            if action == "exchanges"
            else close_account_type_markup()
        )
        with suppress(TelegramBadRequest):  # повторный тык — «not modified»
            await call.message.edit_reply_markup(reply_markup=markup)
        await call.answer()
        return

    if action == "partner":
        await state.set_state(CloseTransaction.partner_name)
        await _prompt(
            state, call.message.chat.id, ASK_PARTNER, cancel_state_entering_markup()
        )
    elif action in AUTO_CHECKED:
        # где есть автосверка — курс не спрашиваем, берём из ордера по ID
        await state.update_data(close_account=action)
        await state.set_state(CloseTransaction.order_id)
        await _prompt(
            state,
            call.message.chat.id,
            ask_order(action),
            cancel_state_entering_markup(),
        )
    else:  # okx | htx | mexc
        await state.update_data(close_account=action)
        await state.set_state(CloseTransaction.rate)
        await _prompt(
            state, call.message.chat.id, ASK_RATE, cancel_state_entering_markup()
        )
    await call.answer()


@aiogram_router.message(CloseTransaction.partner_name, F.text)
async def partner_name_received(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        return
    await _trash(state, message.message_id)
    await state.update_data(close_account=f"partner:{name}")
    await state.set_state(CloseTransaction.rate)
    await _prompt(state, message.chat.id, ASK_RATE, cancel_state_entering_markup())


@aiogram_router.message(CloseTransaction.rate, F.text)
async def close_rate_received(
    message: Message, state: FSMContext, db_connection: Connection
):
    await _trash(state, message.message_id)
    # Гард бухгалтера: единственная точка, куда сходятся все ручные курсы
    # (OKX/HTX/Bybit/MEXC и партнёры). Состояние не трогаем — шаг тот же.
    if message.from_user.id not in settings.bookkeeper_ids:
        await _prompt(
            state,
            message.chat.id,
            f"{NOT_BOOKKEEPER}\n\n{ASK_RATE}",
            cancel_state_entering_markup(),
        )
        return
    rate = parse_close_rate(message.text)
    if rate is None:
        await _prompt(state, message.chat.id, ASK_RATE, cancel_state_entering_markup())
        return
    data = await state.get_data()
    account = data["close_account"]
    # комиссия — из справочника по площадке, оператора не спрашиваем
    fee = await get_close_fee(db_connection, account)
    await _finish_close(message.chat.id, db_connection, state, account, rate, fee, None)


@aiogram_router.message(CloseTransaction.order_id, F.text)
async def close_order_received(
    message: Message, state: FSMContext, db_connection: Connection
):
    await _trash(state, message.message_id)
    data = await state.get_data()
    account = data.get("close_account", "binance")
    parsed = parse_close_order_input(message.text)
    if parsed is None:
        await _prompt(
            state,
            message.chat.id,
            f"ID ордера — число из ордера {display_account(account)}."
            f"\n\n{ask_order(account)}",
            cancel_state_entering_markup(),
        )
        return

    kind, value = parsed
    if kind == "rate":
        # обход «курс N» — тот же ручной курс, гард бухгалтера и здесь;
        # сверка по ID ордера ниже остаётся доступной всем
        if message.from_user.id not in settings.bookkeeper_ids:
            await _prompt(
                state,
                message.chat.id,
                f"{NOT_BOOKKEEPER}\n\n{ask_order(account)}",
                cancel_state_entering_markup(),
            )
            return
        # ручной обход: сервис недоступен или ордер не с нашего аккаунта
        fee = await get_close_fee(db_connection, account)
        await _finish_close(
            message.chat.id, db_connection, state, account, value, fee, None
        )
        return

    transaction = await get_transaction_by_uuid(db_connection, data["transaction_uuid"])
    if transaction is None:
        await state.clear()
        await message.answer("Транзакція не знайдена")
        return

    # сверка занимает секунды — показываем, что не зависли
    await _prompt(state, message.chat.id, checking(account), None)
    # сверяем ключами того, кто закрывает: ордер лежит в истории его биржевого
    # аккаунта, чужим ключом он не найдётся
    verdict = await _verify_order(transaction, value, account, message.from_user.id)
    if isinstance(verdict, str):  # готовый текст отказа
        await _prompt(
            state,
            message.chat.id,
            f"{verdict}\n\n{ask_order(account)}",
            cancel_state_entering_markup(),
        )
        return
    rate, fee = verdict
    await _finish_close(
        message.chat.id, db_connection, state, account, rate, fee, value
    )


async def _verify_order(
    transaction: TransactionResponse,
    order_id: str,
    exchange: str,
    operator_id: int,
) -> tuple[str, str] | str:
    """Сверить P2P-ордер с заявкой через exchange-check: он ходит на биржу,
    проверяет статус/актив/сумму и атомарно резервирует ордер за заявкой во
    всех ботах. Ok — (rate, fee) строками из ордера; str — текст отказа."""
    if not transaction.usdt_amount:
        return "⚠️ У заявки нет суммы USDT — закройте вручную: «курс 41.25»."
    body = {
        "workspace": "globalpayout",
        "request_id": str(transaction.uuid),
        "exchange": exchange,
        "order_id": order_id,
        "expected_amount": str(transaction.usdt_amount),
        "expected_asset": "USDT",
        # Основная сверка — по фиату: крипта ордера считается по курсу
        # оператора, крипта заявки — по курсу клиента, и расходятся они всегда
        # (это наш заработок). Совпадать обязана сумма в гривне.
        "expected_fiat": str(transaction.amount),
        "fiat": transaction.currency,
        # ключи берутся по закрывающему: у каждого сотрудника свой аккаунт
        "operator_id": operator_id,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{settings.EXCHANGE_CHECK_URL}/verify",
                json=body,
                headers={"X-Secret": settings.EXCHANGE_CHECK_SECRET},
                # сервис сам листает историю биржи — даём ему больше времени
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    # 401 — неверный EXCHANGE_CHECK_SECRET; оператору это не починить
                    return UNAVAILABLE
                data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return UNAVAILABLE
    if data.get("ok") is not True:
        # сервис отдаёт готовый русский текст отказа — показываем как есть
        return data.get("message") or "❌ Сверка не прошла."
    rate = data.get("rate") or ""
    if not rate:
        return UNAVAILABLE
    fee = data.get("fee") or "0"
    return rate, fee


async def _finish_close(
    chat_id: int,
    db_connection: Connection,
    state: FSMContext,
    account: str,
    rate,
    fee,
    order_id: str | None,
):
    """Финал: все данные закрытия собраны — один UPDATE (close_* + статус),
    потом перерисовать карточку. До этой точки в БД не писалось ничего."""
    data = await state.get_data()
    transaction_uuid = data["transaction_uuid"]
    try:
        closed = await close_transaction(
            db_connection, transaction_uuid, account, rate, fee, order_id
        )
    except IntegrityError:
        # гонка на уникальном close_order_id: сервис резервирует атомарно,
        # но локальный индекс — последняя страховка
        await _prompt(
            state,
            chat_id,
            f"❌ Ордер уже использован другой заявкой.\n\n{ask_order(account)}",
            cancel_state_entering_markup(),
        )
        return
    except MySQLError:
        # DataError/обрыв БД: молча глотать нельзя — webhook ответит 200 и
        # оператор не узнает, что закрытие не записано. Состояние оставляем,
        # чтобы можно было просто повторить последний шаг.
        await _prompt(
            state,
            chat_id,
            "⚠️ Не удалось сохранить закрытие — отправьте данные ещё раз.",
            cancel_state_entering_markup(),
        )
        return

    if not closed:
        # заявку успели пометить «Невдалий» (или закрыть) — не воскрешаем
        if prompt_id := data.get("prompt_message_id"):
            with suppress(TelegramBadRequest):
                await aiogram_bot_instance.delete_message(chat_id, prompt_id)
        await state.clear()
        await aiogram_bot_instance.send_message(
            chat_id, "⚠️ Заявка уже не в работе — закрытие не сохранено."
        )
        return

    # вымести переписку визарда: подсказку и весь ввод оператора (фото, курс,
    # ID) — в чате остаётся только карточка с квитанцией, как в greatbot
    if prompt_id := data.get("prompt_message_id"):
        with suppress(TelegramBadRequest):
            await aiogram_bot_instance.delete_message(chat_id, prompt_id)
    for msg_id in data.get("trash_ids") or []:
        with suppress(TelegramBadRequest):
            await aiogram_bot_instance.delete_message(chat_id, msg_id)
    await state.clear()

    transaction = await get_transaction_by_uuid(db_connection, transaction_uuid)
    extra = f"🏦 Закрыто: {account} | курс {rate} | комиссия {fee}"
    if order_id:
        extra += f" | ордер {order_id}"
    text = await transaction.get_telegram_formatted_application(db_connection)
    text += f"\n{extra}"

    # Квитанция встаёт в карточку вместо плейсхолдера (editMessageMedia),
    # подпись — карточка + строка закрытия: как в greatbot, один пруф-месседж.
    kind, file_id = data.get("receipt") or (None, None)
    if file_id:
        media_cls = InputMediaPhoto if kind == "photo" else InputMediaDocument
        try:
            await aiogram_bot_instance.edit_message_media(
                chat_id=data["card_chat_id"],
                message_id=data["card_message_id"],
                media=media_cls(media=file_id, caption=text, parse_mode="HTML"),
                reply_markup=None,
            )
            await _refresh_common_card(
                db_connection, data["card_chat_id"], transaction
            )
            return
        except TelegramBadRequest as e:
            log.warning("квитанция не встала в карточку: %s", e.message)
            # карточки нет/не медиа — падаем в обычный refresh ниже
    await _refresh_card(
        db_connection, data["card_chat_id"], data["card_message_id"], transaction, extra
    )
    await _refresh_common_card(db_connection, data["card_chat_id"], transaction)
