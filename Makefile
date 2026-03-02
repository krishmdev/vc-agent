# Two-phase workflow: `make setup` needs the network once; everything after `make index-offline`
# runs with no keys and no network (wrap it in a sandbox to prove it, see README).
SHELL := /bin/bash
ROOT := $(abspath .)
export PLAYWRIGHT_BROWSERS_PATH := $(ROOT)/.pw-browsers
export HF_HOME := $(ROOT)/.models
export NEXT_TELEMETRY_DISABLED := 1

VOICE := livekit-voice-agent
RESEARCH := research-agent
FRONTEND := frontend

.PHONY: setup deps models index-offline index-live build-offline demo test lint e2e-offline egress-companion record-fixtures live

setup: deps models build-offline ## install locked deps, fetch pinned models, build the offline frontend

deps:
	cd $(VOICE) && uv sync --frozen
	cd $(RESEARCH) && uv sync --frozen
	cd $(FRONTEND) && npm ci --no-audit --no-fund
	cd $(FRONTEND) && npx playwright install chromium

models: ## all-MiniLM-L6-v2 at the revision in models.lock, into .models/
	cd $(VOICE) && .venv/bin/python model_store.py fetch

index-offline: ## MiniLM knowledge-base collection (no network); stop the servers first
	cd $(VOICE) && VC_AGENT_MODE=offline HF_HUB_OFFLINE=1 KB_EMBED_THREADS=$${KB_EMBED_THREADS:-0} .venv/bin/python ingest.py --embedder local

index-live: ## OpenAI text-embedding-3-small collection (needs OPENAI_API_KEY, about $0.11)
	cd $(VOICE) && .venv/bin/python ingest.py --embedder openai

build-offline:
	cd $(FRONTEND) && NEXT_PUBLIC_VC_AGENT_MODE=offline NEXT_DIST_DIR=.next-offline npx next build

demo: ## offline stack on localhost:3000
	./scripts/run-offline.sh

test: ## python unit and integration tests (sockets disabled except localhost)
	cd $(VOICE) && .venv/bin/python -m pytest -q
	cd $(RESEARCH) && .venv/bin/python -m pytest -q

lint:
	$(RESEARCH)/.venv/bin/ruff check .
	cd $(FRONTEND) && npx eslint . && npx tsc --noEmit

e2e-offline: ## Playwright journey + egress canaries; run it inside the network sandbox
	cd $(FRONTEND) && npx playwright test

egress-companion: ## unsandboxed: the same canaries must connect, so the offline result isn't vacuous
	cd $(FRONTEND) && EXPECT_EGRESS=open npx playwright test e2e/egress.spec.ts

record-fixtures: ## live, network, costs money: re-record the deep-research fixtures
	cd $(RESEARCH) && .venv/bin/python scripts/record_research_fixtures.py

live: ## all live services (needs keys in .env.local and both KB indexes)
	zsh start.sh
