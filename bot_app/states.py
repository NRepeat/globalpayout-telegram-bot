from aiogram.fsm.state import State, StatesGroup


class NewRateDiscount(StatesGroup):
    rate_info = State()
    rate_confirmation = State()


class NewManualRate(StatesGroup):
    new_manual_rate_value = State()
    input_confirmation = State()
    new_group_manual_rate_value = State()
