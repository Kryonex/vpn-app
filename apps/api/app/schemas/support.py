from pydantic import BaseModel


class SupportContactOut(BaseModel):
    telegram_admin_id: int | None
    username: str | None
    display_tag: str
    telegram_link: str | None
