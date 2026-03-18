from pydantic import BaseModel, ConfigDict


class TelegramAuthRequest(BaseModel):
    init_data: str


class TelegramWebsiteAuthRequest(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class PublicAuthConfigResponse(BaseModel):
    enabled: bool
    bot_username: str | None = None
    mini_app_url: str | None = None

