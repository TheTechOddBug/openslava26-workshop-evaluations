# Workshop Evals — Backend

A small, API-first service for running a matrix of **prompts × models × evaluation
mechanisms**. It powers the hands-on workshop on evaluating generative-AI systems and is
built so the frontend (or any client) can drive it over plain HTTP.

## Why Python

The backend is written in Python with FastAPI for three reasons:

1. **Evaluation ecosystem.** The libraries for talking to local and hosted models
   (OpenAI-compatible servers such as Ollama, plus the Anthropic SDK) are first-class in
   Python, and the scoring logic — code execution, SQL execution, statistical agreement —
   is concise and dependency-light in the standard library.
2. **Readability as a teaching tool.** Workshop attendees read this code. Python keeps the
   evaluation mechanisms legible without ceremony.
3. **Clean separation.** FastAPI exposes an OpenAPI contract, so the frontend is a
   replaceable client rather than a coupled component.

## Architecture

Ports and adapters (hexagonal). The domain holds pure scoring logic with no I/O; the
application layer orchestrates use cases through ports; adapters wire in HTTP, model
providers, datasets and storage.

```
src/workshop_evals/
  domain/        pure evaluation logic (scoring, statistics, model types)
  application/   use cases + ports (interfaces)
  adapters/      inbound HTTP (FastAPI) + outbound providers/repositories
  config/        settings
```

## Requirements

- Python 3.11+
- For the free path: [Ollama](https://ollama.com) running locally
- Optional: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` for hosted models

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn workshop_evals.adapters.inbound.http.app:app --reload
```

The interactive API docs are then served at `http://localhost:8000/docs`. Add `--port <n>` to
use another port (or set `WORKSHOP_EVALS_PORT` for the `workshop-evals` launcher), and point the
frontend at it with `BACKEND_PORT=<n>`.

## Test

```bash
pytest                 # unit + integration (no network, no model calls)
pytest -m real_llm     # opt-in: exercises a live local model via Ollama
```

## Configuration

Copy `.env.example` to `.env` and fill in any hosted-provider keys. Edit
`data/models.yaml` to declare the models available in the catalogue.
