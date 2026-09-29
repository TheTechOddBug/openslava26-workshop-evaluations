# GenAI Evaluations Workshop — Guide

A hands-on workshop introducing systematic evaluation of generative-AI systems.
By the end you will have moved a real model from a vague "it kind of works" feeling to a
scored, reproducible baseline — and you will have seen how a well-engineered prompt on a
small, cheap model can match a larger model running on a naive prompt.

---

## What you will learn

- Why "does it look good?" is not an evaluation strategy, and what to do instead.
- How to score model outputs automatically: from exact string matching to SQL execution to
  an LLM acting as a grader.
- How to compare models and prompt variants side-by-side in a structured matrix.
- When overlap-based metrics (BLEU, ROUGE-L) are useful and when they mislead.
- How to check whether a judge model can actually be trusted for a given task.

---

## Prerequisites

- Python 3.11 or later
- Node.js 18 or later / npm
- Either:
  - [Ollama](https://ollama.com) installed and running (free, local path), **or**
  - API keys for OpenAI or Anthropic (cloud path), **or**
  - Nothing at all — offline demo mode is available for click-through exploration

---

## Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Pull two local models if you are using Ollama (recommended free path) — one to answer
prompts and one non-reasoning model to act as a judge:

```bash
ollama pull qwen3:4b      # a candidate model
ollama pull llama3.2:3b   # a non-reasoning model — a reliable local judge
```

> Tip: prefer a non-reasoning model as the judge. Reasoning models such as Qwen3 tend to
> spend their whole token budget "thinking" and never emit the rubric JSON, which shows up
> as an empty judge score. The app defaults the judge to a non-reasoning model for this
> reason.

Start the server:

```bash
uvicorn workshop_evals.adapters.inbound.http.app:app --reload
# API docs at http://localhost:8000/docs
```

For **offline demo mode** (no model calls — returns canned responses):

```bash
WORKSHOP_EVALS_FAKE_LLM=1 uvicorn workshop_evals.adapters.inbound.http.app:app --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### 3. Cloud keys (optional)

Copy `backend/.env.example` to `backend/.env` and add the keys for the providers you use:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...        # Google Gemini via its OpenAI-compatible endpoint
```

Any OpenAI-compatible provider (OpenAI, Google Gemini, Mistral, Groq, Azure OpenAI, …) works
with the `openai_compat` model type — set the model's `base_url` and the key variable named in
its `api_key_env`. Anthropic uses its own provider. The app surfaces configured models in the
candidate and judge dropdowns automatically.

### 4. Managing models from the app

The **Models** tab configures the catalogue without editing files:

- **Discover local models** — point it at an OpenAI-compatible server (Ollama's
  `http://localhost:11434/v1` by default) and it lists what the server actually serves via
  the plain `/models` endpoint — no AI involved. Add any of them with one click.
- **Add or edit by hand** — register a local or remote model, or override a shipped entry.
- **Session credentials** — set an API key for **any provider** (OpenAI, Anthropic, Google
  Gemini, …) for the running session only (kept in memory, never written to disk). The tab
  lists the key variables your configured models need and whether each is set. Use the
  environment (step 3) for a permanent one.

Anything already described in `backend/data/models.yaml` works with no further action; the
tab only covers what the files do not. Changes made here are written to a separate
`models.runtime.yaml` overlay that overrides the shipped base by id — the base file is never
touched, and the overlay is gitignored. Base models cannot be deleted (disable them
instead); models you add can.

### 5. Editing the dataset from the app

Evaluations run against a dataset of **cases** — the inputs, in `backend/data/datasets/`
(one JSONL file per category). Each case carries the fields that decide which mechanisms
apply: `prompt`, `reference` (exact match / similarity), `rubric` (judge), `tests` (code
execution), `sql_schema` (SQL execution). The **Datasets** tab browses them by category and
lets you **add, edit, enable/disable and remove** cases; the form previews which mechanisms
the fields you fill in will unlock.

As with models, the shipped JSONL base is read-only (source `file`); your changes go to a
gitignored `datasets.runtime.json` overlay (source `user`) and are picked up immediately by
the other tabs' selectors. Base cases can be disabled but not deleted; cases you add can.

---

## The views

| Tab | What it does |
|---|---|
| **Playground** | Single prompt, single model, multiple scoring mechanisms side by side |
| **Matrix** | Multiple cases × multiple candidates (model + optional prompt override) |
| **Compare** | Pairwise A/B judging with a position-swap check for judge bias |
| **Ensemble** | Score one answer with several judges; see their average and disagreement |
| **Judge reliability** | Meta-evaluation: how well does a judge agree with a stronger reference judge? |
| **Datasets** | Browse, add, edit and enable/disable the evaluation cases every run uses |
| **Models** | Discover, add, enable/disable and configure models — local or remote — without leaving the app |

---

## Labs

| # | Lab | Core concept | View |
|---|---|---|---|
| 00 | [Introduction](00-introduction.md) | Why evals, the prompts × models × mechanisms mental model | all |
| 01 | [Deterministic evaluation](01-deterministic-evaluation.md) | Exact match as a baseline; making quality visible | Playground |
| 02 | [Prompt refinement](02-prompt-refinement.md) | A refined prompt on a small model closes the quality gap | Matrix |
| 03 | [Similarity metrics](03-similarity-metrics.md) | BLEU/ROUGE-L and where overlap metrics fail | Playground |
| 04 | [Execution-based evaluation](04-execution-based-evaluation.md) | Code execution and SQL execution as deterministic graders | Playground |
| 05 | [LLM as judge](05-llm-as-judge.md) | 5-dimension rubric, reference-guided vs reference-free | Playground |
| 06 | [Judge reliability](06-judge-reliability.md) | Self-preference bias; measuring inter-judge agreement | Judge reliability |
| 07 | [The full matrix](07-the-full-matrix.md) | Sweeping models × mechanisms; offline demo; eval in CI | Matrix |

Work through the labs in order for the first run. Each lab links to the next at the bottom.
