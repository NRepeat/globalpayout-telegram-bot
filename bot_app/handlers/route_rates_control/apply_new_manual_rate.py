from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.exchange_methods import APIError, RouteResponse
from bot_app.markup.base import (
    ApproveOrCancelNewManualRate,
    RouteSelectionOperations,
    approve_or_cancel_new_manual_rate,
    cancel_state_entering_markup,
)
from bot_app.message_templates import new_manual_rate_input
from bot_app.misc import aiogram_bot_instance, aiogram_router, box_exchanger_client
from bot_app.states import NewManualRate


@aiogram_router.callback_query(RouteSelectionOperations.filter(F.action == "edit_rate"))
async def edit_manual_rate(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: RouteSelectionOperations,
    state: FSMContext,
):
    user = await get_user_by_id(db_connection, call.from_user.id)
    if not user:
        await save_user(db_connection, call.from_user)
        await call.answer("Меню викликане іншим користувачем. Доступ заборонено")
        return

    if callback_data.user_caller_id != call.from_user.id:
        await call.answer("Меню викликане іншим користувачем. Доступ заборонено")
        return
    try:
        route: RouteResponse = await box_exchanger_client.get_route_by_id(
            callback_data.route_external_id
        )
    except APIError as e:
        await call.answer()
        await aiogram_bot_instance.send_message(
            chat_id=call.message.chat.id,
            text=f"{user.linked_name_and_username()}, Помилка при отриманні інформації про напрямок. {e.message}, {e.error_code}",
        )
        return

    await call.answer()
    await call.message.delete()
    from_currency_code = route.from_.currency.xml
    text_to_send = new_manual_rate_input(route)
    await state.set_state(NewManualRate.new_manual_rate_value)
    await state.update_data(
        route_id=route.id,
        route_name=route.get_formatted_route_name(),
        currency_from=from_currency_code,
    )
    message = await call.message.answer(
        f"{user.linked_name_and_username()}, {text_to_send}",
        reply_markup=cancel_state_entering_markup(),
    )
    await state.update_data(message_id_to_delete=message.message_id)


@aiogram_router.message(NewManualRate.new_manual_rate_value, F.text)
async def accept_new_manual_rate_values(
    message: Message, state: FSMContext, db_connection: Connection
):
    user = await get_user_by_id(db_connection, message.from_user.id)

    try:
        rate_from, rate_to = map(float, message.text.split())
    except ValueError:
        await message.answer("Неправильний формат введення. Спробуйте ще раз")
        return
    state_data = await state.get_data()
    await state.set_state(NewManualRate.input_confirmation)

    await state.update_data(rate_from=rate_from, rate_to=rate_to)

    # TODO Show current rate and your rate

    text = f"{user.linked_name_and_username()}, Ви запропонували наступні курсов \n{state_data['route_name']}:\n\n{message.text}\n\nПідтверджуєте застосування?"

    await aiogram_bot_instance.delete_message(
        chat_id=message.chat.id, message_id=state_data["message_id_to_delete"]
    )
    await message.answer(
        text,
        reply_markup=approve_or_cancel_new_manual_rate(),
    )


@aiogram_router.callback_query(
    ApproveOrCancelNewManualRate.filter(F.action == "cancel")
)
async def cancel_rate_discounts(
    call: CallbackQuery, state: FSMContext, db_connection: Connection
):
    await state.clear()
    await call.answer("Ви скасували введення", show_alert=True)
    await call.message.delete()


@aiogram_router.callback_query(
    ApproveOrCancelNewManualRate.filter(F.action == "approve")
)
async def approve_rate_discounts(
    call: CallbackQuery, state: FSMContext, db_connection: Connection
):
    user = await get_user_by_id(db_connection, call.from_user.id)
    state_data = await state.get_data()
    await state.clear()
    await call.message.delete()
    try:
        await box_exchanger_client.update_manual_rate(
            state_data["route_id"], state_data["rate_from"], state_data["rate_to"], 1
        )
    except APIError as e:
        await call.answer()
        await aiogram_bot_instance.send_message(
            chat_id=call.message.chat.id,
            text=f"{user.linked_name_and_username()}, Помилка при встановленні курсу. {e.message}, {e.error_code}",
        )

        return

    try:
        route: RouteResponse = await box_exchanger_client.get_route_by_id(
            state_data["route_id"]
        )
    except APIError as e:
        await aiogram_bot_instance.send_message(
            chat_id=call.message.chat.id,
            text=f"{user.linked_name_and_username()}, Помилка при отриманні інформації про напрямок. {e.message}, {e.error_code}",
        )
        return

    await aiogram_bot_instance.send_message(
        chat_id=call.message.chat.id,
        text=f"{user.linked_name_and_username()}, Курс обміну успішно змінено\n {route.get_formatted_route_name()} \n{route.get_rate_information_in_text_format()}",
    )
