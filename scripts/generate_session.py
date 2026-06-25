#!/usr/bin/env python3
"""Script para gerar string session do Telegram.

Executa interativamente, solicitando API ID, API Hash e número de telefone.
Gera uma string session que pode ser usada no .env como STRING_SESSION.

NUNCA commit a string session no Git.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    """Gera uma string session interativamente."""
    print("=" * 60)
    print("Hermes Userbot — Gerador de String Session")
    print("=" * 60)
    print()
    print("Este script vai gerar uma string session para autenticação")
    print("do Telegram MTProto. A string session deve ser armazenada")
    print("com segurança e NUNCA commitada no Git.")
    print()

    # Solicita credenciais
    api_id = input("API ID: ").strip()
    api_hash = input("API Hash: ").strip()
    phone_number = input("Número de telefone (com código do país, ex: +5511999999999): ").strip()

    if not api_id or not api_hash or not phone_number:
        print("ERRO: Todos os campos são obrigatórios.")
        sys.exit(1)

    try:
        api_id_int = int(api_id)
    except ValueError:
        print("ERRO: API ID deve ser um número.")
        sys.exit(1)

    print()
    print("Conectando ao Telegram...")
    print("Você receberá um código de verificação no Telegram.")
    print()

    from pyrogram import Client  # type: ignore[import-untyped]

    # Cria cliente com sessão em arquivo temporário
    session_path = str(Path(__file__).resolve().parent.parent / "sessions" / "generate_session")
    client = Client(
        name=session_path,
        api_id=api_id_int,
        api_hash=api_hash,
        phone_number=phone_number,
    )

    try:
        client.start()
        string_session = client.export_session_string()

        me = client.get_me()
        print()
        print("=" * 60)
        print("SUCESSO! String session gerada:")
        print("=" * 60)
        print()
        print(f"String Session:\n{string_session}")
        print()
        print(f"Logado como: {me.first_name} (@{me.username}) [ID: {me.id}]")
        print()
        print("Adicione ao seu .env:")
        print(f"STRING_SESSION={string_session}")
        print()
        print("IMPORTANTE: Nunca compartilhe ou commite esta string!")

    except Exception as e:
        print(f"\nERRO: {e}")
        print("Verifique suas credenciais e tente novamente.")
        sys.exit(1)

    finally:
        try:
            client.stop()
        except Exception:
            pass

        # Remove a sessão temporária
        import os
        for ext in ["", "-journal"]:
            path = f"{session_path}.session{ext}"
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()