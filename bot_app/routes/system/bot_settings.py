from typing import Annotated

from aiogram import types
from aiogram.exceptions import (
    TelegramUnauthorizedError,
)
from fastapi import APIRouter, Depends, Header, HTTPException, status

from bot_app.config import settings
from bot_app.data_queries import Connection, get_db_connection
from bot_app.misc import aiogram_bot_instance, multibot_dispatcher

root_router = APIRouter(
    prefix="",
    tags=["telegram_system"],
    include_in_schema=False,
)


@root_router.post("/bot-webhook/", operation_id="bot_webhook")
async def bot_webhook(
    update: dict,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
    db_connection: Connection = Depends(get_db_connection),
):
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    telegram_update = types.Update(**update)
    try:
        await multibot_dispatcher.feed_raw_update(
            bot=aiogram_bot_instance,
            update=telegram_update,
            db_connection=db_connection,
        )
    except TelegramUnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot token is not valid any more, please update it",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=str(e),
        ) from e

    return {}
