import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id
from bot_app.schemas.user import SavedUser


class NewTransaction(BaseModel):
    external_order_id: str = Field(..., description="External Application ID")
    currency: str = Field(..., description="Currency")
    currency_xml_code: str = Field(..., description="Currency XML Code")
    amount: float = Field(..., description="Amount")

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
    usdt_amount: float | None = Field(None, description="USDT Amount")
    rates: float | None = Field(None, description="Rates")
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

    def _build_details_block(self) -> str:
        details = []

        # Method 0: Карта
        if self.method_type == 0:
            details.append(f"💳 <b>Карта:</b> <code>{self.card_number}</code>")
            details.append(f"👤 <b>ФИО:</b> <code>{self.full_name}</code>")

        # Method 1: IBAN UAH
        elif self.method_type == 1:
            details.append(f"🏦 <b>IBAN:</b> <code>{self.iban}</code>")
            details.append(f"👤 <b>ФИО:</b> <code>{self.full_name}</code>")
            details.append(f"📄 <b>ІПН:</b> <code>{self.inn}</code>")

        # Method 2: SEPA
        elif self.method_type == 2:
            details.append(f"🇪🇺 <b>SEPA IBAN:</b> <code>{self.iban}</code>")
            details.append(
                f"👤 <b>Имя (ФОП/ТОВ):</b> <code>{self.recipient_name}</code>"
            )
            details.append(f"📝 <b>Назначение:</b> <code>{self.payment_note}</code>")

        # Method 3: Email-кошелек
        elif self.method_type == 3:
            service = (self.service_name or "Email").capitalize()
            details.append(
                f"📧 <b>{service} Email:</b> <code>{self.payout_email}</code>"
            )
            details.append(f"👤 <b>ФИО:</b> <code>{self.full_name}</code>")

        # Method 4: Revtag
        elif self.method_type == 4:
            details.append(f"📱 <b>Revtag:</b> <code>{self.revtag}</code>")
            details.append(f"👤 <b>ФИО:</b> <code>{self.full_name}</code>")

        else:
            # Обработка старых заявок, где method_type = None
            if self.card_number:
                details.append(f"💳 <b>Карта:</b> <code>{self.card_number}</code>")
            if self.full_name:
                details.append(f"👤 <b>ФИО:</b> <code>{self.full_name}</code>")
            if not details:
                details.append("❗️ <b>Реквизиты не распознаны (старый формат).</b>")

        return "\n".join(details)

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
