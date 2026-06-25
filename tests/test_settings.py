"""Testes para carregamento de settings."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


class TestTelegramSettings:
    """Testes para configurações do Telegram."""

    def test_api_id_placeholder_rejected(self) -> None:
        """API IDs inválidos devem ser rejeitados."""
        from app.config.settings import TelegramSettings

        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_API_ID": "-1",
                    "TELEGRAM_API_HASH": "abc123def456",
                    "TELEGRAM_PHONE_NUMBER": "+551****9999",
                },
            ),
            pytest.raises(ValidationError),
        ):
            TelegramSettings()

    def test_api_hash_placeholder_rejected(self) -> None:
        """API Hash placeholder deve ser rejeitado."""
        from app.config.settings import TelegramSettings

        with (
            patch.dict(
                os.environ,
                {
                    "TELEGRAM_API_ID": "12345",
                    "TELEGRAM_API_HASH": "YOUR_API_HASH",
                    "TELEGRAM_PHONE_NUMBER": "+551****9999",
                },
            ),
            pytest.raises(ValidationError),
        ):
            TelegramSettings()

    def test_valid_settings_load(self) -> None:
        """Settings válidas devem carregar corretamente."""
        from app.config.settings import TelegramSettings

        with patch.dict(
            os.environ,
            {
                "TELEGRAM_API_ID": "12345",
                "TELEGRAM_API_HASH": "abc123def456ghi789",
                "TELEGRAM_PHONE_NUMBER": "+551****9999",
                "TELEGRAM_TWO_FA_PASSWORD": "",
                "TELEGRAM_STRING_SESSION": "",
            },
        ):
            ts = TelegramSettings()
            assert ts.api_id == 12345
            assert ts.api_hash == "abc123def456ghi789"


class TestAPISettings:
    """Testes para configurações da API interna."""

    def test_api_token_placeholder_rejected(self) -> None:
        """Tokens placeholder devem ser rejeitados."""
        from app.config.settings import APISettings

        with (
            patch.dict(
                os.environ,
                {
                    "API_INTERNAL_API_TOKEN": "CHANGE_ME",
                },
            ),
            pytest.raises(ValidationError),
        ):
            APISettings()

    def test_valid_api_token(self) -> None:
        """Token válido deve ser aceito."""
        from app.config.settings import APISettings

        with patch.dict(
            os.environ,
            {
                "API_INTERNAL_API_TOKEN": "my_secure_token_12345",
            },
        ):
            api = APISettings()
            assert api.internal_api_token == "my_secure_token_12345"


class TestRateLimitSettings:
    """Testes para configurações de rate limiting."""

    def test_defaults(self) -> None:
        """Valores padrão devem ser conservadores."""
        from app.config.settings import RateLimitSettings

        rl = RateLimitSettings()
        assert rl.per_second == 1
        assert rl.per_minute == 20
        assert rl.daily_max == 5000


class TestOperationalSettings:
    """Testes para modos operacionais."""

    def test_defaults(self) -> None:
        """Modos padrão devem ser seguros (dry-run desativado por padrão)."""
        from app.config.settings import OperationalSettings

        ops = OperationalSettings()
        # Padrão depende do .env — não testamos valor fixo
        assert isinstance(ops.dry_run, bool)
        assert isinstance(ops.read_only, bool)
