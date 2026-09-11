"""Переїзд взятої заявки в особисту групу оператора.

Перевіряємо межі, на яких можна втратити заявку: групи немає, група та сама,
група недоступна. Запуск: python test_work_group.py
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramBadRequest
from bot_app.handlers.transaction_processing.claim_transaction import move_to_work_group
from bot_app.schemas.user import SavedUser

COMMON_CHAT = -100111
WORK_GROUP = -100999


def call_stub():
    message = SimpleNamespace(
        chat=SimpleNamespace(id=COMMON_CHAT),
        photo=[SimpleNamespace(file_id="photo-1")],
        edit_caption=AsyncMock(),
    )
    return SimpleNamespace(
        from_user=SimpleNamespace(id=42),
        message=message,
        answer=AsyncMock(),
    )


def user(work_group):
    return SavedUser(
        user_id=42,
        name="Аліна",
        user_name="@aa_wrld22",
        senior_operator=False,
        bot_admin=False,
        work_group_chat_id=work_group,
    )


def run(work_group, send_effect=None):
    call = call_stub()
    send = AsyncMock(side_effect=send_effect)
    with patch(
        "bot_app.handlers.transaction_processing.claim_transaction.get_user_by_id",
        AsyncMock(return_value=user(work_group)),
    ), patch(
        "bot_app.handlers.transaction_processing.claim_transaction.aiogram_bot_instance",
        SimpleNamespace(send_photo=send),
    ):
        moved = asyncio.run(
            move_to_work_group(call, None, SimpleNamespace(transaction_uuid="u-1"), "картка")
        )
    return moved, call, send


def test_moves_to_work_group():
    moved, call, send = run(WORK_GROUP)
    assert moved is True
    assert send.await_args.args[0] == WORK_GROUP
    # фото переносимо те саме, інакше editMessageMedia на фіналі впаде
    assert send.await_args.kwargs["photo"] == "photo-1"
    # у спільному чаті лишається слід і зникають кнопки
    caption = call.message.edit_caption.await_args.kwargs["caption"]
    assert "Взята" in caption
    assert call.message.edit_caption.await_args.kwargs["reply_markup"] is None


def test_no_group_keeps_work_in_common_chat():
    moved, _, send = run(None)
    assert moved is False
    send.assert_not_awaited()


def test_same_chat_is_not_a_move():
    moved, _, send = run(COMMON_CHAT)
    assert moved is False
    send.assert_not_awaited()


def test_unavailable_group_falls_back_and_warns():
    error = TelegramBadRequest(method=None, message="chat not found")
    moved, call, _ = run(WORK_GROUP, send_effect=error)
    # заявка не загубилась: працюємо у спільному чаті
    assert moved is False
    assert "робочу групу" in call.answer.await_args.args[0]


if __name__ == "__main__":
    test_moves_to_work_group()
    test_no_group_keeps_work_in_common_chat()
    test_same_chat_is_not_a_move()
    test_unavailable_group_falls_back_and_warns()
    print("OK: переїзд заявки в робочу групу працює, втрати заявки немає")
