"""Картка-заглушка у спільному чаті має оновлюватись після закриття.

Заявка, яка переїхала в робочу групу, у спільному чаті лишалась зі статусом
`in_progress` назавжди: там її правлять лише в момент узяття. По спільному
чату було не видно, що заявка вже закрита.

Запуск: python test_common_card.py
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bot_app.handlers.transaction_processing.finish_transaction_processing as mod

COMMON_CHAT = -100111
WORK_GROUP = -100999
MOD = "bot_app.handlers.transaction_processing.finish_transaction_processing"


def run(worked_chat_id, posted=(COMMON_CHAT, 500)):
    transaction = SimpleNamespace(
        uuid="u-1",
        get_telegram_formatted_application=AsyncMock(return_value="картка completed"),
    )
    bot = SimpleNamespace(edit_message_caption=AsyncMock())
    with patch(f"{MOD}.get_posted_message", AsyncMock(return_value=posted)), patch(
        f"{MOD}.aiogram_bot_instance", bot
    ):
        asyncio.run(mod._refresh_common_card(None, worked_chat_id, transaction))
    return bot


def test_updates_stub_when_work_happened_elsewhere():
    bot = run(WORK_GROUP)
    kwargs = bot.edit_message_caption.await_args.kwargs
    assert kwargs["chat_id"] == COMMON_CHAT
    assert kwargs["message_id"] == 500
    assert kwargs["caption"] == "картка completed"
    assert kwargs["reply_markup"] is None


def test_no_double_edit_when_worked_in_common_chat():
    bot = run(COMMON_CHAT)
    bot.edit_message_caption.assert_not_awaited()


def test_no_posted_message_is_not_an_error():
    bot = run(WORK_GROUP, posted=None)
    bot.edit_message_caption.assert_not_awaited()


if __name__ == "__main__":
    test_updates_stub_when_work_happened_elsewhere()
    test_no_double_edit_when_worked_in_common_chat()
    test_no_posted_message_is_not_an_error()
    print("OK: картка у спільному чаті оновлюється після закриття")
