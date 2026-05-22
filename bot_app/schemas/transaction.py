import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id
from bot_app.schemas.user import SavedUser


class NewTransaction(BaseModel):
    external_order_id: str = Field(..., min_length=1, max_length=128, description="External Application ID")
    currency: str = Field(..., min_length=1, max_length=16, description="Currency")
    currency_xml_code: str = Field(..., min_length=1, max_length=32, description="Currency XML Code")
    amount: float = Field(..., gt=0, description="Amount")

    method_type: int = Field(..., description="Payment method type ID")
    service_name: str = Field(
        ..., description="Service name (e.g., 'monobank', 'iban_uah', 'wise')"
    )

    full_name: str | None = Field(
        None, description="Full Name (для карт, IBAN UAH, e-wallets)"
    )
    card_number: str | None = Field(None, description="Card Number (для methodType 0)")
    iban: str | None = Field(None, description="IBAN (для methodType 1, 2)")
    inn: str | None = Field(None, description="INN / EDRPOU (для methodType 1)")
    recipient_name: str | None = Field(
        None, description="Recipient Name (для SEPA, methodType 2)"
    )
    payment_note: str | None = Field(
        None, description="Payment Note (для SEPA, methodType 2)"
    )
    payout_email: str | None = Field(
        None, description="E-wallet email (Wise, PayPal, methodType 3)"
    )
    revtag: str | None = Field(None, description="Revolut Tag (для methodType 4)")
    wallet_address: str | None = Field(None, description="Crypto wallet address (для methodType 5)")
    bank_name: str | None = Field(None, description="Bank name (для methodType 0, 6)")
    photo: str | None = Field(None, description="QR code photo file_id (для methodType 7, 8)")
    bank_account: str | None = Field(None, description="Bank account number (для CNY methodType 0, 7, 8)")
    country: str | None = Field(None, description="Country (CARD/USD, CARD/EUR, IBAN_INTL/USD)")
    sort_code: str | None = Field(None, description="Sort Code (GBP)")
    account_number: str | None = Field(None, description="Account Number (GBP, INR)")
    phone: str | None = Field(None, description="Phone (m10 AZN, Elcart KGS, MDL CARD)")
    idram_account: str | None = Field(None, description="Idram Account (AMD)")
    ifsc: str | None = Field(None, description="IFSC Code (INR)")
    upi_id: str | None = Field(None, description="UPI ID (INR)")
    paytm_wallet: str | None = Field(None, description="Paytm Wallet (INR)")
    pix_keys: str | None = Field(None, description="Pix Keys (BRL)")
    cpf: str | None = Field(None, description="CPF (BRL)")
    cvu_cbu: str | None = Field(None, description="CVU / CBU / SBU (ARS)")
    separate_direction: str | None = Field(None, description="Separate direction (GEL)")
    telegram: str | None = Field(None, description="Telegram username (ATM_QR BRL)")
    usdt_amount: float | None = Field(None, gt=0, description="USDT Amount")
    rates: float | None = Field(None, gt=0, description="Rates")
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "external_order_id": "order-iban-001",
                "currency": "UAH",
                "currency_xml_code": "P24UAH",
                "amount": 1500.50,
                "method_type": 1,
                "service_name": "iban_uah",
                "full_name": "Тест Тестович Тестенко",
                "card_number": None,
                "iban": "UA123456789012345678901234567",
                "inn": "1234567890",
            }
        },
    }


class TransactionResponse(BaseModel):
    uuid: UUID = Field(..., description="Message UUID")
    external_order_id: str = Field(..., description="External Application ID")
    manager_id: int | None = Field(None, description="TG manager ID")
    status_code: str = Field(..., description="Status Code")
    currency: str = Field(..., description="Currency symbol")
    currency_xml_code: str | None = Field(None, description="Currency XML Code")
    amount: float = Field(..., description="Amount")
    created_at: datetime.datetime = Field(..., description="Created At")
    full_name: str | None = Field(None, description="Full Name")
    card_number: str | None = Field(None, description="To Account")
    method_type: int | None = Field(None, description="Payment method type ID")
    service_name: str | None = Field(None, description="Service name")
    iban: str | None = Field(None, description="IBAN")
    inn: str | None = Field(None, description="INN / EDRPOU")
    recipient_name: str | None = Field(None, description="Recipient Name (for SEPA)")
    payment_note: str | None = Field(None, description="Payment Note (for SEPA)")
    payout_email: str | None = Field(None, description="E-wallet email")
    revtag: str | None = Field(None, description="Revolut Tag")
    wallet_address: str | None = Field(None, description="Crypto wallet address")
    bank_name: str | None = Field(None, description="Bank name")
    photo: str | None = Field(None, description="QR code photo file_id")
    bank_account: str | None = Field(None, description="Bank account number (CNY)")
    country: str | None = Field(None, description="Country")
    sort_code: str | None = Field(None, description="Sort Code (GBP)")
    account_number: str | None = Field(None, description="Account Number")
    phone: str | None = Field(None, description="Phone")
    idram_account: str | None = Field(None, description="Idram Account")
    ifsc: str | None = Field(None, description="IFSC Code")
    upi_id: str | None = Field(None, description="UPI ID")
    paytm_wallet: str | None = Field(None, description="Paytm Wallet")
    pix_keys: str | None = Field(None, description="Pix Keys")
    cpf: str | None = Field(None, description="CPF")
    cvu_cbu: str | None = Field(None, description="CVU / CBU / SBU")
    separate_direction: str | None = Field(None, description="Separate direction")
    telegram: str | None = Field(None, description="Telegram username")
    usdt_amount: float | None = Field(None, description="USDT Amount")
    rates: float | None = Field(None, description="Rates")
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "uuid": "123e4567-e89b-12d3-a456-426614174000",
            }
        },
    }

    def status_codes_to_emoji(self, status_code: str) -> str:
        if status_code == "created":
            return "📋"
        elif status_code == "in_progress":
            return "🕒"
        elif status_code == "completed":
            return "✅"
        elif status_code == "failed":
            return "❌"
        else:
            return "❓"

    def _row(self, emoji: str, label: str, value) -> str | None:
        if value in (None, ""):
            return None
        return f"{emoji} <b>{label}:</b> <code>{value}</code>"

    def _build_details_block(self) -> str:
        r = self._row
        m = self.method_type
        rows: list[str | None] = []

        # Method 0: CARD (multi-currency variants)
        if m == 0:
            if self.bank_account:
                rows.append(r("🏦", "Банк. счет", self.bank_account))
                rows.append(r("📧", "Email", self.payout_email))
            else:
                rows.append(r("💳", "Карта", self.card_number))
                rows.append(r("👤", "ФИО", self.full_name))
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("🏦", "Банк", self.bank_name))
            rows.append(r("🏦", "IBAN", self.iban))
            rows.append(r("🏦", "Счёт", self.account_number))
            rows.append(r("🔢", "Sort Code", self.sort_code))
            rows.append(r("🏷", "IFSC", self.ifsc))
            rows.append(r("📱", "Телефон", self.phone))
            rows.append(r("🌍", "Страна", self.country))
            rows.append(r("📄", "CPF", self.cpf))
            rows.append(r("📄", "CVU/CBU", self.cvu_cbu))
            rows.append(r("🧭", "Направление", self.separate_direction))
            rows.append(r("📝", "Призначення", self.payment_note))

        # Method 1: IBAN UAH
        elif m == 1:
            rows.append(r("🏦", "IBAN", self.iban))
            rows.append(r("👤", "ФИО", self.full_name))
            rows.append(r("📄", "ІПН", self.inn))
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("📝", "Призначення", self.payment_note))

        # Method 2: SEPA
        elif m == 2:
            rows.append(r("🇪🇺", "SEPA IBAN", self.iban))
            rows.append(r("👤", "Имя (ФОП/ТОВ)", self.recipient_name))
            rows.append(r("📝", "Назначение", self.payment_note))

        # Method 3: E-WALLET (Wise/PayPal/Skrill)
        elif m == 3:
            service = (self.service_name or "Email").capitalize()
            rows.append(r("📧", f"{service} Email", self.payout_email))
            rows.append(r("👤", "ФИО", self.full_name))
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("💳", "Карта", self.card_number))
            rows.append(r("🏦", "IBAN", self.iban))
            rows.append(r("🏦", "Счёт", self.account_number))
            rows.append(r("🔢", "Sort Code", self.sort_code))
            rows.append(r("📝", "Назначение", self.payment_note))

        # Method 4: REVTAG (Revolut)
        elif m == 4:
            rows.append(r("📱", "Revtag", self.revtag))
            rows.append(r("👤", "ФИО", self.full_name))
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("💳", "Карта", self.card_number))
            rows.append(r("🏦", "IBAN", self.iban))
            rows.append(r("🏦", "Банк", self.bank_name))
            rows.append(r("🏦", "Счёт", self.account_number))
            rows.append(r("🔢", "Sort Code", self.sort_code))
            rows.append(r("📝", "Назначение", self.payment_note))

        # Method 5: CRYPTO
        elif m == 5:
            rows.append(r("🔐", "Гаманець", self.wallet_address))

        # Method 6: IBAN International
        elif m == 6:
            rows.append(r("🌐", "IBAN (міжнар.)", self.iban))
            rows.append(r("👤", "ФИО", self.full_name))
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("🏦", "Банк", self.bank_name))
            rows.append(r("🏦", "Банк. счет", self.bank_account))
            rows.append(r("💳", "Карта", self.card_number))
            rows.append(r("🏦", "Счёт", self.account_number))
            rows.append(r("🔢", "Sort Code", self.sort_code))
            rows.append(r("🏷", "IFSC", self.ifsc))
            rows.append(r("📄", "CVU/CBU", self.cvu_cbu))
            rows.append(r("🧭", "Направление", self.separate_direction))
            rows.append(r("📝", "Призначення", self.payment_note))

        # Method 7: CNY AliPay
        elif m == 7:
            rows.append(r("🏦", "Банк. счет", self.bank_account))
            rows.append(r("📧", "Email", self.payout_email))
            rows.append(r("📝", "Призначення", self.payment_note))

        # Method 8: CNY WeChat
        elif m == 8:
            rows.append(r("🏦", "Банк. счет", self.bank_account))
            rows.append(r("📧", "Email", self.payout_email))
            rows.append(r("📝", "Призначення", self.payment_note))

        # Method 9: PHONE_WALLET (m10 AZN, Idram AMD)
        elif m == 9:
            rows.append(r("📱", "Телефон", self.phone))
            rows.append(r("🆔", "Idram Account", self.idram_account))
            rows.append(r("👤", "ФИО", self.full_name))
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("💳", "Карта", self.card_number))

        # Method 10: UPI INR
        elif m == 10:
            rows.append(r("🆔", "UPI ID", self.upi_id))
            rows.append(r("👤", "Получатель", self.recipient_name))

        # Method 11: PAYTM INR
        elif m == 11:
            rows.append(r("📱", "Paytm Wallet", self.paytm_wallet))
            rows.append(r("👤", "Получатель", self.recipient_name))

        # Method 12: PIX BRL
        elif m == 12:
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("🔑", "Pix Keys", self.pix_keys))
            rows.append(r("📄", "CPF", self.cpf))

        # Method 13: ATM QR BRL
        elif m == 13:
            rows.append(r("✈️", "Telegram", self.telegram))
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("🔑", "Pix Keys", self.pix_keys))
            rows.append(r("📄", "CPF", self.cpf))

        # Method 14: Mercado Pago ARS
        elif m == 14:
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("🏦", "Банк", self.bank_name))
            rows.append(r("📄", "CVU/CBU", self.cvu_cbu))

        # Method 15: ELCART KGS
        elif m == 15:
            rows.append(r("💳", "Карта", self.card_number))
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("📱", "Телефон", self.phone))

        # Method 16: INTERAC CAD
        elif m == 16:
            rows.append(r("👤", "Получатель", self.recipient_name))
            rows.append(r("🏦", "Банк", self.bank_name))
            rows.append(r("📝", "Призначення", self.payment_note))

        else:
            rows.append(r("💳", "Карта", self.card_number))
            rows.append(r("👤", "ФИО", self.full_name))
            if not any(rows):
                rows.append("❗️ <b>Реквизиты не распознаны (старый формат).</b>")

        # photo (QR code file_id) — render label if present, attached separately by handler
        if self.photo:
            rows.append(r("🖼", "QR-фото", self.photo))

        return "\n".join([x for x in rows if x])

    async def get_telegram_formatted_application(self, conn: Connection) -> str:
        manager = None
        if self.manager_id:
            manager: SavedUser = await get_user_by_id(conn, self.manager_id)

        details_block = self._build_details_block()

        text = (
            f"💸 <b>Нова транзакція виплати</b>\n"
            f"🆔 <b>Ідентифікатор транзакції:</b> <code>{self.uuid}</code>\n"
            f"🆔 <b>Номер заявки:</b> <code>{self.external_order_id}</code>\n"
            f"💰 <b>Сума:</b> <code>{self.amount} {self.currency}</code>\n"
        )
        if self.usdt_amount is not None:
            text += f"💰 <b>Внесена сума:</b> <code>{self.usdt_amount} USDT</code>\n"
        if self.rates is not None:
            text += f"📊 <b>Курс:</b> <code>{self.rates:.2f}</code>\n"
        text += (
            f"💱 <b>Сервіс:</b> <code>{self.service_name or 'N/A'}</code>\n"
            f"🔔 <b>Статус:</b> {self.status_codes_to_emoji(self.status_code)} {self.status_code}\n"
            f"--- <b>Реквізити</b> ---\n"
            f"{details_block}"
        )

        if self.manager_id and manager:
            text += f"\n👤 <b>Менеджер:</b> {manager.linked_name_and_username()}"

        return text
