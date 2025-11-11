from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types.callback_query import CallbackQuery

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.exchange_methods import APIError, GroupResponse
from bot_app.handlers.route_rates_control.utils import authorize_user
from bot_app.markup.base import (
    ApproveOrCancelNewManualRate,
    GroupSelectionOperations,
    approve_or_cancel_new_manual_rate,
    approve_or_cancel_updating_group_rate_markup,
    approve_or_cancel_updating_rate_discounts_markup,
    cancel_state_entering_markup,
    group_route_selection_markup,
    group_selection_markup,
)
from bot_app.message_templates import new_manual_group_rate_input, new_manual_rate_input
from bot_app.misc import aiogram_bot_instance, aiogram_router, box_exchanger_client
from bot_app.states import NewManualRate


@aiogram_router.message(Command("groups"))
async def get_group_routes(
    message: Message, db_connection: Connection, state: FSMContext
):
    await state.clear()
    user = await get_user_by_id(db_connection, message.from_user.id)
    if not user:
        await save_user(db_connection, message.from_user)
        await message.answer("Виконання цієї дії дозволено лише старшим операторам")
        return
    if not user.senior_operator:
        await message.answer("Виконання цієї дії дозволено лише старшим операторам")
        return
    try:
        all_groups = await box_exchanger_client.get_groups()
    except APIError as e:
        await message.answer(
            f"Помилка при отриманні списку напрямків. {e.message}, {e.error_code}"
        )
        return
    await message.answer(
        f"{user.linked_name_and_username()}, Оберіть напрямок (показано лише активні напрямки з валютою UAH)",
        reply_markup=group_selection_markup(all_groups, message.from_user.id),
    )


@aiogram_router.callback_query(GroupSelectionOperations.filter(F.action == "select"))
async def edit_discounts(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: GroupSelectionOperations,
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
        group: GroupResponse = await box_exchanger_client.get_group_by_id(
            callback_data.group_external_id
        )
    except APIError as e:
        await call.answer(
            "Помилка при отриманні інформації про напрямок.",
            show_alert=True,
        )
        return
    if call.message is None:
        return
    uah_active_routes = [route for route in group.routeIds]
    await call.answer()
    await call.message.delete()
    await call.message.answer(
        f"{user.linked_name_and_username()}, Оберіть напрямок (показано лише активні напрямки з валютою UAH)",
        reply_markup=group_route_selection_markup(
            uah_active_routes, callback_data.group_external_id, call.from_user.id
        ),
    )


@aiogram_router.callback_query(GroupSelectionOperations.filter(F.action == "edit"))
async def edit_selected_group(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: GroupSelectionOperations,
    state: FSMContext,
):
    if not await authorize_user.authorize(db_connection, call, callback_data):
        return
    if not callback_data.group_external_id:
        return
    group_id = callback_data.group_external_id
    try:
        group: GroupResponse = await box_exchanger_client.get_group_by_id(group_id)
    except APIError as e:
        await call.answer()
        await aiogram_bot_instance.send_message(
            chat_id=call.message.chat.id,
            text=f"Помилка при отриманні інформації про напрямок. {e.message}, {e.error_code}",
        )
        return

    await call.answer()
    await call.message.delete()
    text_to_send = new_manual_group_rate_input(group.name)
    await state.set_state(NewManualRate.new_group_manual_rate_value)
    await state.update_data(
        group_id=group_id,
        group_name=group.name,
    )
    message = await call.message.answer(
        f"{text_to_send}",
        reply_markup=cancel_state_entering_markup(),
    )

    await state.update_data(message_id_to_delete=message.message_id)


@aiogram_router.message(NewManualRate.new_group_manual_rate_value, F.text)
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
    print(state_data, "state_data")
    # TODO Show current rate and your rate

    text = f"{user.linked_name_and_username()}, Ви запропонували наступні курсов \n{state_data['group_name']}:\n\n{message.text}\n\nПідтверджуєте застосування?"

    await aiogram_bot_instance.delete_message(
        chat_id=message.chat.id, message_id=state_data["message_id_to_delete"]
    )
    print("approve_or_cancel_updating_group_rate_markup")
    await message.answer(
        text,
        reply_markup=approve_or_cancel_updating_group_rate_markup(),
    )


@aiogram_router.callback_query(
    ApproveOrCancelNewManualRate.filter(F.action == "group_aprove")
)
async def approve_gropu_rate(
    call: CallbackQuery,
    state: FSMContext,
    db_connection: Connection,
    callback_data: ApproveOrCancelNewManualRate,
):
    user = await get_user_by_id(db_connection, call.from_user.id)
    state_data = await state.get_data()
    await state.clear()
    await call.message.delete()
    try:
        await box_exchanger_client.update_manual_group_rate(
            state_data["group_id"], state_data["rate_from"], state_data["rate_to"], 1
        )
    except APIError as e:
        await call.answer()
        await aiogram_bot_instance.send_message(
            chat_id=call.message.chat.id,
            text=f"{user.linked_name_and_username()}, Помилка при встановленні курсу. {e.message}, {e.error_code}",
        )

        return

    try:
        group: GroupResponse = await box_exchanger_client.get_group_by_id(
            state_data["group_id"]
        )
    except APIError as e:
        await aiogram_bot_instance.send_message(
            chat_id=call.message.chat.id,
            text=f"{user.linked_name_and_username()}, Помилка при отриманні інформації про напрямок. {e.message}, {e.error_code}",
        )
        return

    await aiogram_bot_instance.send_message(
        chat_id=call.message.chat.id,
        text=f"{user.linked_name_and_username()}, Курс обміну успішно змінено\n {group.name} \n",
    )


@aiogram_router.callback_query(GroupSelectionOperations.filter(F.action == "cancel"))
async def cancel_route_selection(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: GroupSelectionOperations,
):
    if not await get_user_by_id(db_connection, call.from_user.id):
        await save_user(db_connection, call.from_user)
        await call.answer("Меню викликане іншим користувачем. Доступ заборонено")
        return

    if callback_data.user_caller_id != call.from_user.id:
        await call.answer("Меню викликане іншим користувачем. Доступ заборонено")
        return

    await call.answer("Ви відмінили вибір групи", show_alert=True)
    await call.message.delete()
