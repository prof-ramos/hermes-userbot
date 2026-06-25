"""Plugin: comandos administrativos.

Comandos especiais do owner para gerenciar o userbot.
Apenas o owner (OWNER_USER_ID) pode executar comandos.
"""

from __future__ import annotations

from pyrogram import Client, filters  # type: ignore[import-untyped]
from pyrogram.types import Message  # type: ignore[import-untyped]

from app.bootstrap import get_rate_limiter, get_session_manager
from app.config.settings import settings
from app.tools.safety import is_owner
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Filtra: apenas mensagens do owner
owner_filter = filters.create(lambda _, __, message: is_owner(message.from_user.id if message.from_user else 0))


@Client.on_message(filters.private & owner_filter & filters.command("status"))  # type: ignore[misc]
async def cmd_status(client: Client, message: Message) -> None:
    """!status — Retorna o status atual do userbot."""
    from app.bootstrap import get_audit_log

    rate_limiter = get_rate_limiter()
    audit = get_audit_log()

    status_text = (
        "🟢 **Hermes Userbot — Status**\n\n"
        f"• Modo dry-run: **{'Ativo' if settings.operational.dry_run else 'Inativo'}**\n"
        f"• Modo read-only: **{'Ativo' if settings.operational.read_only else 'Inativo'}**\n"
        f"• Rate limiter: {rate_limiter._daily_count}/{settings.rate_limit.daily_max} ações hoje\n"
        f"• Aprovações pendentes: 0\n"
        f"• Sessões: {len(get_session_manager().list_sessions())}"
    )

    await message.reply(status_text)
    audit.log_command("status", "owner_command")


@Client.on_message(filters.private & owner_filter & filters.command("health"))  # type: ignore[misc]
async def cmd_health(client: Client, message: Message) -> None:
    """!health — Healthcheck do userbot."""
    try:
        me = await client.get_me()
        health_text = (
            "💚 **Healthcheck OK**\n\n"
            f"• Conectado como: {me.first_name} (@{me.username})\n"
            f"• User ID: {me.id}\n"
            f"• API ID: {settings.telegram.api_id}"
        )
        await message.reply(health_text)
    except Exception as e:
        await message.reply(f"🔴 **Healthcheck falhou**: {e}")
        logger.error("healthcheck_failed", error=str(e))


@Client.on_message(filters.private & owner_filter & filters.command("mode"))  # type: ignore[misc]
async def cmd_mode(client: Client, message: Message) -> None:
    """!mode [dry_run|read_only|normal] — Altera modo operacional.

    Apenas o owner pode alterar. Requer restart para efeito completo.
    """
    args = message.text.split()[1:] if message.text else []
    from app.bootstrap import get_audit_log

    if not args:
        current = "dry_run" if settings.operational.dry_run else ("read_only" if settings.operational.read_only else "normal")
        await message.reply(f"Modo atual: **{current}**")
        return

    mode = args[0].lower()
    if mode == "dry_run":
        settings.operational.dry_run = True
        settings.operational.read_only = False
        await message.reply("✅ Modo **dry-run** ativado. Nenhuma ação será executada.")
    elif mode == "read_only":
        settings.operational.read_only = True
        settings.operational.dry_run = False
        await message.reply("✅ Modo **read-only** ativado. Apenas leitura.")
    elif mode == "normal":
        settings.operational.dry_run = False
        settings.operational.read_only = False
        await message.reply("✅ Modo **normal** ativado.")
    else:
        await message.reply("Modos disponíveis: `dry_run`, `read_only`, `normal`")

    get_audit_log().log_command("mode", "owner_command", {"mode": mode})


@Client.on_message(filters.private & owner_filter & filters.command("ping"))  # type: ignore[misc]
async def cmd_ping(client: Client, message: Message) -> None:
    """!ping — Responde com pong."""
    await message.reply("🏓 Pong!")


@Client.on_message(filters.private & owner_filter & filters.command("help"))  # type: ignore[misc]
async def cmd_help(client: Client, message: Message) -> None:
    """!help — Lista comandos disponíveis."""
    help_text = (
        "📖 **Comandos do Hermes Userbot**\n\n"
        "• `!status` — Status atual\n"
        "• `!health` — Healthcheck\n"
        "• `!mode [dry_run|read_only|normal]` — Altera modo\n"
        "• `!ping` — Teste de resposta\n"
        "• `!help` — Esta mensagem\n\n"
        "_Apenas o owner pode executar comandos._"
    )
    await message.reply(help_text)