"""Валидация ввода шагов закрытия (ID ордера / курс) — чистые функции без
сети и БД. Импорт bot_app целиком тянет aiogram и живой токен, поэтому
utils.py грузим напрямую файлом. Запуск: pytest test_close_input.py"""

import importlib.util
import pathlib
from decimal import Decimal

_spec = importlib.util.spec_from_file_location(
    "bot_utils", pathlib.Path(__file__).parent / "bot_app" / "utils.py"
)
utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(utils)


def test_parse_close_rate():
    # деньги: запятая оператора не должна валить шаг, мусор не должен пройти
    assert utils.parse_close_rate(" 41,25 ") == Decimal("41.25")
    assert utils.parse_close_rate("41.25") == Decimal("41.25")
    assert utils.parse_close_rate("0") is None  # ноль — всегда опечатка
    assert utils.parse_close_rate("-1") is None
    assert utils.parse_close_rate("41.2.5") is None
    assert utils.parse_close_rate("сорок") is None
    assert utils.parse_close_rate("inf") is None
    assert utils.parse_close_rate("nan") is None


def test_parse_close_order_input():
    # ID ордера — только ASCII-цифры, длина от 5
    assert utils.parse_close_order_input(" 20250910123 ") == ("order", "20250910123")
    # короткое число — ручной курс голым числом (гард бухгалтера — в хендлере)
    assert utils.parse_close_order_input("1234") == ("rate", Decimal("1234"))
    assert utils.parse_close_order_input("44,12") == ("rate", Decimal("44.12"))
    assert utils.parse_close_order_input("12a45") is None
    assert utils.parse_close_order_input("١٢٣٤٥") is None  # юникод-цифры — не ордер
    # ручной обход «курс N»
    assert utils.parse_close_order_input("курс 41,25") == ("rate", Decimal("41.25"))
    assert utils.parse_close_order_input("Курс 41.25") == ("rate", Decimal("41.25"))
    assert utils.parse_close_order_input("курс ноль") is None
    assert utils.parse_close_order_input("курс 0") is None


# config.py тоже грузим файлом: пакет bot_app тянет aiogram и живой токен
_cfg_spec = importlib.util.spec_from_file_location(
    "bot_config", pathlib.Path(__file__).parent / "bot_app" / "config.py"
)
config = importlib.util.module_from_spec(_cfg_spec)
_cfg_spec.loader.exec_module(config)


def test_bookkeeper_ids():
    # env через запятую; пробелы, пустые хвосты и мусор не валят гард
    s = config.Settings(BOOKKEEPER_TG_IDS=" 111, 222,,abc, -5 ")
    assert s.bookkeeper_ids == frozenset({111, 222})
    assert config.Settings(BOOKKEEPER_TG_IDS="").bookkeeper_ids == frozenset()
