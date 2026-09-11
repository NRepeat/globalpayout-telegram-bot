"""Відмова від заявки: заявка має повернутись у спільний чат і стати вільною.

Найнебезпечніше тут — «відпустити наполовину»: зняти менеджера, але не
повернути кнопку «Взяти», і заявка зникне для всіх. Перевіряємо обидві гілки:
коли картку у спільному чаті вдалось поправити і коли ні.

Запуск: python test_decline.py
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramBadRequest

import bot_app.handlers.transaction_processing.decline_transaction as mod

COMMON_CHAT = -100111
WORK_GROUP = -100999
UUID = "u-1"

MOD = "bot_app.handlers.transaction_processing.decline_transaction"


def call_stub(chat_id):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            delete=AsyncMock(),
        ),
        answer=AsyncMock(),
    )


def run(*, chat_id, released=True, edit_fails=False, posted=(COMMON_CHAT, 500)):
    call = call_stub(chat_id)
    bot = SimpleNamespace(
        edit_message_caption=AsyncMock(
            side_effect=TelegramBadRequest(method=None, message="message to edit not found")
            if edit_fails
            else None
        ),
        send_photo=AsyncMock(return_value=SimpleNamespace(message_id=777)),
    )
    transaction = SimpleNamespace(
        get_telegram_formatted_application=AsyncMock(return_value="картка")
    )
    update_posted = AsyncMock()
    with patch(f"{MOD}.release_transaction", AsyncMock(return_value=released)), patch(
        f"{MOD}.get_transaction_by_uuid", AsyncMock(return_value=transaction)
    ), patch(f"{MOD}.get_posted_message", AsyncMock(return_value=posted)), patch(
        f"{MOD}.get_transaction_target_chat",
        AsyncMock(return_value=SimpleNamespace(chat_tg_id=COMMON_CHAT, record_id=2)),
    ), patch(
        f"{MOD}.update_posted_information", update_posted
    ), patch(f"{MOD}.aiogram_bot_instance", bot):
        asyncio.run(
            mod.decline_transaction(
                call, None, SimpleNamespace(transaction_uuid=UUID)
            )
        )
    return call, bot, update_posted


def test_returns_card_to_common_chat_and_drops_copy():
    call, bot, _ = run(chat_id=WORK_GROUP)
    # копію в робочій групі прибрали
    call.message.delete.assert_awaited()
    # у спільному чаті картка знову з кнопкою «Взяти»
    kwargs = bot.edit_message_caption.await_args.kwargs
    assert kwargs["chat_id"] == COMMON_CHAT
    assert kwargs["message_id"] == 500
    assert kwargs["reply_markup"].inline_keyboard[0][0].text == "🗃️ Взяти в роботу"


def test_declined_in_common_chat_keeps_message():
    call, bot, _ = run(chat_id=COMMON_CHAT)
    # тут копії немає — видаляти нічого
    call.message.delete.assert_not_awaited()
    bot.edit_message_caption.assert_awaited()


def test_lost_message_is_reposted_not_silently_dropped():
    _, bot, update_posted = run(chat_id=WORK_GROUP, edit_fails=True)
    # картку у спільному чаті не знайшли — публікуємо заново, інакше заявка
    # стане невидимою для всіх
    bot.send_photo.assert_awaited()
    update_posted.assert_awaited()


def test_foreign_transaction_is_refused():
    call, bot, _ = run(chat_id=WORK_GROUP, released=False)
    bot.edit_message_caption.assert_not_awaited()
    call.message.delete.assert_not_awaited()
    assert "не у вас" in call.answer.await_args.args[0]


if __name__ == "__main__":
    test_returns_card_to_common_chat_and_drops_copy()
    test_declined_in_common_chat_keeps_message()
    test_lost_message_is_reposted_not_silently_dropped()
    test_foreign_transaction_is_refused()
    print("OK: відмова повертає заявку у спільний чат, загубити її не можна")
