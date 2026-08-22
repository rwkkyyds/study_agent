import pytest

from app.core.config import DEFAULT_JWT_SECRET_KEY, Settings


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(environment="production", jwt_secret_key=DEFAULT_JWT_SECRET_KEY)


def test_production_accepts_custom_jwt_secret():
    settings = Settings(environment="production", jwt_secret_key="prod-secret-at-least-for-tests")

    assert settings.jwt_secret_key == "prod-secret-at-least-for-tests"
