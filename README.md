# Evaluating Generative-AI Systems — a hands-on workshop

A small but complete application for **evaluating generative-AI outputs**, plus a
step-by-step workshop that uses it. The central idea is a matrix:

> **prompts × models × evaluation mechanisms**

You pick a prompt, run it through one or more models with whatever parameters you like,
and score the responses with mechanisms that range from the simplest deterministic checks
to a panel of language models acting as judges — and then you measure whether those judges
can be trusted at all.

The workshop walks through that progression from the ground up. The script lives in
[`docs/`](docs/README.md).

## What's in here

| Path | What it is |
|---|---|
| [`backend/`](backend/) | The evaluation engine and its HTTP API (Python, FastAPI). |
| [`frontend/`](frontend/) | The web application that drives it (React, TypeScript, Vite). |
| [`docs/`](docs/README.md) | The workshop script: a sequence of hands-on labs. |

## Why these languages

**Backend — Python with FastAPI.** Evaluation work leans heavily on the language ecosystem
that grew up around it: talking to local and hosted models (OpenAI-compatible servers such
as Ollama, and the Anthropic SDK) is first-class in Python, and the scoring logic — running
generated code, executing SQL, computing rank agreement between judges — is concise and
dependency-light in the standard library. Just as important for a teaching tool, the code
stays readable: workshop attendees can open any scorer and understand it in a minute.

A fair question is "why not Java, to match a langchain4j *building* workshop?" Because this
workshop teaches something different — how to *evaluate* systems rather than how to build
them — and reuse of an existing Python evaluation engine made the choice decisive. The two
topics are complementary; the language follows the task.

**Frontend — React with TypeScript.** The interface is component-driven and benefits from
static types checked against the API contract. It is deliberately a *separate* application:
the backend exposes a plain HTTP/OpenAPI surface, so this frontend is replaceable. You could
throw it away and drive the same API from a notebook, a CLI, or a different framework.

## Architecture

Ports and adapters (hexagonal). The domain holds pure evaluation logic with no I/O; the
application layer orchestrates use cases through ports (interfaces); adapters wire in the
HTTP API, the model providers, the datasets and storage. Nothing in the core depends on a
web framework or an SDK, which is what keeps the evaluation logic testable and the API
replaceable.

```
┌────────────┐      HTTP / OpenAPI      ┌────────────────────────────────────┐
│  frontend  │ ───────────────────────▶ │ inbound adapter (FastAPI)           │
│ (React)    │                          │  → application (use cases, ports)   │
└────────────┘                          │     → domain (pure scoring logic)   │
                                        │  ← outbound adapters (models, data) │
                                        └────────────────────────────────────┘
```

## The evaluation mechanisms

From simplest to most involved:

1. **Deterministic** — exact match, numeric tolerance, regex, JSON-schema validation,
   running generated **code** against unit tests, executing **SQL** against a schema.
2. **Similarity** — BLEU, ROUGE-L and a fuzzy ratio against a reference.
3. **LLM as judge** — a model scores a response on a five-dimension rubric; the judge is
   itself a model you choose.
4. **Meta-evaluation** — measure how well one judge agrees with a stronger reference judge
   (Pearson / Spearman / mean absolute error, and a reliability verdict).

The same response can be graded by several mechanisms at once, which is the quickest way to
see where each one succeeds and where it misleads you.

## Quick start

**Prerequisites:** Python 3.11+, Node 18+, and — for the free local path —
[Ollama](https://ollama.com) with a model pulled (`ollama pull qwen3:4b`). Hosted models
need `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY`.

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn workshop_evals.adapters.inbound.http.app:app
```

No model or API key handy? Run it in offline demo mode, which answers with a canned client
so the whole app still works:

```bash
WORKSHOP_EVALS_FAKE_LLM=1 uvicorn workshop_evals.adapters.inbound.http.app:app
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The API docs are at <http://localhost:8000/docs>.

## Tests

```bash
# backend: unit + API integration (offline, deterministic)
cd backend && pytest
cd backend && pytest -m real_llm        # optional: exercises a live local model

# frontend: end-to-end against the demo backend, with coverage
cd frontend && npx playwright test
```

## The workshop

Start at [`docs/README.md`](docs/README.md) and work through the labs in order.
