"""Раздел суточной сводки: по нему считают день, поэтому суммы и разрезы
проверяем отдельно. Запуск: python test_daily_summary.py"""

from bot_app.daily_summary import build_lines


def test_totals_and_breakdown():
    rows = [
        {"manager": "artem", "account": "binance", "cnt": 2, "amount": 1500.5},
        {"manager": "artem", "account": "bybit", "cnt": 1, "amount": 250},
        {"manager": "alina", "account": "binance", "cnt": 3, "amount": 900},
    ]
    lines = build_lines(rows, unclosed=2)

    assert lines[0] == "💰 Закрыто заявок: 6 на 2650.50 USDT", lines[0]
    assert "👤 artem — 3 заявок, 1750.50 USDT" in lines, lines
    assert "👤 alina — 3 заявок, 900.00 USDT" in lines, lines
    # площадки считаются поперёк операторов
    assert "🏦 binance — 5 заявок, 2400.50 USDT" in lines, lines
    assert "🏦 bybit — 1 заявок, 250.00 USDT" in lines, lines
    assert "⚠️ Незакрытых заявок: 2" in lines, lines


def test_empty_day():
    lines = build_lines([], unclosed=0)
    assert lines == ["💰 Закрыто заявок: 0 на 0.00 USDT"], lines


def test_unclosed_only_when_present():
    lines = build_lines([{"manager": "x", "account": "binance", "cnt": 1, "amount": 10}], 0)
    assert not any("Незакрытых" in line for line in lines), lines


if __name__ == "__main__":
    test_totals_and_breakdown()
    test_empty_day()
    test_unclosed_only_when_present()
    print("OK: раздел сводки считается верно")
