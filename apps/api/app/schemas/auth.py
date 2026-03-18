from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    init_data: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class PublicAuthConfigResponse(BaseModel):
    enabled: bool = False
    bot_username: str | None = None
    mini_app_url: str | None = None

