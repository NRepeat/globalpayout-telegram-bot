from typing import Optional

from pydantic import BaseModel, Field


class SavedUser(BaseModel):
    user_id: int
    name: str
    user_name: Optional[str] = Field(None, description="TG user name")
    senior_operator: bool
    bot_admin: bool

    def linked_name_and_username(self) -> str:
        if self.user_name is not None and len(self.user_name) > 0:
            username_without_at = self.user_name.replace("@", "")
            full_link_string = f'<a href="https://t.me/{username_without_at}">{self.name} ({self.user_name})</a>'
        else:
            full_link_string = f'<a href="tg://user?id={self.user_id}">{self.name}</a>'
        return full_link_string
