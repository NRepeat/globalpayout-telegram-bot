import datetime
import re
from decimal import Decimal, InvalidOperation


def format_unix_timestamp(unix_ms: int) -> str:
    # Convert milliseconds to seconds by dividing by 1000
    unix_seconds = unix_ms / 1000
    # Convert to datetime object
    dt = datetime.datetime.fromtimestamp(unix_seconds)
    # Format to match the desired output
    formatted_date = dt.strftime("%a %b %d %Y %H:%M:%S")
    return formatted_date


def parse_close_rate(text: str) -> Decimal | None:
    """Курс закрытия из ввода оператора: запятая — тоже точка, ноль и мусор —
    отказ (курс нулевым не бывает, ноль здесь всегда опечатка)."""
    s = text.strip().replace(",", ".")
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0:
        return None
    return value


# Оформление списка: маркер или нумерация — не номер ордера
_LIST_NOISE = re.compile(r"^(?:[-–—*•·]|\d{1,3}[.)])$")


def parse_order_ids(text: str) -> list[str] | None:
    """ID ордеров из одного сообщения: закрытие частями — оператор шлёт их
    списком (с новой строки, через пробел или запятую), часто с маркерами или
    нумерацией, копипастой из своих заметок. Номера достаём, оформление
    выбрасываем. Дубли схлопываем: повторённый номер удвоил бы сумму и
    «сошёлся» там, где недоплата.
    None — среди слов есть что-то кроме номера и оформления: это курс или
    мусор, в сверку такой текст пускать нельзя."""
    ids: list[str] = []
    for part in text.replace(",", " ").replace(";", " ").split():
        if _LIST_NOISE.match(part):
            continue
        order_id = part.lstrip("#№")
        # только ASCII-цифры: isdigit() пропускает юникод-цифры («١٢٣»)
        if len(order_id) < 5 or not (order_id.isascii() and order_id.isdigit()):
            return None
        if order_id not in ids:
            ids.append(order_id)
    return ids or None


def parse_close_order_input(text: str) -> tuple[str, list[str] | Decimal] | None:
    """Ввод на шаге ID ордера Binance: ("order", ["<цифры>", ...]) — сверить
    через сервис (несколько ID = закрытие частями); ("rate", Decimal) — ручной
    курс; None — мусор.
    Ручной курс принимаем и голым числом («44.12»), не только «курс 44.12»:
    ID от курса отличается сам — длинное целое из цифр против короткого числа."""
    s = text.strip()
    if s.lower().startswith("курс"):
        rate = parse_close_rate(s[4:])
        return ("rate", rate) if rate is not None else None
    ids = parse_order_ids(s)
    if ids is not None:
        return ("order", ids)
    # только ASCII: Decimal молча глотает юникод-цифры («١٢٣»), а это мусор
    if s.isascii():
        rate = parse_close_rate(s)
        if rate is not None:
            return ("rate", rate)
    return None
