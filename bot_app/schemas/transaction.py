import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from bot_app.data_queries import Connection
from bot_app.data_queries.user import get_user_by_id
from bot_app.schemas.user import SavedUser


class NewTransaction(BaseModel):
    external_order_id: str = Field(..., description="External Application ID")
    full_name: Optional[str] = Field(None, description="Full Name")
    card_number: str = Field(..., description="Card Number")
    currency: str = Field(..., description="Currency")
    currency_xml_code: str = Field(..., description="Currency XML Code")
    amount: float = Field(..., description="Amount")
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "reference_id": "123456",
                "exchange_rate": 0.1,
                "currency_symbol": "USDT",
                "amount": 100,
                "card_number": "1234 1234 1234 1234",
                "full_name": "John Doe",
            }
        },
    }


class TransactionResponse(BaseModel):
    uuid: UUID = Field(..., description="Message UUID")
    external_order_id: str = Field(..., description="External Application ID")
    manager_id: Optional[int] = Field(None, description="TG manager ID")
    status_code: str = Field(..., description="Status Code")
    full_name: Optional[str] = Field(None, description="Full Name")
    currency_xml_code: Optional[str] = Field(None, description="Currency XML Code")
    currency: str = Field(..., description="Currency symbol")
    amount: float = Field(..., description="Amount")
    card_number: str = Field(..., description="To Account")
    created_at: datetime.datetime = Field(..., description="Created At")

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

    async def get_telegram_formatted_application(self, conn: Connection) -> str:
        if self.manager_id:
            manager: SavedUser = await get_user_by_id(conn, self.manager_id)
            manager.linked_name_and_username()

        text = (
            f"💸 Нова транзакція виплати\n"
            f"🆔 <b>Ідентифікатор транзакції:</b> <code>{self.uuid}</code>\n"
            f"🆔 <b>Номер заявки:</b> <code>{self.external_order_id}</code>\n"
            f"💰 <b>Сума:</b> <code>{self.amount}</code>\n"
            f"💱 <b>Валюта:</b> <code>{self.currency}</code>\n"
            f"💳 <b>Карта:</b> <code>{self.card_number}</code>\n"
            f"🔔 <b>Статус:</b> {self.status_codes_to_emoji(self.status_code)} {self.status_code}\n"
        )
        if self.manager_id and manager:
            text += f"👤 <b>Менеджер:</b> {manager.linked_name_and_username()}"
        return text
