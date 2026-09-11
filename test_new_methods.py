"""
Test script for new payout methods (5-8).
Run on the server where the bot is deployed:
  python test_new_methods.py
"""
import json
import urllib.error
import urllib.request

API_URL = "http://localhost:2000/transaction/"

TEST_CASES = [
    {
        "name": "Method 5 — CRYPTO",
        "payload": {
            "external_order_id": "test-crypto-001",
            "currency": "USDT",
            "currency_xml_code": "USDTTON",
            "amount": 50.0,
            "method_type": 5,
            "service_name": "usdt_ton",
            "wallet_address": "UQBtest1234567890abcdefghijklmnopqrstuvwxyz12",
        },
    },
    {
        "name": "Method 6 — IBAN INTL",
        "payload": {
            "external_order_id": "test-iban-intl-001",
            "currency": "EUR",
            "currency_xml_code": "WISEEUR",
            "amount": 100.0,
            "method_type": 6,
            "service_name": "wise",
            "iban": "DE89370400440532013000",
            "full_name": "Test User Name",
            "bank_name": "Deutsche Bank",
        },
    },
    {
        "name": "Method 7 — CNY AliPay",
        "payload": {
            "external_order_id": "test-alipay-001",
            "currency": "CNY",
            "currency_xml_code": "ALIPAY",
            "amount": 300.0,
            "method_type": 7,
            "service_name": "alipay",
            "photo": "test_photo_file_id_alipay_qr_123",
        },
    },
    {
        "name": "Method 8 — CNY WeChat",
        "payload": {
            "external_order_id": "test-wechat-001",
            "currency": "CNY",
            "currency_xml_code": "WECHAT",
            "amount": 200.0,
            "method_type": 8,
            "service_name": "wechat",
            "photo": "test_photo_file_id_wechat_qr_456",
        },
    },
    {
        "name": "Method 0 — CARD with bank_name (new optional fields)",
        "payload": {
            "external_order_id": "test-card-bankname-001",
            "currency": "AZN",
            "currency_xml_code": "CARDAZN",
            "amount": 85.0,
            "method_type": 0,
            "service_name": "card_azn",
            "card_number": "4111111111111111",
            "full_name": "Test Testov",
            "bank_name": "ABB Bank",
        },
    },
]


def send_request(name, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            print(f"  ✅ OK — uuid: {body.get('uuid')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ❌ HTTP {e.code}: {body[:300]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    print(f"Sending test transactions to {API_URL}\n")
    for case in TEST_CASES:
        print(f"[{case['name']}]")
        send_request(case["name"], case["payload"])
    print("\nDone. Check your Telegram test group for messages.")
