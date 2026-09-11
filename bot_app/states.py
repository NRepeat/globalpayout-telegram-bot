from aiogram.fsm.state import State, StatesGroup


class NewRateDiscount(StatesGroup):
    rate_info = State()
    rate_confirmation = State()


class NewManualRate(StatesGroup):
    new_manual_rate_value = State()
    input_confirmation = State()
    new_group_manual_rate_value = State()


class CloseTransaction(StatesGroup):
    """Обязательные шаги закрытия заявки: квитанция → площадка → курс.
    Ничего не пишем в БД до финала — отмена на любом шаге бесследна."""

    receipt = State()  # ждём скрин/квитанцию выплаты
    account = State()  # выбор площадки кнопками (биржи или партнёр)
    partner_name = State()  # «Партнёр»: имя текстом
    order_id = State()  # Binance: ID P2P-ордера (или «курс N» вручную)
    rate = State()  # остальные площадки: курс закрытия числом
