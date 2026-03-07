from app.core.config import Settings


def test_optional_int_env_values_can_be_empty() -> None:
    settings = Settings(
        _env_file=None,
        TELEGRAM_ADMIN_ID='',
        THREEXUI_DEFAULT_INBOUND_ID='',
    )

    assert settings.telegram_admin_id is None
    assert settings.threexui_default_inbound_id is None
