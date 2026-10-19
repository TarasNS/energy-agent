# Energy 4.0 Harness — root commands (owner: Dev 3)
# Targets whose implementation does not exist yet FAIL with an explanation.
# They never report false success.

SHELL := /bin/bash
VENV  := .venv
PY    := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)

.PHONY: help setup check test eval run demo-smoke verify docs

help:
	@echo "make setup       tools check, .venv, dev dependencies"
	@echo "make check       structure, schemas, doc links, secret scan"
	@echo "make test        unit + golden tests (pytest)"
	@echo "make eval        EnergyBench-Lite (evals/run.py)"
	@echo "make run         start the demo UI"
	@echo "make demo-smoke  end-to-end smoke test"
	@echo "make verify      check + test + demo-smoke"
	@echo "make docs        rebuild the docs/ portal"

setup:
	@bash scripts/setup.sh

check:
	@$(PY) scripts/verify.py

test:
	@$(PY) -m pytest; rc=$$?; \
	if [ $$rc -eq 5 ]; then \
	  echo ""; \
	  echo "NOT IMPLEMENTED: no tests collected."; \
	  echo "  Needed: tests under mcp/*/tests/, harness/, evals/ or tests/ (owner: Dev 4, plus each component owner)."; \
	  exit 1; \
	elif [ $$rc -eq 127 ] || ! $(PY) -c 'import pytest' 2>/dev/null; then \
	  echo "pytest not available. Run: make setup"; exit 1; \
	else exit $$rc; fi

eval:
	@if [ -f evals/run.py ]; then $(PY) evals/run.py; \
	else \
	  echo "NOT IN THE POC: evals/run.py comes after the POC (EVALS.md §4)."; \
	  echo "  In the POC, golden cases run in make test."; \
	  exit 1; \
	fi

run:
	@if [ -f apps/web/run.sh ]; then bash apps/web/run.sh; \
	else \
	  echo "NOT IMPLEMENTED: apps/web/run.sh does not exist."; \
	  echo "  Needed: one start command for the demo UI (owner: Dev 5; wiring: Dev 3)."; \
	  exit 1; \
	fi

demo-smoke:
	@bash scripts/demo-smoke.sh

verify:
	@bash scripts/verify.sh

docs:
	@$(PY) scripts/build_docs.py
