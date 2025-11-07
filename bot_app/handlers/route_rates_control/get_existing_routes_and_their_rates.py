from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.exchange_methods import APIError, RouteResponse
from bot_app.markup.base import (
    RouteSelectionOperations,
    route_edit_options_menu_markup,
    route_selection_markup,
)
from bot_app.message_templates import direction_current_information
from bot_app.misc import aiogram_router, box_exchanger_client


@aiogram_router.message(Command("rate"))
async def start_rates_control_menu(
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
        all_routes: list[RouteResponse] = await box_exchanger_client.get_routes()
    except APIError as e:
        await message.answer(
            f"Помилка при отриманні списку напрямків. {e.message}, {e.error_code}"
        )
        return
    uah_active_routes = [
        route
        for route in all_routes
        if route.active
        and ("UAH" in route.to.currency.xml or "UAH" in route.from_.currency.xml)
    ]
    await message.answer(
        f"{user.linked_name_and_username()}, Оберіть напрямок (показано лише активні напрямки з валютою UAH)",
        reply_markup=route_selection_markup(uah_active_routes, message.from_user.id),
    )


@aiogram_router.callback_query(RouteSelectionOperations.filter(F.action == "cancel"))
async def cancel_route_selection(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: RouteSelectionOperations,
):
    if not await get_user_by_id(db_connection, call.from_user.id):
        await save_user(db_connection, call.from_user)
        await call.answer("Меню викликане іншим користувачем. Доступ заборонено")
        return

    if callback_data.user_caller_id != call.from_user.id:
        await call.answer("Меню викликане іншим користувачем. Доступ заборонено")
        return

    await call.answer("Ви відмінили вибір напрямку", show_alert=True)
    await call.message.delete()


@aiogram_router.callback_query(RouteSelectionOperations.filter(F.action == "select"))
async def edit_discounts(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: RouteSelectionOperations,
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
        await call.answer(
            f"Помилка при отриманні інформації про напрямок. {e.message}, {e.error_code}",
            show_alert=True,
        )
        return
    await call.answer()
    await call.message.delete()
    from_currency_code = route.from_.currency.xml
    text_to_send = direction_current_information(route, from_currency_code)
    await call.message.answer(
        f"{user.linked_name_and_username()}, {text_to_send}",
        reply_markup=route_edit_options_menu_markup(route, call.from_user.id),
    )
