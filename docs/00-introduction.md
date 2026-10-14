# Lab 00 — Introduction

## Goal

Understand why evaluations matter, meet the mental model the rest of the workshop is built
on, and take a short tour of the three views in the app.

---

## Concept

### The problem with "it looks good"

When you first wire a language model into an application, you test it the way you would
test anything new: you ask it a few questions, scan the responses, and decide it works well
enough. That process is informal and opaque. You cannot tell whether the model is improving
between versions, whether a prompt change helped or hurt, or whether the gains you see on
one input are offset by regressions you did not check.

Evaluations are the systematic replacement for that instinct. An evaluation is a function
that takes a model response and returns a score. Once you have that function, you have a
number you can track, compare, and put in a CI pipeline.

The shift in mindset is worth stating plainly: before you touch a prompt, you should know
what "better" means in quantitative terms. Anthropic puts it this way in their documentation:
"Spend time establishing success criteria first." Evaluation is not the afterthought you add
when something breaks; it is the prerequisite for any improvement loop.

### The prompts × models × mechanisms matrix

The workshop is built on a three-axis mental model:

- **Prompts (cases)**: the inputs you give to the model, along with reference answers and
  any extra context the grader needs (expected output, test code, SQL schema, rubric).
- **Models (candidates)**: the model you are evaluating, plus any parameters that shape its
  output — temperature, max tokens, reasoning effort, and so on.
- **Evaluation mechanisms**: the function that scores the response. The spectrum runs from
  "check whether the output is exactly equal to the reference string" (zero cost, fully
  deterministic) to "ask a second language model to grade the response on five dimensions"
  (more expensive, handles nuance).

Each intersection of a case, a candidate, and a mechanism produces one cell in the matrix:
a response, a score, a verdict, and usage data (tokens, cost, latency). The app makes that
matrix concrete and interactive.

### The evaluation mechanism spectrum

The ten mechanisms in this app are organised in tiers:

**Deterministic — no model calls, fully reproducible:**

| Label | Method | What it checks |
|---|---|---|
| Exact match | `exact_match` | Normalized string equality or substring; pipe-separated variants |
| Numeric tolerance | `numeric` | Extracted number within 1% of the reference value |
| Regex | `regex` | Response matches a regular expression |
| JSON schema | `json_schema` | Response is valid JSON conforming to a schema |
| Code execution | `code_exec` | Extracted code passes the provided test suite |
| SQL execution | `sql_exec` | Extracted SQL produces the same result as the reference query |

**Similarity — statistical, needs a reference, no model calls:**

| Label | Method | What it checks |
|---|---|---|
| BLEU | `bleu` | N-gram precision overlap with reference |
| ROUGE-L | `rouge_l` | Longest-common-subsequence recall with reference |
| Fuzzy match | `fuzzy` | Character-level edit-distance similarity |

**LLM as judge — a second model grades the response:**

| Label | Method | What it checks |
|---|---|---|
| LLM judge | `llm_judge` | 5-dimension rubric (correctness, completeness, robustness, clarity, efficiency); each dimension scored 0–10 and combined into a weighted [0, 1] score |

The progression from deterministic to LLM-as-judge is also a trade-off progression:
deterministic mechanisms are free, fast, and perfectly reproducible, but they require a
structured reference answer and cannot handle paraphrase or open-ended quality. LLM
judges handle all that flexibility, but they introduce cost, latency, and their own
reliability concerns — which is why this workshop ends with meta-evaluation.

---

## Tour of the three views

Open the app at `http://localhost:5173`.

The top navigation bar has three tabs: **Playground**, **Matrix**, and **Judge reliability**.

### Playground

The left panel has three cards: Prompt, Model, and Mechanisms.

- **Prompt — From dataset**: choose a category (e.g. `sentiment_classification`) and a
  specific case from the dropdown. The case prompt is shown below the selectors.
- **Prompt — Custom**: type any prompt, an optional reference answer, and an optional
  rubric (one item per line).
- **Model**: select the candidate model and adjust parameters (temperature, max tokens).
  If the model supports reasoning, a reasoning effort control appears.
- **Mechanisms**: toggle checkboxes for one or more scoring methods. The app enables only
  the mechanisms applicable to the selected case — for example, SQL execution is only
  available when the case carries a SQL schema.
- When you need LLM judge, a **Judge model** selector appears below the mechanism list.

Click **Evaluate** to run. The right panel shows the model response and one score card per
selected mechanism.

The key teaching value of the Playground is the last bullet in that description: you can
score the **same response** with several mechanisms simultaneously and watch their verdicts
diverge. A response that passes exact match may score 0.6 from the LLM judge; a response
that earns a 0.9 from the judge may completely fail a regex check. That tension is the
lesson.

### Matrix

The left panel has three cards: Cases, Candidates, and Mechanisms.

- **Cases**: select a dataset category, then tick the individual cases you want to include.
- **Candidates**: one candidate card per row. Each card has a model selector, a label
  (free text, appears as the column header), and an optional **Prompt override**. The
  prompt override replaces the case's original prompt for that candidate only — this is
  how you compare a naive prompt against a refined one on the same model.
- **Mechanisms**: same toggle interface as the Playground.

Click **Run matrix**. A progress bar fills as cells complete. Results appear as a table:
rows are cases, columns are candidates, and each cell shows the method scores as chips
coloured by verdict (green pass, red fail, amber borderline), followed by the candidate's
token usage (input and output). A **Tokens** row at the bottom totals each column, and a
**Gate** row marks each column **PASS** or **BLOCKED** against a threshold per mechanism
(Lab 07 explains it).

### Judge reliability

This view runs a two-phase experiment:

1. A candidate model generates responses for every case in the chosen dataset.
2. A "judge under test" scores all those responses using the LLM judge mechanism.
3. A "reference judge" (expected to be stronger) re-scores a random sample.
4. The app computes Pearson r, Spearman ρ, rank agreement, and mean absolute error
   between the two judges' scores per dimension.

The result is a verdict — reliable, uncertain, or unreliable — and a breakdown of error
by dimension (correctness, completeness, robustness, clarity, efficiency).

---

## What to look for

- Notice that the app is titled **Evaluation Lab** and subtitled
  "prompts · models · evaluation mechanisms". That subtitle is the three-axis model in
  practice.
- On the Playground, hover over a grayed-out mechanism. It is disabled because the
  selected case does not supply the required fields (e.g. a code test suite).
- On the Matrix, the progress bar shows cells completing in parallel. The matrix is
  computed as a cartesian product of {cases} × {candidates}.

---

## Reflection

Before moving on, think about a task you have recently used a language model for.

- What would a "correct" response look like? Could you express that as a reference string,
  a JSON schema, or a rubric?
- Which of the mechanisms above could you apply to that task today without writing any
  custom code?
- What would you need to know to say "this model improved between last week and this week"?

---

Next: [Lab 01 — Deterministic evaluation](01-deterministic-evaluation.md)
