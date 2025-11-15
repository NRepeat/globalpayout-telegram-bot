from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.exchange_methods import APIError
from bot_app.markup.base import GroupSelectionOperations, group_route_selection_markup
from bot_app.misc import aiogram_router, box_exchanger_client


@aiogram_router.callback_query(
    GroupSelectionOperations.filter(F.action == "disable_group_parser")
)
async def disable_parser_for_group(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: GroupSelectionOperations,
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
        await box_exchanger_client.change_parser_state_for_group(
            callback_data.group_external_id, False
        )
    except APIError as e:
        await call.answer(
            f"Помилка при вимкненні парсерів для групи. {e.message}, {e.error_code}",
            show_alert=True,
        )
        return

    await call.answer("Парсери для групи вимкнено.")

    try:
        group = await box_exchanger_client.get_group_by_id(
            callback_data.group_external_id
        )
    except APIError as e:
        await call.answer(f"Помилка при оновленні меню: {e.message}", show_alert=True)
        return

    await call.message.edit_reply_markup(
        reply_markup=group_route_selection_markup(
            group.routeIds,
            group.id,
            call.from_user.id,
            parsers_enabled_for_group=False,
        )
    )


@aiogram_router.callback_query(
    GroupSelectionOperations.filter(F.action == "enable_group_parser")
)
async def enable_parser_for_group(
    call: CallbackQuery,
    db_connection: Connection,
    callback_data: GroupSelectionOperations,
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
        await box_exchanger_client.change_parser_state_for_group(
            callback_data.group_external_id, True
        )
    except APIError as e:
        await call.answer(
            f"Помилка при включенні парсерів для групи. {e.message}, {e.error_code}",
            show_alert=True,
        )
        return

    await call.answer("Парсери для групи включено.")

    try:
        group = await box_exchanger_client.get_group_by_id(
            callback_data.group_external_id
        )
    except APIError as e:
        await call.answer(f"Помилка при оновленні меню: {e.message}", show_alert=True)
        return

    await call.message.edit_reply_markup(
        reply_markup=group_route_selection_markup(
            group.routeIds,
            group.id,
            call.from_user.id,
            parsers_enabled_for_group=True,
        )
    )
