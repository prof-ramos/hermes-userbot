#!/usr/bin/env python3
"""Script para rodar o userbot em modo desenvolvimento.

Carrega variáveis do .env e inicia o userbot com logs verbosos.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    """Inicia o userbot em modo desenvolvimento."""
    print("=" * 60)
    print("Hermes Userbot — Modo Desenvolvimento")
    print("=" * 60)
    print()

    # Carrega .env
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        print("ERRO: .env não encontrado. Copie .env.example para .env e configure.")
        print("  cp .env.example .env")
        sys.exit(1)

    print(f"Carregando configurações de: {env_path}")

    # Importa e roda
    from dotenv import load_dotenv

    load_dotenv(str(env_path))

    # Força modo dry-run em dev se solicitado
    import os

    if os.getenv("DEV_DRY_RUN", "true").lower() == "true":
        os.environ.setdefault("DRY_RUN", "true")
        print("⚠️  MODO DRY-RUN ATIVO — nenhuma ação será executada")
        print("   Para desativar, set DEV_DRY_RUN=false no .env")
    else:
        print("🔴 MODO DRY-RUN DESATIVADO — ações serão executadas!")

    print()
    print("Iniciando userbot...")
    print()

    from app.main import run

    run()


if __name__ == "__main__":
    main()
