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

# query: run a RAG query (use: make query q='Your question')
query:
	$(COMPOSE) up -d jupyter
	CID=$$($(COMPOSE) ps -q jupyter); \
		docker exec -e Q="$(q)" -it $$CID python /home/jovyan/scripts/rag_query.py

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

# ingest-batch-file: split a large file and ingest parts (file=path size=5MB [out=dir] [prefix=name])
ingest-batch-file:
	$(COMPOSE) up -d jupyter
	CID=$$($(COMPOSE) ps -q jupyter); docker exec -it $$CID python /home/jovyan/scripts/ingest_batch.py --file "$(file)" --size "$(size)" --out "$(out)" --prefix "$(prefix)" $(if $(filter true,$(QUIET)),--summary-only,)

# ingest-batch-dir: ingest all files matching a pattern (dir=path [pattern=*.txt] [recursive=true|false])
ingest-batch-dir:
	$(COMPOSE) up -d jupyter
	CID=$$($(COMPOSE) ps -q jupyter); docker exec -it $$CID python /home/jovyan/scripts/ingest_batch.py --dir "$(dir)" --pattern "$(pattern)" $(if $(filter false,$(recursive)),--no-recursive,) $(if $(filter true,$(QUIET)),--summary-only,)

# json-to-text: convert ChatGPT-like JSON exports to Q/A markdown files
# input should be reachable inside the container (e.g., /home/jovyan/data/..)
json-to-text:
	$(COMPOSE) up -d jupyter
	CID=$$($(COMPOSE) ps -q jupyter); docker exec -it $$CID python /home/jovyan/scripts/json_to_text.py --input "$(input)" --out-dir "$(out)" --pattern "$(pattern)"
