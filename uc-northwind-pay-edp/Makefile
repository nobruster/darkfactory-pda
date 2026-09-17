SHELL := /bin/sh

PYTHON ?= python3
RUNNER_VENV := legacy/runner/.venv
RUNNER_PYTHON := $(RUNNER_VENV)/bin/python
SCENARIO ?= valid-minimal
TYPE ?= 01
OUTPUT ?= gen/output
EVIDENCE ?= evidence
POLL_INTERVAL ?= 5
MAX_BATCHES ?= 100
SUPPORTED_TYPES := 01 02 03 04 05 06
E2E_TYPES := 01 02 03 04 05
WORKER_E2E_SUITE := tests/end-to-end/run_worker_suite.py

.DEFAULT_GOAL := help

.PHONY: help init deploy migrate status down gen test-contracts test-gen test-python test-postgres test-java check \
	publish publish-raw run run-type run-file worker worker-once test-type01 test-e2e test-worker-e2e test clean clean-runtime \
	ontology ontology-clean ontology-ask ontology-ask-sql ontology-mcp test-ontology

help: ## [base] List supported targets, compatibility aliases, and input variables.
	@awk 'BEGIN { \
		FS = ":.*## "; \
		print "Usage: make <target> [VARIABLE=value]"; \
		print ""; \
		print "Base — boot and run the legacy use case:"; \
	} \
	/^[a-zA-Z0-9_-]+:.*## \[base\] / { \
		sub(/^\[base\] /, "", $$2); \
		printf "  %-18s %s\n", $$1, $$2; \
	} \
	END { }' $(MAKEFILE_LIST)
	@awk 'BEGIN { \
		FS = ":.*## "; \
		print ""; \
		print "Graph — catalog over live Postgres (not the use case, not Gold):"; \
	} \
	/^[a-zA-Z0-9_-]+:.*## \[graph\] / { \
		sub(/^\[graph\] /, "", $$2); \
		printf "  %-18s %s\n", $$1, $$2; \
	} \
	END { }' $(MAKEFILE_LIST)
	@awk 'BEGIN { \
		FS = ":.*## "; \
		print ""; \
		print "Verify — prove the base:"; \
	} \
	/^[a-zA-Z0-9_-]+:.*## \[verify\] / { \
		sub(/^\[verify\] /, "", $$2); \
		printf "  %-18s %s\n", $$1, $$2; \
	} \
	END { \
		print ""; \
		print "Inputs:"; \
		print "  TYPE=01|02|03|04|05|06|all  Type selector; run/gen/test-e2e accept all."; \
		print "  SCENARIO=name       Canonical scenario (default: valid-minimal)."; \
		print "  OUTPUT=path         DataGen output root (default: gen/output)."; \
		print "  EVIDENCE=path       Worker evidence root (default: evidence)."; \
		print "  POLL_INTERVAL=secs  Worker poll interval, 0.1 through 3600 (default: 5)."; \
		print "  MAX_BATCHES=count   Worker per-cycle bound, 1 through 100 (default: 100)."; \
		print "  BATCH=id            Bundle directory name below OUTPUT for publish."; \
		print "  BUNDLE=path         Explicit bundle directory for publish."; \
		print "  FILE=path           Raw file with sibling checksum and manifest; TYPE cannot be all."; \
		print "  CONFIRM=clean-runtime  Required destructive-clean confirmation."; \
		print "  Q=text             Optional question for ontology-ask / ontology-ask-sql."; \
		print ""; \
		print "BATCH and BUNDLE are mutually exclusive."; \
		print "Graph contrast (nights 1-3): ontology-ask-sql (without), then ontology-ask (with)."; \
		print "Default Q is the Type 01 paid question. MCP catalog_ask is the same catalog."; \
		print "There is no dlt, dbt, or modern target. Type 01 Gold is agent-authored after lakehouse Consensus."; \
	}' $(MAKEFILE_LIST)

init: ## [base] Create local Python environments, .env, and container builds.
	@test -f .env || cp .env.example .env
	@chmod 0600 .env
	@$(PYTHON) -m venv $(RUNNER_VENV)
	@$(RUNNER_PYTHON) -m pip install --quiet --upgrade pip
	@$(RUNNER_PYTHON) -m pip install --quiet -e 'gen[dev]' -e ontology -r legacy/runner/requirements.txt
	@docker compose build sftp processor
	@echo "local development environment initialized"

deploy: ## [base] Recreate SFTP + Postgres, migrate PostgreSQL, and verify runtime health.
	@docker compose up -d --build --force-recreate --wait sftp postgres
	@$(RUNNER_PYTHON) legacy/runner/bootstrap_runtime.py
	@$(MAKE) --no-print-directory migrate
	@$(RUNNER_PYTHON) legacy/runner/runtime_status.py

migrate: ## [base] Apply immutable PostgreSQL migrations or verify checksums.
	@PYTHONPATH=legacy/runner $(RUNNER_PYTHON) legacy/postgres/migrate.py

status: ## [base] Show Compose state and verify every local connection.
	@docker compose ps
	@$(RUNNER_PYTHON) legacy/runner/runtime_status.py

down: ## [base] Stop services without deleting volumes or evidence.
	@docker compose down

gen: ## [base] Generate one type, or the same scenario for all five types.
	@case "$(TYPE)" in 01|02|03|04|05|06|all) ;; \
		*) echo "TYPE must be one of 01, 02, 03, 04, 05, 06, or all" >&2; exit 2 ;; \
	esac
	@if [ "$(TYPE)" = "all" ]; then \
		for type_number in $(SUPPORTED_TYPES); do \
			$(RUNNER_PYTHON) gen/src/cli.py \
				--type "$$type_number" \
				--scenario "$(SCENARIO)" \
				--output "$(OUTPUT)" \
				--contracts-root contracts/types || exit $$?; \
		done; \
	else \
		$(RUNNER_PYTHON) gen/src/cli.py \
			--type "$(TYPE)" \
			--scenario "$(SCENARIO)" \
			--output "$(OUTPUT)" \
			--contracts-root contracts/types; \
	fi

test-gen: ## [verify] Run all Python DataGen unit, contract, integration, and security tests.
	@PYTHONPATH=gen/src $(RUNNER_PYTHON) -m unittest discover \
		--start-directory gen/tests \
		--pattern 'test_*.py' \
		--verbose
	@PYTHONPATH=gen/src $(RUNNER_PYTHON) -m mypy \
		--python-version 3.12 \
		--strict \
		gen/src

test-contracts: ## [verify] Validate executable cross-type schemas and canonical contract oracles.
	@PYTHONPATH=gen/src $(RUNNER_PYTHON) -m unittest discover \
		--start-directory tests/contracts \
		--pattern 'test_*.py' \
		--verbose

test-python: ## [verify] Run Python unit/security/oracle tests and strict worker-boundary typing.
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/intake:legacy/postgres:validation/oracle \
		$(RUNNER_PYTHON) -m unittest discover \
		--start-directory tests/unit \
		--pattern 'test_*.py' \
		--verbose
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/intake:legacy/postgres:validation/oracle \
		$(RUNNER_PYTHON) -m unittest discover \
		--start-directory tests/security \
		--pattern 'test_*.py' \
		--verbose
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/intake:legacy/postgres:validation/oracle \
		$(RUNNER_PYTHON) -m unittest discover \
		--start-directory validation/oracle/tests \
		--pattern 'test_*.py' \
		--verbose
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/intake:legacy/postgres:validation/oracle \
		$(RUNNER_PYTHON) -m mypy \
		--python-version 3.12 \
		--strict \
		--no-incremental \
		legacy/runner/worker.py \
		legacy/runner/recovery_journal.py \
		legacy/runner/lifecycle.py \
		legacy/runner/workflow.py \
		legacy/intake/raw_intake.py \
		legacy/publisher/raw_publisher.py

test-postgres: ## [verify] Run rollback-only COPY, procedure, and permission tests.
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/postgres \
		$(RUNNER_PYTHON) -m unittest discover \
		--start-directory tests/postgres \
		--pattern 'test_*.py' \
		--verbose

test-java: ## [verify] Build Java 21 and run its parser/privacy regression suite.
	@docker compose build processor

check: test-contracts test-gen test-python test-java ## [verify] Run pure source/schema suites and build the Java image.
	@docker compose config --quiet
	@$(RUNNER_PYTHON) -m compileall -q gen/src legacy validation tests
	@$(RUNNER_PYTHON) -m json.tool contracts/common/source-manifest.schema.json >/dev/null
	@$(RUNNER_PYTHON) -m json.tool contracts/common/generation-receipt.schema.json >/dev/null
	@$(RUNNER_PYTHON) -m json.tool contracts/common/sanitized-manifest.schema.json >/dev/null

test-type01: ## [verify] Run the complete Type 01 proof on a deployed runtime. Does not clean.
	@PYTHONPATH=gen/src $(RUNNER_PYTHON) -m unittest discover \
		--start-directory gen/tests \
		--pattern 'test_type_01_*.py' \
		--verbose
	@PYTHONPATH=gen/src $(RUNNER_PYTHON) -m unittest discover \
		--start-directory tests/contracts \
		--pattern 'test_type01*.py' \
		--verbose
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/intake:legacy/postgres:validation/oracle \
		$(RUNNER_PYTHON) -m unittest discover \
		--start-directory tests/unit \
		--pattern 'test_type01*.py' \
		--verbose
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/intake:legacy/postgres:validation/oracle \
		$(RUNNER_PYTHON) -m unittest discover \
		--start-directory validation/oracle/tests \
		--pattern 'test_type01*.py' \
		--verbose
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/intake:legacy/postgres:validation/oracle \
		$(RUNNER_PYTHON) -m unittest discover \
		--start-directory tests/security \
		--pattern 'test_worker_security.py' \
		--verbose
	@$(MAKE) --no-print-directory test-java
	@docker compose config --quiet
	@PYTHONPATH=legacy/runner:legacy/publisher:legacy/postgres \
		$(RUNNER_PYTHON) -m unittest discover \
		--start-directory tests/postgres \
		--pattern 'test_type01*.py' \
		--verbose
	@$(RUNNER_PYTHON) tests/end-to-end/run_type01_suite.py

publish: ## [base] Publish exactly one BATCH or BUNDLE through real SFTP.
	@test -n "$(BATCH)$(BUNDLE)" || { echo "set exactly one of BATCH=<batch-id> or BUNDLE=<directory>" >&2; exit 2; }
	@test -z "$(BATCH)" || test -z "$(BUNDLE)" || { echo "BATCH and BUNDLE are mutually exclusive" >&2; exit 2; }
	@$(RUNNER_PYTHON) legacy/runner/publish_raw_cli.py \
		"$(if $(BUNDLE),$(BUNDLE),$(OUTPUT)/$(BATCH))"

publish-raw: publish ## [base] Compatibility alias for publish.

run: ## [base] Run one typed scenario, or the same scenario for all five types.
	@case "$(TYPE)" in 01|02|03|04|05|06|all) ;; \
		*) echo "TYPE must be one of 01, 02, 03, 04, 05, 06, or all" >&2; exit 2 ;; \
	esac
	@if [ "$(TYPE)" = "all" ]; then \
		for type_number in $(SUPPORTED_TYPES); do \
			$(RUNNER_PYTHON) legacy/runner/run_type.py \
				--type "$$type_number" \
				--scenario "$(SCENARIO)" || exit $$?; \
		done; \
	else \
		$(RUNNER_PYTHON) legacy/runner/run_type.py \
			--type "$(TYPE)" \
			--scenario "$(SCENARIO)"; \
	fi

run-type: run ## [base] Compatibility alias for run.

run-file: ## [base] Run one explicit typed FILE with sibling checksum and manifest.
	@case "$(TYPE)" in 01|02|03|04|05|06) ;; \
		*) echo "TYPE for run-file must be one of 01, 02, 03, 04, 05, or 06" >&2; exit 2 ;; \
	esac
	@test -n "$(FILE)" || { echo "set FILE=<raw-file-path>" >&2; exit 2; }
	@$(RUNNER_PYTHON) legacy/runner/run_type.py \
		--type "$(TYPE)" \
		--file "$(FILE)"

worker: ## [base] Run the automatic manifest-ready worker in the foreground.
	@$(RUNNER_PYTHON) legacy/runner/worker.py \
		--poll-interval "$(POLL_INTERVAL)" \
		--max-batches "$(MAX_BATCHES)" \
		--evidence-root "$(EVIDENCE)"

worker-once: ## [base] Run exactly one bounded worker polling iteration.
	@$(RUNNER_PYTHON) legacy/runner/worker.py \
		--once \
		--poll-interval "$(POLL_INTERVAL)" \
		--max-batches "$(MAX_BATCHES)" \
		--evidence-root "$(EVIDENCE)"

ontology: ## [graph] Crawl live Postgres into ontology/output (graph, not the use case).
	@$(RUNNER_PYTHON) -m pip install --quiet -e ontology
	@PYTHONPATH=ontology/src $(RUNNER_PYTHON) ontology/scripts/crawl.py

ontology-clean: ## [graph] Delete ontology/output crawl artifacts.
	@rm -rf ontology/output

ontology-ask: ## [graph] Ask the catalog graph (Q=... defaults to the Type 01 paid question).
	@test -f ontology/output/graph.json || $(MAKE) --no-print-directory ontology
	@PYTHONPATH=ontology/src $(RUNNER_PYTHON) ontology/scripts/ask.py $(if $(Q),"$(Q)",)

ontology-ask-sql: ## [graph] Same paid question against legacy/postgres SQL only (no graph).
	@PYTHONPATH=ontology/src $(RUNNER_PYTHON) ontology/scripts/ask_sql_only.py $(if $(Q),"$(Q)",)

ontology-mcp: ## [graph] Stdio MCP server over ontology/output/graph.json (read-only).
	@test -f ontology/output/graph.json || $(MAKE) --no-print-directory ontology
	@PYTHONPATH=ontology/src $(RUNNER_PYTHON) ontology/scripts/mcp_server.py

test-ontology: ## [verify] Ontology unit mapping plus live crawl smoke (skips if Postgres is down).
	@$(RUNNER_PYTHON) -m pip install --quiet -e ontology
	@PYTHONPATH=ontology/src $(RUNNER_PYTHON) -m unittest discover \
		--start-directory ontology/tests \
		--pattern 'test_*.py' \
		--verbose

test-e2e: ## [verify] Run the selected live acceptance suite; TYPE=all runs 01 through 05.
	@case "$(TYPE)" in 01|02|03|04|05|all) ;; \
		06) echo "TYPE=06 has no typed e2e suite; use make run TYPE=06" >&2; exit 2 ;; \
		*) echo "TYPE must be one of 01, 02, 03, 04, 05, or all" >&2; exit 2 ;; \
	esac
	@if [ "$(TYPE)" = "all" ]; then \
		for type_number in $(E2E_TYPES); do \
			$(RUNNER_PYTHON) \
				"tests/end-to-end/run_type$${type_number}_suite.py" \
				|| exit $$?; \
		done; \
	else \
		$(RUNNER_PYTHON) \
			"tests/end-to-end/run_type$(TYPE)_suite.py"; \
	fi

test-worker-e2e: ## [verify] Run the live automatic-worker acceptance suite on a clean runtime.
	@$(RUNNER_PYTHON) "$(WORKER_E2E_SUITE)"

test: check test-postgres ## [verify] Run source/build, rollback-only PostgreSQL, and fresh worker acceptance.
	@$(RUNNER_PYTHON) "$(WORKER_E2E_SUITE)"

clean: ## [base] Delete disposable runtime state after explicit confirmation.
	@test "$(CONFIRM)" = "clean-runtime" || { echo "rerun with CONFIRM=clean-runtime" >&2; exit 2; }
	@docker compose down --volumes --remove-orphans
	@$(RUNNER_PYTHON) legacy/runner/clean_runtime.py

clean-runtime: clean ## [base] Compatibility alias for clean.
