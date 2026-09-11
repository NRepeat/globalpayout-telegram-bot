import datetime
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


def parse_close_order_input(text: str) -> tuple[str, str | Decimal] | None:
    """Ввод на шаге ID ордера Binance: ("order", "<цифры>") — сверить через
    сервис; ("rate", Decimal) — ручной курс; None — мусор.
    Ручной курс принимаем и голым числом («44.12»), не только «курс 44.12»:
    ID от курса отличается сам — длинное целое из цифр против короткого числа."""
    s = text.strip()
    if s.lower().startswith("курс"):
        rate = parse_close_rate(s[4:])
        return ("rate", rate) if rate is not None else None
    # ID P2P-ордера — только ASCII-цифры (isdigit() пропускает юникод-цифры)
    if len(s) >= 5 and s.isascii() and s.isdigit():
        return ("order", s)
    # только ASCII: Decimal молча глотает юникод-цифры («١٢٣»), а это мусор
    if s.isascii():
        rate = parse_close_rate(s)
        if rate is not None:
            return ("rate", rate)
    return None
