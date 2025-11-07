from typing import Optional

from pydantic import BaseModel


class SavedChat(BaseModel):
    record_id: int
    chat_tg_id: int
    chat_title: str
    chat_user_name: Optional[str] = None
    transaction_target: bool
