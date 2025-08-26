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
