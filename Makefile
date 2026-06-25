.PHONY: install dev test lint check run docker-build docker-up docker-down session clean

# Instalar dependências
install:
	uv pip install -e ".[dev]"

# Rodar em modo desenvolvimento
dev:
	python scripts/run_dev.py

# Rodar testes
test:
	pytest -v --tb=short

# Rodar testes com cobertura
test-cov:
	pytest -v --cov=app --cov-report=term-missing

# Lint com ruff
lint:
	ruff check app/ scripts/ tests/
	ruff format --check app/ scripts/ tests/

# Verificação de tipos
typecheck:
	mypy app/

# Rodar linter + typecheck
check: lint typecheck

# Rodar o userbot diretamente
run:
	python -m app.main

# Gerar string session
session:
	python scripts/generate_session.py

# Docker
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f hermes-userbot

# Limpar artefatos
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov