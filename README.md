# Minimal Local RAG Stack (1)

A reproducible, minimal stack for learning, experimenting, and developing sustainable Retrieval-Augmented Generation (RAG) systems locally. Designed for rapid prototyping, collaborative learning, and easy extension to CI/CD and custom LLM training.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker & Docker Compose:** Required to run the stack locally.
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop) (includes Docker Compose)
  - Verify installation:
    ```sh
    docker --version
    docker compose version
    ```
  - **Disk space:** At least 20GB free (for models, data, and volumes)
  - **RAM:** At least 8GB available (recommend 16GB+ for smooth operation)

- **Make:** For running convenience commands (optional but recommended)
  - macOS: Pre-installed or install via `xcode-select --install`
  - Linux: `sudo apt-get install make` (Debian/Ubuntu)
  - Windows: Install [GNU Make for Windows](https://gnuwin32.sourceforge.net/packages/make.htm) or use WSL2 with Linux commands

## Project Overview
This project provides a simple, local-first RAG pipeline using Infrastructure as Code principles for reproducible, maintainable environments:
- **Ollama** for running LLMs locally
- **Weaviate** as a vector database
- **Jupyter Notebooks** for experimentation and documentation
- **OpenWebUI** (optional) for LLM chat interface

The goal is to empower anyone to learn, work, and build with RAGs on their own hardware, with minimal setup and maximal transparency. By treating local infrastructure as code, we gain better control over hardware resources, simplified maintenance, and a foundation for scaling from development to production.

## Quickstart
1. **Clone the repository:**
   ```sh
   git clone https://github.com/escape/RAG-IAC.git
   cd rag-iac
   ```
2. **Start the stack:**
   ```sh
   make smoke
   ```
   This will bring up all services, ingest a sample document, and run a test query. 

### Makefile Commands for Stack Management

Use the provided `Makefile` for common stack operations:

- `make up` — Start all services in the background
- `make down` — Stop all services
- `make reset` — Stop all services and destroy all volumes (irreversible)
- `make logs` — View live logs from all services
- `make ingest` — Run the ingestion script in Jupyter
- `make query q="your question"` — Run a query against the stack
- `make smoke` — Run the full smoke test (stack up, ingest, query)

These commands simplify stack management and troubleshooting. Use `make reset` to clear all persistent data and start fresh, or `make smoke` to validate the stack end-to-end.

3. **Experiment in Jupyter:**
   - Open Jupyter at [http://localhost:8889](http://localhost:8889)
   - Try the provided notebooks for ingestion and querying.

## Data prep and ingestion utilities

All utilities run inside the Jupyter container. Paths must be container paths (your repo is mounted at `/home/jovyan`). Examples below assume input files live under `/home/jovyan/data/...`.

Tips
- Add `QUIET=true` to batch operations to print only a compact JSON summary.
- Estimation can be very verbose on large folders; use summary-only.

### Convert JSON exports to Q/A markdown
Turn ChatGPT-like conversation JSON into many small markdown files ready for ingestion.

Examples
- Convert one JSON file to a folder of `.md` files:
   - make json-to-text input=/home/jovyan/data/raw/conversations.json out=/home/jovyan/data/raw/json2txt
- Optionally filter by filename pattern during conversion (keeps only matching titles/ids if the script supports it):
   - make json-to-text input=/home/jovyan/data/raw/conversations.json out=/home/jovyan/data/raw/json2txt pattern='*'

Output goes to the `out` directory; each message pair becomes `Title__0001.md`, etc.

### Estimate chunks before ingest
Get per-file and total chunk counts using the current splitter settings (size ~900, overlap ~150).

Examples
- Whole folder (totals only):
   - make estimate path=/home/jovyan/data/raw/json2txt QUIET=true
- Single file (full detail):
   - make estimate path=/home/jovyan/data/raw/one_big.md

### Split a large file into parts
Useful for giant files that you want to ingest in parallel or track progress on.

Examples
- Split a 200MB file into ~5MB parts:
   - make split file=/home/jovyan/data/raw/one_big.md size=5MB out=/home/jovyan/data/raw/parts prefix=big

Creates `out/prefix.part-0001.md`, etc.

### Ingest data
Two common flows are supported:

1) Split-and-ingest a single large file
- In one shot: split then ingest the parts
   - make ingest-batch-file file=/home/jovyan/data/raw/one_big.md size=5MB out=/home/jovyan/data/raw/parts prefix=big QUIET=true

2) Ingest a directory of files
- Non-recursive (default) with an explicit filename pattern:
   - make ingest-batch-dir dir=/home/jovyan/data/raw/json2txt pattern='*.md' QUIET=true
- Recursive mode:
   - make ingest-batch-dir dir=/home/jovyan/data/raw recursive=true QUIET=true

Notes
- QUIET mode returns a single final JSON summary line with totals (ingested chunks, files processed).
- The scripts wait for Ollama and Weaviate to be ready before starting.

### Query
Ask questions against your ingested corpus using retrieval + local LLM generation.

Example
- make query q='What are the key steps in the creative methodology breakdown?'

Notes
- The query path validates service readiness and will error if the question is empty.
- Uses the same embeddings/vector store as the ingestion utilities.

## Stack Components
- **Ollama:** Runs LLMs locally (e.g., phi3:mini). No cloud required.
- **Weaviate:** Stores and retrieves vector embeddings for context-aware queries.
- **Jupyter:** Interactive notebooks for code, notes, and experiments.
- **OpenWebUI:** Optional web interface for chatting with LLMs.

## Multi-Interface Architecture
The stack is designed to maintain consistency across different interfaces:

### Shared State Management
- **Weaviate Vector Store**: Central source of truth for embeddings
  - Persistent across restarts via Docker volumes
  - Accessible simultaneously from all interfaces
  - Use `make reset` to clear if needed

### Interface Coordination
1. **Programmatic (Python Scripts)**
   - Direct API access to Weaviate and Ollama
   - Best for automated pipelines and testing
   - Use for bulk operations and systematic evaluation

2. **Interactive (Jupyter)**
   - Same underlying APIs as scripts
   - Great for exploration and learning
   - Maintains persistence with main vector store
   - Perfect for LLM training experiments

3. **Chat (OpenWebUI)**
   - Uses the same Ollama instance
   - Can access the same context via Weaviate
   - Ideal for quick testing and demonstrations

### Best Practices
- Use notebooks for exploration and training
- Scripts for production and testing
- OpenWebUI for demo and quick checks
- All interfaces share the same vector store
- Document significant changes to shared state

## Usage
- **Ingest data:** Place text files in `data/raw/` and run the ingestion notebook or script.
- **Query:** Use the query notebook or script to ask questions and get context-aware answers.
- **Extend:** Add new notebooks, scripts, or data sources as needed.

## Extensibility
- **CI/CD:** Easily add GitHub Actions or other CI/CD tools for automated testing and deployment.
- **Custom LLM Training:** The notebook approach supports step-by-step experimentation with fine-tuning and evaluation.
- **Scalability:** Start minimal, scale up as needed—add more data, models, or integrations.

## Learning Goals
- Understand the RAG pipeline end-to-end.
- Learn how to run LLMs and vector DBs locally.
- Experiment and document findings in notebooks.
- Build a foundation for sustainable, privacy-preserving AI development.

## Contributing
Pull requests, issues, and suggestions are welcome! Help us make local RAGs accessible to all.

---

*This project is a starting point. Refine, extend, and share your improvements!*

## Stack Health & Reset

If you encounter issues (e.g., Weaviate stuck, stale data, or persistent errors), you can restart the stack from scratch:

1. **Stop all services:**
   ```sh
   docker compose down
   ```
2. **Remove persistent volumes (clears all data):**
   ```sh
   docker volume rm rag-iac_weaviate-data rag-iac_ollama-data
   ```
   *(You can remove only `rag-iac_weaviate-data` if you want to keep Ollama models.)*
3. **Restart the stack:**
   ```sh
   make smoke
   ```

This will ensure a clean state for all services. Useful for troubleshooting, development, or sharing a reproducible environment.

## Weaviate maintenance: targeted cleanup, backup, and restore

Weaviate stores its data in the named Docker volume `rag-iac_weaviate-data` (mounted at `/var/lib/weaviate`). Here are safe, minimal recipes to maintain that data.

Important notes
- Prefer stopping Weaviate before backup/restore to ensure consistency.
- Keep `CLUSTER_HOSTNAME` stable (already set to `node1` in `compose.yml`). If it changes, stale Raft state may require a targeted cleanup.

### Quick targeted cleanup (only Weaviate data)

This clears Weaviate’s state without touching Ollama models.

```sh
# Stop the stack (or at least Weaviate)
docker compose down

# Remove only Weaviate data (irreversible)
docker volume rm rag-iac_weaviate-data

# Start and validate
make smoke
```

### Offline backup of Weaviate data

Creates a timestamped tarball under `./backups/`. Best done with Weaviate stopped.

```sh
# Stop only Weaviate to get a consistent snapshot
docker compose stop weaviate

# Ensure backups folder exists
mkdir -p backups

# Create a compressed backup of the volume
docker run --rm \
   -v rag-iac_weaviate-data:/data:ro \
   -v "$PWD/backups:/backup" \
   alpine:3.19 sh -c "tar -C /data -czf /backup/weaviate-$(date +%Y%m%d-%H%M%S).tgz . && ls -lh /backup/weaviate-*.tgz"

# Bring Weaviate back up
docker compose start weaviate
```

Optional: backup Ollama models as well

```sh
docker run --rm \
   -v rag-iac_ollama-data:/data:ro \
   -v "$PWD/backups:/backup" \
   alpine:3.19 sh -c "tar -C /data -czf /backup/ollama-$(date +%Y%m%d-%H%M%S).tgz . && ls -lh /backup/ollama-*.tgz"
```

### Restore Weaviate from a backup

Restores a previously created tarball into the `rag-iac_weaviate-data` volume.

```sh
# Stop the stack (or at least Weaviate)
docker compose down

# Pick the backup file name (from ./backups)
BACKUP_FILE="weaviate-YYYYMMDD-HHMMSS.tgz"  # replace with your filename

# Restore into the (emptied) volume
docker run --rm \
   -v rag-iac_weaviate-data:/data \
   -v "$PWD/backups:/backup" \
   alpine:3.19 sh -c "rm -rf /data/* && tar -C /data -xzf /backup/$BACKUP_FILE && ls -la /data | head"

# Start and validate
docker compose up -d
make smoke
```

### Verify backups quickly

```sh
tar -tzf backups/weaviate-*.tgz | head
```

### Tips and FAQs
- If Weaviate reports 503 and logs show Raft join errors, prefer the targeted cleanup above instead of a full reset.
- Backups can be large; ensure sufficient disk space before creating/restoring.
- You can also script these as `make` targets (e.g., `make backup-weaviate`, `make restore-weaviate`). They’re left out by default to keep the stack minimal.
