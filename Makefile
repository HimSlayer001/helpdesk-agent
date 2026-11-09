PY ?= python3
BIN := .venv/bin
export PYTHONPATH := src

.PHONY: setup models test chat serve eval readme all docker clean

setup:            ## virtualenv + dependencies
	$(PY) -m venv .venv
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -r requirements.txt

models:           ## pull the local models (needs Ollama installed and running)
	ollama pull llama3.2:3b
	ollama pull nomic-embed-text

test:             ## offline tests, no Ollama needed
	$(BIN)/python -m pytest -q

chat:             ## chat in the terminal
	$(BIN)/python -m helpdesk.cli

serve:            ## HTTP API on :8000
	$(BIN)/uvicorn helpdesk.api:app --app-dir src --port 8000

eval:             ## benchmark retrieval + agent -> results/
	$(BIN)/python -m helpdesk.evaluate

readme:           ## write measured results into README.md
	$(BIN)/python -m helpdesk.make_readme

all: setup models test eval readme

docker:
	docker build -t helpdesk-agent .

clean:
	rm -rf .venv results/*.json results/*.md tickets.db .pytest_cache
