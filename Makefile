include .env

# add these helper vars at the top (optional)
COMPOSE ?= docker compose --env-file .env
JUPYTER_CID := $(shell docker compose --env-file .env ps -q jupyter)

up:
	docker compose --env-file .env up -d

down:
	docker compose --env-file .env down

reset:           ## destroys volumes (irreversible)
	docker compose --env-file .env down --volumes

logs:
	docker compose --env-file .env logs -f

ingest:
	$(COMPOSE) up -d jupyter
	docker exec -it $(JUPYTER_CID) python /home/jovyan/scripts/ingest.py

query:
	$(COMPOSE) up -d jupyter
	docker exec -it $(JUPYTER_CID) python /home/jovyan/scripts/rag_query.py "$(q)"

smoke:
	bash scripts/smoke.sh

# Utilities
# estimate: estimate chunk counts for a file or directory (path=<file|dir>)
estimate:
	$(COMPOSE) up -d jupyter
	CID=$$($(COMPOSE) ps -q jupyter); docker exec -it $$CID python /home/jovyan/scripts/estimate_chunks.py "$(path)"

# split: split a large file into parts (file=path size=5MB [out=dir] [prefix=name])
split:
	$(COMPOSE) up -d jupyter
	CID=$$($(COMPOSE) ps -q jupyter); docker exec -it $$CID python /home/jovyan/scripts/split_file.py "$(file)" "$(size)" "$(out)" "$(prefix)"

# ingest-one: ingest a single file (file=path)
ingest-one:
	$(COMPOSE) up -d jupyter
	CID=$$($(COMPOSE) ps -q jupyter); docker exec -it $$CID python /home/jovyan/scripts/ingest_one.py "$(file)"
