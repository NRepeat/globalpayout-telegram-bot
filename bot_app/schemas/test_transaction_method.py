"""Проверка нормализации метода выплаты: python3 -m bot_app.schemas.test_transaction_method"""

from bot_app.schemas.transaction import NewTransaction

BASE = {
    "external_order_id": "2033",
    "currency": "UAH",
    "currency_xml_code": "P24UAH",
    "amount": 20119.76,
}


def build(**kw) -> NewTransaction:
    return NewTransaction(**{**BASE, **kw})


def main() -> None:
    # Карточный пресет на банковском направлении: плагин прислал iban_uah,
    # реквизиты — карта, iban/inn строкой "undefined".
    t = build(
        method_type=1,
        service_name="iban_uah",
        card_number="5168745029729750",
        full_name="Nikita Nazarov",
        iban="undefined",
        inn="undefined",
    )
    assert t.method_type == 0, t.method_type
    assert t.service_name == "card_uah", t.service_name

    # Обратный случай: метод карточный, а пришёл IBAN.
    t = build(method_type=0, service_name="card_uah", iban="UA273348510000026206122148382")
    assert (t.method_type, t.service_name) == (1, "iban_uah")

    # Нормальные заявки не трогаем.
    t = build(method_type=1, service_name="iban_uah", iban="UA27", inn="3377110113")
    assert (t.method_type, t.service_name) == (1, "iban_uah")
    t = build(method_type=0, service_name="card_uah", card_number="5168745029729750")
    assert (t.method_type, t.service_name) == (0, "card_uah")

    # Чужие методы (крипта, SEPA, e-wallet) остаются как есть.
    t = build(method_type=5, service_name="usdt_ton", wallet_address="TJhCY")
    assert (t.method_type, t.service_name) == (5, "usdt_ton")
    t = build(method_type=2, service_name="sepa", iban="DE89", currency="EUR")
    assert (t.method_type, t.service_name) == (2, "sepa")

    print("transaction method normalization: ok")


if __name__ == "__main__":
    main()
