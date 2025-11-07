import re

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id, save_user
from bot_app.exchange_methods import APIError, Discount, RouteResponse
from bot_app.markup.base import (
    ApproveOrCancelUpdatingRateDiscounts,
    CancelStateEntering,
    RouteSelectionOperations,
    approve_or_cancel_updating_rate_discounts_markup,
    cancel_state_entering_markup,
)
from bot_app.message_templates import format_discount_input_example
from bot_app.misc import aiogram_bot_instance, aiogram_router, box_exchanger_client
from bot_app.states import NewRateDiscount

regexp_to_accept_rate = r"^([\d.,]+)\s+([\d.,]+)$"


# Cancel the state entering
@aiogram_router.callback_query(CancelStateEntering.filter(F.action == "cancel"))
async def cancel_state_entering(
    call: CallbackQuery, state: FSMContext, db_connection: Connection
):
    await state.clear()
    await call.message.delete()
    await call.answer("Ви скасували введення", show_alert=True)


@aiogram_router.callback_query(
    RouteSelectionOperations.filter(F.action == "edit_discounts")
)
async def edit_discounts(
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
        await call.answer(
            f"Помилка при отриманні інформації про напрямок. {e.message}, {e.error_code}",
            show_alert=True,
        )
        return
    await call.answer()
    await call.message.delete()
    from_currency_code = route.from_.currency.xml
    text_to_send = format_discount_input_example(route, from_currency_code)
    await state.set_state(NewRateDiscount.rate_info)
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


@aiogram_router.message(NewRateDiscount.rate_info, F.text)
async def accept_new_rate(
    message: Message, state: FSMContext, db_connection: Connection
):
    user = await get_user_by_id(db_connection, message.from_user.id)

    state_data = await state.get_data()
    await state.set_state(NewRateDiscount.rate_confirmation)
    lines = [line.strip() for line in message.text.split("\n") if line.strip()]
    discounts_to_apply: list[Discount] = []
    for line in lines:
        match = re.match(regexp_to_accept_rate, line)
        if match:
            amountMoreThan = float(match.group(1).replace(",", "."))
            discountPercent = float(match.group(2).replace(",", "."))

            discounts_to_apply.append(
                Discount(amountMoreThan=amountMoreThan, discountPercent=discountPercent)
            )

    if not discounts_to_apply:
        await message.answer(
            f"{user.linked_name_and_username()}, Не знайдено коректних параметрів знижок. Використовуйте формат: &lt;сума&gt; &lt;знижка&gt;",
            reply_markup=cancel_state_entering_markup(),
        )
        return

    current_discounts_text = "\n".join(
        [
            f"{discount.discountPercent}% для сум від {discount.amountMoreThan} <b>{state_data['currency_from']}</b>"
            for discount in discounts_to_apply
        ]
    )

    text = f"{user.linked_name_and_username()}, Ви запропонували наступні курсові знижки для напрямку\n{state_data['route_name']}:\n\n{current_discounts_text}\n\nПідтверджуєте застосування?"
    await state.update_data(
        discounts_to_apply=[
            discount.model_dump(mode="json") for discount in discounts_to_apply
        ]
    )
    await aiogram_bot_instance.delete_message(
        chat_id=message.chat.id, message_id=state_data["message_id_to_delete"]
    )
    await message.answer(
        text,
        reply_markup=approve_or_cancel_updating_rate_discounts_markup(),
    )


@aiogram_router.callback_query(
    ApproveOrCancelUpdatingRateDiscounts.filter(F.action == "approve")
)
async def approve_rate_discounts(
    call: CallbackQuery, state: FSMContext, db_connection: Connection
):
    user = await get_user_by_id(db_connection, call.from_user.id)
    state_data = await state.get_data()
    route_id = state_data["route_id"]
    discounts_list: list[Discount] = [
        Discount(**discount) for discount in state_data["discounts_to_apply"]
    ]
    try:
        await box_exchanger_client.update_route_discounts(route_id, discounts_list)
    except APIError as e:
        await call.answer(
            f"Помилка при збереженні знижок. {e.message}, {e.error_code}",
            show_alert=True,
        )
        return
    await state.clear()
    await call.message.answer(
        f"""{user.linked_name_and_username()}, Знижки успішно встановлені""",
    )
    await call.message.delete()
    await call.answer()


@aiogram_router.callback_query(
    ApproveOrCancelUpdatingRateDiscounts.filter(F.action == "cancel")
)
async def cancel_rate_discounts(
    call: CallbackQuery, state: FSMContext, db_connection: Connection
):
    await state.clear()
    await call.message.delete()
    await call.answer("Ви скасували введення", show_alert=True)
