"""Автопостинг курсов обмена в группу/канал (ARG-58).

Логика сообщений портирована из telegram_rates_post.py (проверен на боевых данных):
  1. Тянет все направления через внутренний API (box_exchanger_client),
     финальный курс пары = resultExchange.rate.out / resultExchange.rate.in
     (сверено с публичным экспортом: совпадает с xr)
  2. Для категории берёт курс по сети USDT TRC20
  3. Сравнивает с курсом за вчера (rates_history.json рядом с модулем)
  4. Отправляет сообщение(я) в чат settings.RATES_POSTING_CHAT_ID от основного бота

Расписание (таймзона settings.TIME_ZONE):
  10:00 card_account / 15:00 wallets / 20:00 asia

Планировщик запускается фоновой задачей из lifespan (__main__.py).
RATES_POSTING_CHAT_ID = 0 полностью выключает постинг.

Проверка без отправки (в контейнере бота):
  python3 -m bot_app.rates_posting card_account
"""

import asyncio
import json
import logging
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from bot_app.config import settings

logger = logging.getLogger(__name__)

HISTORY_FILE = Path(__file__).resolve().parent / "rates_history.json"
# ponytail: история в файле контейнера — после redeploy первый день без дельты,
# переносить в БД когда это станет проблемой
HISTORY_DAYS_TO_KEEP = 1  # ротация: храним только вчера

EXCHANGE_LINK = "https://www.globalpayout.club/ru/"
MAX_MESSAGE_LEN = 3500  # запас от лимита Telegram в 4096 символов

# Сети USDT, которые пробуем для каждого направления (код валюты "отдаём", подпись сети)
# TRC20 используем как основную сеть, остальные (ERC20/TON/SOL) не берём.
NETWORKS = [
    ("USDTTRC20", "TRC20"),
]

# (время поста, категория) — порт кронтаба из QUICKSTART.txt
SCHEDULE = (
    (time(10, 0), "card_account"),
    (time(15, 0), "wallets"),
    (time(20, 0), "asia"),
)

# Коды и подписи сверены вживую с публичным калькулятором на globalpayout.club/ru/
CATEGORIES = {
    # Карта + счета (включая счёт компании). Азиатские/кавказские валюты сюда
    # не попадают — они целиком уходят в категорию "asia" (см. ниже).
    "card_account": {
        "emoji": "💳",
        "title": "Карта / Счёт",
        "groups": [
            ("🇺🇦 Гривна (UAH)", [
                ("CARDUAH", "Visa/Mastercard"),
                ("MONOBUAH", "Monobank"),
                ("P24UAH", "Privat24"),
                ("RFBUAH", "Райффайзен"),
                ("PMBBUAH", "ПУМБ"),
                ("SNBUAH", "Sense Bank"),
                ("OSDBUAH", "Ощадбанк"),
                ("USBUAH", "Укрсиббанк"),
                ("OTPBUAH", "ОТП Банк"),
                ("ABUAH", "A-Bank"),
                ("IZIBUAH", "izibank"),
                ("TASBUAH", "TAScombank"),
                ("SPBUAH", "Sportbank"),
                ("WIREUAH", "Банковский счёт"),
                ("CORPUAH", "Счёт компании"),
            ]),
            ("🇺🇸 Доллар (USD)", [("CARDUSD", "Visa/Mastercard")]),
            ("🇪🇺 Евро (EUR)", [("CARDEUR", "Visa/Mastercard"), ("SEPAEUR", "SEPA")]),
            ("🇬🇧 Фунт (GBP)", [("CARDGBP", "Visa/Mastercard"), ("WIREGBP", "Банковский счёт")]),
            ("🇨🇦 Канадский доллар (CAD)", [("CARDCAD", "Visa/Mastercard"), ("WIRECAD", "Interac (счёт)")]),
            ("🇳🇬 Найра (NGN)", [("CARDNGN", "Visa/Mastercard"), ("WIRENGN", "Банковский счёт")]),
            ("🇨🇿 Крона (CZK)", [("CARDCZK", "Visa/Mastercard"), ("WIRECZK", "Банковский счёт")]),
            ("🇸🇪 Крона (SEK)", [("CARDSEK", "Visa/Mastercard"), ("WIRESEK", "Банковский счёт")]),
            ("🇲🇩 Лей (MDL)", [("CARDMDL", "Visa/Mastercard")]),
            ("🇧🇬 Лев (BGN)", [("CARDBGN", "Visa/Mastercard"), ("WIREBGN", "Банковский счёт")]),
            ("🇭🇺 Форинт (HUF)", [("CARDHUF", "Visa/Mastercard")]),
            ("🇷🇴 Лей (RON)", [("CARDRON", "Visa/Mastercard"), ("WIRERON", "Банковский счёт")]),
            ("🇧🇷 Реал (BRL)", [("CARDBRL", "Visa/Mastercard")]),
            ("🇦🇷 Песо (ARS)", [("CARDARS", "Visa/Mastercard"), ("WIREARS", "Банковский счёт")]),
            ("🇵🇱 Злотый (PLN)", [("WIREPLN", "Банковский счёт")]),
            ("🇦🇪 Дирхам (AED)", [("WIREAED", "Банковский счёт")]),
        ],
    },
    # Электронные кошельки (PayPal/Wise/Skrill/Revolut и т.п.), без Азии/Кавказа.
    "wallets": {
        "emoji": "💸",
        "title": "Электронные кошельки",
        "groups": [
            ("🇺🇸 Доллар (USD)", [
                ("PPUSD", "PayPal"),
                ("WISEUSD", "Wise"),
                ("SKLUSD", "Skrill"),
                ("REVBUSD", "Revolut"),
            ]),
            ("🇪🇺 Евро (EUR)", [
                ("PPEUR", "PayPal"),
                ("WISEEUR", "Wise"),
                ("SKLEUR", "Skrill"),
                ("REVBEUR", "Revolut"),
            ]),
            ("🇬🇧 Фунт (GBP)", [
                ("WISEGBP", "Wise"),
                ("REVBGBP", "Revolut"),
                ("PPGBP", "PayPal"),
            ]),
            ("🇨🇦 Канадский доллар (CAD)", [("PPCAD", "PayPal")]),
            ("🇦🇷 Песо (ARS)", [("MPARS", "Mercado Pago")]),
        ],
    },
    # Азия + Кавказ: KZT/UZS/KGS/TJS/CNY/THB/IDR/VND/INR/GEL/AMD/AZN.
    # Собраны из карты/счёта/кошелька в один пост, поэтому в других
    # категориях эти валюты не повторяются.
    "asia": {
        "emoji": "🌏",
        "title": "Азия",
        "groups": [
            ("🇰🇿 Тенге (KZT)", [
                ("CARDKZT", "Visa/Mastercard"),
                ("KSPBKZT", "Kaspi Bank"),
                ("HLKBKZT", "Halyk Bank"),
                ("JSNBKZT", "Jysan Bank"),
                ("FRTBKZT", "ForteBank"),
                ("KSNVKZKA", "Freedom Bank"),
                ("ERSNBKZT", "Евразийский банк"),
                ("KCJBKZK", "Центр Кредит"),
                ("BRBKZT", "Bereke Bank"),
            ]),
            ("🇺🇿 Сум (UZS)", [
                ("CARDUZS", "Visa/Mastercard"),
                ("UZCUZS", "Uzcard"),
                ("HUMOUZS", "Humo"),
            ]),
            ("🇰🇬 Сом (KGS)", [("CARDKGS", "Visa/Mastercard"), ("ELKGS", "Elcart")]),
            ("🇹🇯 Сомони (TJS)", [("CARDTJS", "Visa/Mastercard")]),
            ("🇨🇳 Юань (CNY)", [
                ("CARDCNY", "Visa/Mastercard"),
                ("UPCNY", "UnionPay"),
                ("ALPCNY", "Alipay"),
                ("WCTCNY", "WeChat"),
            ]),
            ("🇹🇭 Бат (THB)", [("CARDTHB", "Visa/Mastercard"), ("WIRETHB", "Банковский счёт")]),
            ("🇮🇩 Рупия (IDR)", [("CARDIDR", "Visa/Mastercard"), ("WIREIDR", "Банковский счёт")]),
            ("🇻🇳 Донг (VND)", [("CARDVND", "Visa/Mastercard"), ("WIREVND", "Банковский счёт")]),
            ("🇮🇳 Рупия (INR)", [
                ("PAYTMINR", "Paytm"),
                ("WIREINR", "Банковский счёт"),
                ("UPIINR", "UPI"),
            ]),
            ("🇬🇪 Лари (GEL)", [("CARDGEL", "Visa/Mastercard"), ("WIREGEL", "Банковский счёт")]),
            ("🇦🇲 Драм (AMD)", [("CARDAMD", "Visa/Mastercard"), ("IDRAMAMD", "Idram")]),
            ("🇦🇿 Манат (AZN)", [("M10AZN", "m10"), ("CARDAZN", "Банковский счёт")]),
        ],
    },
}

FOOTER_NOTE = "▪️ Все направления работают в штатном режиме. Время обработки транзакций — до 15 минут."


# ---------- Данные ----------


async def fetch_rates() -> dict:
    """Все активные направления через внутренний API.

    Возвращает {(from_xml, to_xml): ratio}, где ratio = resultExchange.rate.out/in
    ("сколько to за 1 from"). Для задублированных направлений берётся лучший
    для клиента курс (max ratio) — совпадает с тем, что отдаёт публичный экспорт.
    """
    from bot_app.misc import box_exchanger_client

    data = await box_exchanger_client.call(method="GET:admin/exchanger/route/get")
    rates = {}
    for route in (data or {}).get("routes", []):
        if route.get("deleted") or not route.get("active"):
            continue
        rate_node = (route.get("resultExchange") or {}).get("rate") or {}
        rate_in = rate_node.get("in")
        rate_out = rate_node.get("out")
        if not rate_in or not rate_out:
            continue
        pair = (route["from"]["currency"]["xml"], route["to"]["currency"]["xml"])
        ratio = float(rate_out) / float(rate_in)
        if pair not in rates or ratio > rates[pair]:
            rates[pair] = ratio
    return rates


def get_rate(rates: dict, from_code: str, to_code: str):
    """Курс пары для отображения или None, если направления нет/оно выключено.

    Экспорт (и посты Владислава) квотируют стороной >= 1: 44.11 UAH за 1 USDT,
    но 1.15 USDT за 1 EUR — воспроизводим то же самое."""
    ratio = rates.get((from_code, to_code))
    if ratio is None or ratio <= 0:
        return None
    return ratio if ratio >= 1 else 1.0 / ratio


# ---------- История (дельта ко вчера) ----------


def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_history(history: dict, today: date, today_rates: dict) -> None:
    # Запускается 3 раза в день (card_account/wallets/asia) — каждый запуск
    # добавляет свои пары в историю за сегодня, а не перезаписывает её целиком.
    day_rates = history.setdefault(today.isoformat(), {})
    day_rates.update(today_rates)

    cutoff = today - timedelta(days=HISTORY_DAYS_TO_KEEP)
    history = {
        day: rates
        for day, rates in history.items()
        if date.fromisoformat(day) >= cutoff
    }
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------- Сообщение ----------


def format_rate(rate: float) -> str:
    # 2 знака для крупных курсов, 4 — для курсов около 1 (USDT->USD/EUR и т.п.)
    decimals = 2 if rate >= 5 else 4
    return f"{rate:.{decimals}f}"


def format_delta(today_rate: float, yesterday_rate) -> str:
    """Возвращает суффикс вида ' ↗️ (+0.15%)' для строки курса."""
    if yesterday_rate is None or yesterday_rate == 0:
        return ""
    diff_pct = (today_rate - yesterday_rate) / yesterday_rate * 100
    if abs(diff_pct) < 0.01:
        return ""
    arrow = "↗️" if diff_pct > 0 else "↘️"
    return f" {arrow} ({diff_pct:+.2f}%)"


def build_row(rates: dict, to_code: str, label: str,
              yesterday_rates: dict, today_rates: dict):
    """Строка вида '   • Monobank: 44.21 TRC20 ↗️ (+0.15%)'."""
    parts = []
    delta_str = ""
    for from_code, net_label in NETWORKS:
        rate = get_rate(rates, from_code, to_code)
        if rate is None:
            continue
        pair_key = f"{from_code}_{to_code}"
        today_rates[pair_key] = rate
        if not parts:
            delta_str = format_delta(rate, yesterday_rates.get(pair_key))
        parts.append(f"{format_rate(rate)} {net_label}")

    if not parts:
        return None
    return f"   • {label}: " + " · ".join(parts) + delta_str


def build_messages(category_key: str, rates: dict,
                   yesterday_rates: dict, today_rates: dict, today: date) -> list:
    """Список готовых к отправке сообщений (больше 1, если не влезает в лимит)."""
    category = CATEGORIES[category_key]
    header = f"{category['emoji']} Курсы обмена ({category['title']}) на {today.strftime('%d.%m.%Y')}"

    blocks = []
    for group_title, pairs in category["groups"]:
        rows = []
        for to_code, label in pairs:
            row = build_row(rates, to_code, label, yesterday_rates, today_rates)
            if row is not None:
                rows.append(row)
        if rows:
            blocks.append([f"🔹 {group_title}"] + rows + [""])

    if not blocks:
        return []

    chunks = []
    current = [header, ""]
    for block in blocks:
        prospective_len = len("\n".join(current + block))
        if prospective_len > MAX_MESSAGE_LEN and len(current) > 2:
            chunks.append(current)
            current = [f"{header} (продолжение)", ""]
        current.extend(block)
    chunks.append(current)

    chunks[-1] = chunks[-1] + [
        FOOTER_NOTE,
        f"📲 Начать обмен: [globalpayout.club]({EXCHANGE_LINK})",
    ]
    return ["\n".join(lines) for lines in chunks]


# ---------- Постинг и планировщик ----------


async def post_category(category_key: str) -> None:
    # main bot is admin in the posting group
    from bot_app.misc import aiogram_bot_instance

    rates = await fetch_rates()

    today = datetime.now(ZoneInfo(settings.TIME_ZONE)).date()
    history = load_history()
    yesterday_rates = history.get((today - timedelta(days=1)).isoformat(), {})

    today_rates = {}
    messages = build_messages(
        category_key, rates, yesterday_rates, today_rates, today
    )
    if not messages:
        raise RuntimeError(f"rates posting: no pairs resolved for '{category_key}'")

    for msg in messages:
        await aiogram_bot_instance.send_message(
            chat_id=settings.RATES_POSTING_CHAT_ID,
            text=msg,
            parse_mode="Markdown",
        )

    save_history(history, today, today_rates)
    logger.info("rates posting: sent %s message(s) for '%s'", len(messages), category_key)


def next_run(now: datetime) -> tuple[datetime, str]:
    for run_time, category in SCHEDULE:
        run_at = now.replace(
            hour=run_time.hour, minute=run_time.minute, second=0, microsecond=0
        )
        if run_at > now:
            return run_at, category
    run_time, category = SCHEDULE[0]
    run_at = (now + timedelta(days=1)).replace(
        hour=run_time.hour, minute=run_time.minute, second=0, microsecond=0
    )
    return run_at, category


async def rates_posting_scheduler() -> None:
    """Фоновая задача: 3 поста в день по SCHEDULE в таймзоне settings.TIME_ZONE."""
    if not settings.RATES_POSTING_CHAT_ID:
        logger.info("rates posting disabled (RATES_POSTING_CHAT_ID is 0)")
        return
    tz = ZoneInfo(settings.TIME_ZONE)
    while True:
        now = datetime.now(tz)
        run_at, category = next_run(now)
        await asyncio.sleep((run_at - now).total_seconds())
        try:
            await post_category(category)
        except Exception:
            logger.exception("rates posting failed for '%s'", category)


if __name__ == "__main__":
    # dry-run: python3 -m bot_app.rates_posting [card_account|wallets|asia]
    import sys

    key = sys.argv[1] if len(sys.argv) > 1 else "card_account"

    async def _dry_run():
        rates = await fetch_rates()
        today = datetime.now(ZoneInfo(settings.TIME_ZONE)).date()
        msgs = build_messages(key, rates, {}, {}, today)
        assert msgs, f"no messages built for '{key}'"
        assert msgs[0].startswith(CATEGORIES[key]["emoji"])
        for m in msgs:
            assert len(m) <= 4096
            print(m)
            print("---")
        print(f"[DRY RUN] OK, {len(msgs)} message(s), nothing sent")

    asyncio.run(_dry_run())
