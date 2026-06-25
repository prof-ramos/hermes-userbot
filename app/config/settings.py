"""Configurações centralizadas do hermes-userbot.

Lê variáveis de ambiente via pydantic-settings.
Nunca hardcode secrets — use .env e placeholders seguros.

Notas sobre Pydantic Settings:
- Sub-modelos usam env_nested_delimiter='__' para ler variáveis como TELEGRAM__API_ID
- Ou usam prefixos dedicados como RATE_LIMIT_, LOG_, PLUGINS_
- Variáveis sem prefixo ficam no modelo raiz (Settings)
- Para compatibilidade com .env simples, TELEGRAM__API_ID e API_ID são ambos suportados
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class TelegramSettings(BaseSettings):
    """Credenciais e configuração do Telegram MTProto."""

    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_id: int = Field(..., description="API ID obtido em my.telegram.org")
    api_hash: str = Field(..., description="API Hash obtido em my.telegram.org")
    string_session: str | None = Field(
        default=None,
        description="String session (vazio = usa sessão em arquivo)",
    )
    phone_number: str = Field(..., description="Número da conta suporte")
    two_fa_password: str = Field(
        default="",
        description="Senha 2FA (vazio se não configurada)",
    )

    @field_validator("api_hash")
    @classmethod
    def api_hash_nao_placeholder(cls, v: str) -> str:
        """Rejeita placeholders óbvios."""
        if v.strip().upper() in {"YOUR_API_HASH", "CHANGE_ME", ""}:
            raise ValueError("TELEGRAM_API_HASH não configurado. Defina um valor válido no .env.")
        return v

    @field_validator("api_id")
    @classmethod
    def api_id_nao_placeholder(cls, v: int) -> int:
        """Rejeita IDs placeholder."""
        if v <= 0:
            raise ValueError(
                "TELEGRAM_API_ID deve ser um número positivo obtido em my.telegram.org"
            )
        return v


class SecuritySettings(BaseSettings):
    """Configurações de segurança operacional."""

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    owner_user_id: int | None = Field(
        default=None,
        description="ID do dono da conta suporte (conta de controle)",
    )
    allowed_chat_ids: list[int] = Field(
        default_factory=list,
        description="IDs de chat permitidos (vazio = todos, exceto bloqueados)",
    )
    blocked_chat_ids: list[int] = Field(
        default_factory=list,
        description="IDs de chat bloqueados",
    )


class RateLimitSettings(BaseSettings):
    """Limites de taxa conservadores."""

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    per_second: int = Field(default=1, description="Máximo de ações por segundo")
    per_minute: int = Field(default=20, description="Máximo de ações por minuto")
    per_hour: int = Field(default=300, description="Máximo de ações por hora")
    daily_max: int = Field(default=5000, description="Máximo de ações por dia")
    per_chat_minute: int = Field(default=5, description="Máximo de ações por chat por minuto")


class OperationalSettings(BaseSettings):
    """Modos operacionais."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dry_run: bool = Field(
        default=False,
        description="Se true, nenhuma ação é executada — apenas registrada",
    )
    read_only: bool = Field(
        default=False,
        description="Se true, apenas lê eventos, nunca envia mensagens",
    )


class APISettings(BaseSettings):
    """Configuração da API interna FastAPI."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    internal_api_token: str = Field(
        ...,
        description="Token de autenticação da API interna",
    )
    host: str = Field(default="127.0.0.1", description="Host da API interna")
    port: int = Field(default=8000, description="Porta da API interna")

    @field_validator("internal_api_token")
    @classmethod
    def token_nao_placeholder(cls, v: str) -> str:
        """Rejeita tokens placeholder."""
        if v.strip().upper() in {"CHANGE_ME", "YOUR_INTERNAL_API_TOKEN", ""}:
            raise ValueError(
                "API_INTERNAL_API_TOKEN não configurado. Defina um token seguro no .env."
            )
        return v


class LogSettings(BaseSettings):
    """Configuração de logging."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    level: str = Field(default="INFO", description="Nível de log (DEBUG, INFO, WARNING, ERROR)")
    file: str = Field(
        default="logs/hermes-userbot.log",
        description="Caminho do arquivo de log",
    )


class PluginSettings(BaseSettings):
    """Configuração de plugins."""

    model_config = SettingsConfigDict(
        env_prefix="PLUGINS_",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    include: list[str] = Field(
        default_factory=list,
        description="Plugins a incluir (vazio = todos). Notação de ponto: 'private_messages'",
    )
    exclude: list[str] = Field(
        default_factory=list,
        description="Plugins a excluir. Notação de ponto: 'lifecycle'",
    )


class Settings(BaseSettings):
    """Configuração global — agrega todos os sub-settings.

    Variáveis de ambiente usam os prefixos definidos em cada sub-model:
    - TELEGRAM_API_ID, TELEGRAM_API_HASH, etc.
    - SECURITY_OWNER_USER_ID, SECURITY_BLOCKED_CHAT_IDS, etc.
    - RATE_LIMIT_PER_SECOND, RATE_LIMIT_DAILY_MAX, etc.
    - API_INTERNAL_API_TOKEN, API_HOST, API_PORT
    - LOG_LEVEL, LOG_FILE
    - PLUGINS_INCLUDE, PLUGINS_EXCLUDE
    - DRY_RUN, READ_ONLY (sem prefixo)

    Para compatibilidade com .env simples, variáveis sem prefixo
    (como DRY_RUN, READ_ONLY) ficam no modelo raiz ou em OperationalSettings.
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    operational: OperationalSettings = Field(default_factory=OperationalSettings)
    api: APISettings = Field(default_factory=APISettings)
    log: LogSettings = Field(default_factory=LogSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)


# Singleton de configuração — importe deste módulo
settings = Settings()
