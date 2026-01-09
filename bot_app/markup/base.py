from aiogram.filters.callback_data import CallbackData
from aiogram.types.reply_keyboard_markup import ReplyKeyboardMarkup
from aiogram.utils.keyboard import (
    InlineKeyboardBuilder,
    InlineKeyboardMarkup,
)
from typing_extensions import List

from bot_app.exchange_methods import (
    GroupResponse,
    GroupsListResponse,
    RouteId,
    RouteResponse,
)


class ReportPeriodSelection(CallbackData, prefix="report"):
    period: str


def get_report_period_markup() -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    m.button(text="Сьогодні", callback_data=ReportPeriodSelection(period="today"))
    m.button(text="Останні 7 днів", callback_data=ReportPeriodSelection(period="7days"))
    m.button(
        text="Останні 30 днів", callback_data=ReportPeriodSelection(period="30days")
    )
    m.button(
        text="Останні 90 днів", callback_data=ReportPeriodSelection(period="90days")
    )
    return m.adjust(2).as_markup()


class RouteSelectionOperations(CallbackData, prefix="route"):
    route_external_id: str
    user_caller_id: int
    action: str


class GroupSelectionOperations(CallbackData, prefix="group"):
    group_external_id: str
    user_caller_id: int
    action: str


class TransactionOperations(CallbackData, prefix="tx"):
    transaction_uuid: str
    action: str


class CancelStateEntering(CallbackData, prefix="cancel"):
    action: str


class ApproveOrCancelUpdatingRateDiscounts(CallbackData, prefix="discount_rate"):
    action: str


class ApproveOrCancelNewManualRate(CallbackData, prefix="manual_rate"):
    action: str


def approve_or_cancel_updating_group_rate_markup() -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    m.button(
        text="✅ Підтвердити",
        callback_data=ApproveOrCancelNewManualRate(action="group_aprove"),
    )
    m.button(
        text="❌ Відмінити",
        callback_data=ApproveOrCancelNewManualRate(action="cancel"),
    )
    keyboard = m.adjust(2).as_markup()
    return keyboard


def approve_or_cancel_updating_rate_discounts_markup() -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    m.button(
        text="✅ Підтвердити",
        callback_data=ApproveOrCancelUpdatingRateDiscounts(action="approve"),
    )
    m.button(
        text="❌ Відмінити",
        callback_data=ApproveOrCancelUpdatingRateDiscounts(action="cancel"),
    )
    keyboard = m.adjust(2).as_markup()
    return keyboard


def approve_or_cancel_new_manual_rate() -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    m.button(
        text="✅ Підтвердити",
        callback_data=ApproveOrCancelNewManualRate(action="approve"),
    )
    m.button(
        text="❌ Відмінити",
        callback_data=ApproveOrCancelNewManualRate(action="cancel"),
    )
    keyboard = m.adjust(2).as_markup()
    return keyboard


def route_edit_options_menu_markup(
    route: RouteResponse, user_caller_id: int
) -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    m.button(
        text="🔄 Змінити знижки",
        callback_data=RouteSelectionOperations(
            user_caller_id=user_caller_id,
            route_external_id=route.id,
            action="edit_discounts",
        ),
    )
    m.button(
        text="💱 Установити новий курс обміну вручну",
        callback_data=RouteSelectionOperations(
            user_caller_id=user_caller_id,
            route_external_id=route.id,
            action="edit_rate",
        ),
    )
    if route.rate.enable_parser:
        m.button(
            text="🛑 Вимкнути парсер",
            callback_data=RouteSelectionOperations(
                user_caller_id=user_caller_id,
                route_external_id=route.id,
                action="disable_parser",
            ),
        )
    else:
        m.button(
            text="🟢 Увімкнути парсер",
            callback_data=RouteSelectionOperations(
                user_caller_id=user_caller_id,
                route_external_id=route.id,
                action="enable_parser",
            ),
        )

    m.button(
        text="❌ Відмінити",
        callback_data=RouteSelectionOperations(
            user_caller_id=user_caller_id,
            route_external_id=route.id,
            action="cancel",
        ),
    )
    keyboard = m.adjust(1).as_markup()
    return keyboard


def cancel_state_entering_markup() -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    m.button(
        text="❌ Відмінити",
        callback_data=CancelStateEntering(action="cancel"),
    )
    keyboard = m.adjust(1).as_markup()
    return keyboard


def claim_transaction_markup(transaction_uuid: str) -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    m.button(
        text="🗃️ Взяти в роботу",
        callback_data=TransactionOperations(
            transaction_uuid=transaction_uuid, action="claim"
        ),
    )
    keyboard = m.adjust(1).as_markup()
    return keyboard


def finish_transaction_processing(transaction_uuid: str) -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    m.button(
        text="✅ Сплачений",
        callback_data=TransactionOperations(
            transaction_uuid=transaction_uuid, action="completed"
        ),
    )
    m.button(
        text="❌ Невдалий",
        callback_data=TransactionOperations(
            transaction_uuid=transaction_uuid, action="failed"
        ),
    )
    keyboard = m.adjust(2).as_markup()
    return keyboard


def route_selection_markup(
    routes: list[RouteResponse], user_caller_id: int
) -> InlineKeyboardMarkup:
    m = InlineKeyboardBuilder()
    for route in routes:
        m.button(
            text=route.get_formatted_route_name(),
            callback_data=RouteSelectionOperations(
                user_caller_id=user_caller_id,
                route_external_id=route.id,
                action="select",
            ),
        )
    m.button(
        text="❌ Відмінити",
        callback_data=RouteSelectionOperations(
            user_caller_id=user_caller_id, route_external_id="", action="cancel"
        ),
    )
    keyboard = m.adjust(1).as_markup()
    return keyboard


def group_route_selection_markup(
    routes: List[RouteId],
    group_external_id: str,
    user_caller_id: int,
    parsers_enabled_for_group: bool = None,
) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
    m = InlineKeyboardBuilder()
    # for route in routes:
    #     m.button(
    #         text=route.get_formatted_route_name(),
    #         callback_data=RouteSelectionOperations(
    #             user_caller_id=user_caller_id,
    #             route_external_id=route.id,
    #             action="select",
    #         ),
    #     )

    m.button(
        text="❌ Відмінити",
        callback_data=GroupSelectionOperations(
            user_caller_id=user_caller_id, group_external_id="", action="cancel"
        ),
    )

    m.button(
        text="Редагувати курс групи",
        callback_data=GroupSelectionOperations(
            user_caller_id=user_caller_id,
            group_external_id=group_external_id,
            action="edit",
        ),
    )
    if parsers_enabled_for_group is None:
        m.button(
            text="🟢 Увімкнути парсери групи",
            callback_data=GroupSelectionOperations(
                user_caller_id=user_caller_id,
                group_external_id=group_external_id,
                action="enable_group_parser",
            ),
        )
        m.button(
            text="🛑 Вимкнути парсери групи",
            callback_data=GroupSelectionOperations(
                user_caller_id=user_caller_id,
                group_external_id=group_external_id,
                action="disable_group_parser",
            ),
        )
    elif parsers_enabled_for_group:
        m.button(
            text="🛑 Вимкнути парсери групи",
            callback_data=GroupSelectionOperations(
                user_caller_id=user_caller_id,
                group_external_id=group_external_id,
                action="disable_group_parser",
            ),
        )
    else:  # False
        m.button(
            text="🟢 Увімкнути парсери групи",
            callback_data=GroupSelectionOperations(
                user_caller_id=user_caller_id,
                group_external_id=group_external_id,
                action="enable_group_parser",
            ),
        )
    keyboard = m.adjust(1).as_markup()
    return keyboard


def group_selection_markup(
    groups: GroupsListResponse, user_caller_id: int
) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
    m = InlineKeyboardBuilder()

    # FIX 1: Iterate over groups.groups, which is the actual list
    for group in groups.groups:
        m.button(
            text=group.name,
            callback_data=GroupSelectionOperations(
                user_caller_id=user_caller_id,
                group_external_id=group.id,
                action="select",
            ),
        )

    m.button(
        text="❌ Відмінити",
        callback_data=GroupSelectionOperations(
            user_caller_id=user_caller_id, group_external_id="", action="cancel"
        ),
    )
    keyboard = m.adjust(2).as_markup()
    return keyboard
