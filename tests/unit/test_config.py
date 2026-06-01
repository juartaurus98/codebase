import pytest

from app.core.config import Settings, get_settings


def test_default_app_name() -> None:
    s = Settings()
    assert s.app_name == "python-toolkit"


def test_default_api_port() -> None:
    s = Settings()
    assert s.api_port == 8000


def test_default_log_json() -> None:
    s = Settings()
    assert s.log_json is True


def test_is_production_flag() -> None:
    s = Settings(environment="production")
    assert s.is_production is True
    assert s.is_development is False


def test_is_development_flag() -> None:
    s = Settings(environment="development")
    assert s.is_development is True
    assert s.is_production is False


def test_env_override_via_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "my-service")
    s = Settings()
    assert s.app_name == "my-service"


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    get_settings.cache_clear()
