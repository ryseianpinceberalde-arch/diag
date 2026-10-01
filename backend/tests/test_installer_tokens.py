import pytest
from fastapi import HTTPException
from jose import jwt

from config import Settings
from routers.installer import (
    INSTALL_TOKEN_ALGORITHM,
    create_install_token,
    validate_install_token,
)


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_ANON_KEY="test-anon",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-key",
        AGENT_API_KEY="test-agent-key",
    )


def test_generated_installer_token_validates(settings):
    token = create_install_token(settings)
    validate_install_token(token, settings)


def test_installer_token_no_longer_uses_exposed_agent_key(settings):
    old_style_token = jwt.encode(
        {"purpose": "pc-sentinel-agent-install"},
        settings.agent_api_key,
        algorithm=INSTALL_TOKEN_ALGORITHM,
    )
    with pytest.raises(HTTPException) as error:
        validate_install_token(old_style_token, settings)
    assert error.value.status_code == 401
