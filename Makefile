# Energy 4.0 Harness — root commands (owner: Dev 3)
# Every target calls scripts/dev.py, so `python scripts/dev.py <target>` works where make is not installed.
# Targets whose implementation does not exist yet FAIL with an explanation.
# They never report false success.

SHELL := /bin/bash
VENV  := .venv
PY    := $(or $(wildcard $(VENV)/bin/python),$(wildcard $(VENV)/Scripts/python.exe),$(shell command -v python3 || command -v python))

.PHONY: help setup check test eval run demo-smoke verify docs

help:
	@echo "make setup       tools check, .venv, dev dependencies"
	@echo "make check       structure, schemas, doc links, secret scan"
	@echo "make test        unit + golden tests (pytest)"
	@echo "make eval        EnergyBench-Lite (evals/run.py)"
	@echo "make run         start the chat page and server"
	@echo "make demo-smoke  end-to-end smoke test"
	@echo "make verify      check + test + demo-smoke"
	@echo "make docs        rebuild the docs/ portal"

setup:
	@$(PY) scripts/dev.py setup

check:
	@$(PY) scripts/dev.py check

test:
	@$(PY) scripts/dev.py test

eval:
	@if [ -f evals/run.py ]; then $(PY) evals/run.py; \
	else \
	  echo "NOT IN THE POC: evals/run.py comes after the POC (EVALS.md §4)."; \
	  echo "  In the POC, golden cases run in make test."; \
	  exit 1; \
	fi

run:
	@$(PY) scripts/dev.py run

demo-smoke:
	@bash scripts/demo-smoke.sh

verify:
	@$(PY) scripts/dev.py verify

docs:
	@$(PY) scripts/dev.py docs
