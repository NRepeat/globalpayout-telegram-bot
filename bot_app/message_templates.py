from bot_app.exchange_methods import RouteResponse


def direction_current_information(route: RouteResponse, from_currency_code: str):
    discounts_info = route.get_current_discounts_text()

    return f"""<b>Напрямок обміну</b>

{route.get_formatted_route_name()}

{discounts_info}

{route.get_rate_information_in_text_format()}Будь ласка, виберіть, що ви хочете зробити:"""


def format_discount_input_example(route: RouteResponse, from_currency_code: str):
    discounts_info = route.get_current_discounts_text()

    return f"""<b>Налаштування знижок для обмінної операції</b>\n{route.get_formatted_route_name()}\n{discounts_info}\n
Порядок введення: &lt;базова сума&gt; &lt;відсоток знижки&gt;

Приклади:
<code>100 10</code>
<code>733 30</code>

Деталізація:
- При обміні від 100 <b>{from_currency_code}</b> буде застосована знижка 10%
- При обміні від 733 <b>{from_currency_code}</b> буде застосована знижка 30%

Важливі умови:
- Дозволено вводити одне або декілька значень знижок
- Кожне нове налаштування повністю замінює попередні параметри знижок
"""


def new_manual_rate_input(route: RouteResponse):
    ## we should accept from and to here
    return f"""<b>Введення нового курсу обміну вручну</b>

<b>Напрямок обміну</b>
{route.get_formatted_route_name()}

Введіть новий курс обміну в форматі &lt;курс from&gt; &lt;курс to&gt;

Приклади:
<code>27.5 1</code>
<code>1 27.5</code>
"""
