from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.exchange_methods import APIError
from bot_app.markup.base import (
    RouteSelectionOperations,
    route_edit_options_menu_markup,
)
from bot_app.message_templates import direction_current_information
from bot_app.misc import aiogram_router, box_exchanger_client


@aiogram_router.callback_query(
    RouteSelectionOperations.filter(F.action == "disable_parser")
)
async def disable_parser(
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
        await box_exchanger_client.change_parser_state(
            callback_data.route_external_id, False
        )
    except APIError as e:
        await call.answer(
            f"Помилка при вимкненні парсера. {e.message}, {e.error_code}",
            show_alert=True,
        )

    try:
        route = await box_exchanger_client.get_route_by_id(
            callback_data.route_external_id
        )
    except APIError as e:
        await call.answer(
            f"Помилка при отриманні інформації про напрямок. {e.message}, {e.error_code}",
            show_alert=True,
        )
        return
    if route.rate.enable_parser:
        await call.answer(
            "Помилка при вимкненні парсера. Спробуйте ще раз", show_alert=True
        )
        return
    await call.answer()
    from_currency_code = route.from_.currency.xml
    text_to_send = direction_current_information(route, from_currency_code)
    await call.message.edit_text(
        f"{user.linked_name_and_username()}, {text_to_send}",
        reply_markup=route_edit_options_menu_markup(route, call.from_user.id),
    )


@aiogram_router.callback_query(
    RouteSelectionOperations.filter(F.action == "enable_parser")
)
async def enable_parser(
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
        await box_exchanger_client.change_parser_state(
            callback_data.route_external_id, True
        )
    except APIError as e:
        await call.answer(
            f"Помилка при включенні парсера. {e.message}, {e.error_code}",
            show_alert=True,
        )

    try:
        route = await box_exchanger_client.get_route_by_id(
            callback_data.route_external_id
        )
    except APIError as e:
        await call.answer(
            f"Помилка при отриманні інформації про напрямок. {e.message}, {e.error_code}",
            show_alert=True,
        )
        return
    if not route.rate.enable_parser:
        await call.answer(
            "Помилка при включенні парсера. Спробуйте ще раз", show_alert=True
        )
        return
    await call.answer()
    from_currency_code = route.from_.currency.xml
    text_to_send = direction_current_information(route, from_currency_code)
    await call.message.edit_text(
        f"{user.linked_name_and_username()}, {text_to_send}",
        reply_markup=route_edit_options_menu_markup(route, call.from_user.id),
    )
