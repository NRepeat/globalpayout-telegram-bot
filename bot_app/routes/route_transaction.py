from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from bot_app.data_queries import Connection, get_db_connection
from bot_app.data_queries.api_allowed_keys import get_access_key
from bot_app.data_queries.chat import get_transaction_target_chat
from bot_app.data_queries.transaction import (
    get_transaction_by_uuid,
    new_transaction,
    update_posted_information,
    update_transaction_usdt_value,
)
from bot_app.exchange_methods import BoxExchanger
from bot_app.markup.base import claim_transaction_markup
from bot_app.misc import aiogram_bot_instance, box_exchanger_client
from bot_app.schemas.transaction import NewTransaction, TransactionResponse

transaction_router = APIRouter(
    prefix="/transaction",
    tags=["transaction"],
)


@transaction_router.post(
    "/",
    operation_id="submit_transaction",
    response_model=TransactionResponse,
    responses={
        504: {
            "description": "Issues with telegram API. Probably, the bot can't publish message in the chat."
        }
    },
)
async def submit_transaction(
    transaction_data: NewTransaction,
    db_connection: Connection = Depends(get_db_connection),
    authorization: str | None = Header(default=None),
) -> TransactionResponse:
    boxApi = BoxExchanger()
    try:
        response = await boxApi.getCurrentOrderDetails(
            transaction_data.external_order_id
        )

        if response and isinstance(response, dict) and "order" in response:
            order_details = response["order"]

            transaction_data.usdt_amount = order_details.get("inAmount", 0.0)
            transaction_data.rates = order_details.get("rate", 0.0)

            print(
                f"Данные успешно обновлены: Сумма {transaction_data.usdt_amount}, Курс {transaction_data.rates}"
            )
        else:
            print(
                f"Предупреждение: Заказ {transaction_data.external_order_id} не найден или структура ответа изменилась."
            )

    except Exception as e:
        # Любая ошибка (сеть, тип данных и т.д.) будет поймана здесь
        print(f"Произошла ошибка при обработке заказа: {e}")
        # Бот продолжает работу дальше

    created_transaction = await new_transaction(db_connection, transaction_data)
    # if authorization is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Authorization header is required",
    #     )

    # key_data = await get_access_key(db_connection, authorization.split(" ")[1])
    # if not key_data:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Access key is not valid",
    #     )
    # I am not sure I can get that from module itself so we are storing currencies id's into database to not fetch all of them each time we need them
    # currency_id = await get_user_rate_by_currency_xml_code(db_connection, created_transaction.currency_xml_code)
    # order_extra_info = await box_exchanger_client.get_order_info(
    #     created_transaction.external_order_id
    # )
    # order_extra_info["order"]["usdRate"]
    # if order_extra_info:
    #     order_data = order_extra_info.get("order")
    #     if order_data:
    #         usd_rate = order_data.get("usdRate")
    #         if usd_rate:
    #             usdt_amount = (
    #                 Decimal(created_transaction.amount) / Decimal(usd_rate)
    #             ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    #             await update_transaction_usdt_value(
    #                 db_connection, created_transaction.uuid, usdt_amount
    #             )

    target_chat = await get_transaction_target_chat(db_connection)

    print(f"Target chat:{target_chat}")
    if target_chat is None:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Target chat not found",
        )

    telegram_formatted_text = (
        await created_transaction.get_telegram_formatted_application(db_connection)
    )
    print(f"telegram_formatted_text chat:{telegram_formatted_text}")
    try:
        message = await aiogram_bot_instance.send_message(
            target_chat.chat_tg_id,
            text=telegram_formatted_text,
            reply_markup=claim_transaction_markup(str(created_transaction.uuid)),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Issues with telegram API. Probably, the bot can't publish message in the chat. {e}",
        ) from e
    await update_posted_information(
        db_connection, target_chat, message.message_id, created_transaction
    )
    return created_transaction


@transaction_router.get(
    "/{transaction_id}",
    operation_id="get_transaction",
    response_model=TransactionResponse,
)
async def get_transaction(
    transaction_id: UUID,
    db_connection: Connection = Depends(get_db_connection),
    authorization: str | None = Header(default=None),
) -> dict:
    # if authorization is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Authorization header is required",
    #     )
    # key_data = await get_access_key(db_connection, authorization.split(" ")[1])
    # if not key_data:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Access key is not valid",
    #     )
    transaction_data: TransactionResponse | None = await get_transaction_by_uuid(
        db_connection, transaction_id
    )
    if not transaction_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return transaction_data
