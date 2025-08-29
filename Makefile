SHELL := /bin/bash

# Defaults
TIMEOUT     ?= 60
MODEL_PATH  ?= ./ml/model/
MODEL_NAME  ?= model.pkl

# Detect uv (empty if not installed)
UV := $(shell command -v uv 2>/dev/null)

.PHONY: all clean test install run deploy down generate_dot_env venv ensure_uv

all: clean test

# ---- Tooling / env ----------------------------------------------------------
ensure_uv:
ifeq ($(UV),)
	@echo "uv not found — installing with pip..."
	python -m pip install --upgrade pip
	python -m pip install uv
	$(eval UV := $(shell command -v uv 2>/dev/null))
endif

venv: ensure_uv
ifeq ($(UV),)
	@echo "Creating .venv via stdlib venv (no uv available)"
	python -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip
else
	@echo "Creating .venv via uv"
	uv venv .venv
endif

install: generate_dot_env venv
ifeq ($(UV),)
	. .venv/bin/activate && pip install -e ".[dev]"
else
	uv pip install --python .venv/bin/python -e ".[dev]"
endif

test: install
ifeq ($(UV),)
	. .venv/bin/activate && pytest tests -vv --show-capture=all
else
	uv run --python .venv/bin/python pytest tests -vv --show-capture=all
endif

run: install
	# Adjust module path below if your ASGI app is at app.main:app
ifeq ($(UV),)
	PYTHONPATH=app/ . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
else
	PYTHONPATH=app/ uv run --python .venv/bin/python uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
endif

deploy: generate_dot_env
	docker compose build
	docker compose up -d

down:
	docker compose down

generate_dot_env:
	@if [[ ! -e .env ]]; then cp .env.example .env; fi

clean:
	@find . -name '*.pyc' -delete
	@find . -name '__pycache__' -exec rm -rf {} +
	@find . -name 'Thumbs.db' -delete
	@find . -name '*~' -delete
	rm -rf .cache build dist *.egg-info htmlcov .tox/ docs/_build .venv
