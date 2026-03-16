from uuid import UUID

from pydantic import BaseModel, Field


class SupportContactOut(BaseModel):
    telegram_admin_id: int | None
    username: str | None
    display_tag: str
    telegram_link: str | None


class SupportTicketCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    telegram_username: str | None = Field(default=None, max_length=64)
    subject: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=10, max_length=4000)


class SupportTicketCreateResponse(BaseModel):
    ok: bool
    ticket_id: UUID
    message: str
