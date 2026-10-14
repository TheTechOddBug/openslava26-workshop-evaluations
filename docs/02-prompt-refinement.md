# Lab 02 — Prompt Refinement

## Goal

Use the Matrix view to compare a naive prompt against a refined prompt on the same small
model. See the score gap close — and understand the cost implication.

---

## Concept

### The standard intuition, and why it is incomplete

When a model underperforms, the instinct is to upgrade to a larger model. Larger models
are more capable, so the score goes up, and the problem is solved. This is often true —
but it is also expensive, and it obscures a different lever that is usually cheaper: the
prompt.

Anthropic's prompt evaluation course documents the pattern clearly: a minimal prompt on
Claude Haiku (the smallest, cheapest model) achieved 85% accuracy on a customer complaint
classification task. After adding detailed category definitions and nine few-shot examples,
the same Haiku model reached 100%. No model upgrade. No infrastructure change. Just a
better-specified prompt.

The implication for production systems is significant. A well-engineered prompt on a small
model can match a naive prompt on a model several times more expensive. The investment
shifts from API spend to prompt engineering work — which is a one-time cost with
compounding returns, rather than a recurring inference charge.

### What "prompt refinement" means in practice

A naive prompt for a classification task might read: "Classify the sentiment of this
review." It relies on the model's generic training to guess the right output format, the
right label vocabulary, and how to handle ambiguous cases.

A refined prompt adds:
- A precise list of allowed output labels and their definitions.
- A few worked examples (few-shot) covering the main patterns and edge cases.
- An explicit output format constraint ("Respond with exactly one word.").
- Optionally, guidance for ambiguous cases ("If the sentiment is mixed, return neutral.").

Each addition removes a source of inconsistency. The model has less to infer and more to
follow. That directly translates to higher exact-match accuracy on the evaluation set.

### The Matrix view as the comparison tool

Running a single candidate in the Playground tells you what one model scored on one case.
The Matrix view runs everything at once: you specify multiple candidates (each with its own
model and optional prompt override), select the cases to include, and the app fills the
table in parallel.

The comparison this lab calls for is two candidates with the **same model** but different
prompts: one with no override (the case's original prompt), one with a refined override.
Because the model is held constant, any score difference is attributable to the prompt.

---

## Steps

1. Click the **Matrix** tab in the navigation bar.

2. In the **Cases** card, select `sentiment_classification` from the **Category** dropdown.
   The first three cases will be pre-selected. Add a few more by clicking their checkboxes —
   aim for 5–8 cases for a meaningful comparison.

3. In the **Candidates** card, you will see one candidate row already present.

4. Set the **Model** for candidate 1 to a small local model — **Qwen3 4B (local)** or
   **Llama 3.2 3B (local)**. In the **Label** field, type `naive`.

5. Leave the **Prompt override** field empty for candidate 1. This means the candidate
   will use each case's original prompt as-is.

6. Click **Add candidate**.

7. In the new candidate row, set the **Model** to the **same model** as candidate 1.
   In the **Label** field, type `refined`.

8. In the **Prompt override** field, paste this refined prompt:

   ```
   You are a sentiment classifier. Read the following customer review and classify
   its overall sentiment using exactly one of these three labels:

   - positive: the review expresses satisfaction, praise, or approval
   - negative: the review expresses dissatisfaction, complaint, or criticism
   - neutral: the review is balanced, factual, or expresses neither clear approval nor disapproval

   Respond with exactly one word — the label — and nothing else.

   Review:
   {prompt}
   ```

   Leave `{prompt}` exactly as written. When the run starts, the app replaces it with
   each case's own `prompt` field, so this one template runs across every case you
   selected. An override without `{prompt}` is sent to the model exactly as written, the
   same text for every case.

9. In the **Mechanisms** card, check **Exact match**.

10. Click **Run matrix**.

11. Watch the progress bar fill as cells complete. When done, read the results table.
    Rows are the cases you selected; columns are `naive` and `refined`. Under the score
    chips, each cell shows the candidate's token usage (`86 in · 49 out`), and the
    **Tokens** row at the bottom totals each column.

---

## What to look for

- Count the passes (green chips) for each column. If the refined prompt is better
  specified, the `refined` column should have more green chips.
- Look at the cases where `naive` fails and `refined` passes. Read the model's response
  for `naive` — does it contain the right label but wrapped in extra text? Does it use the
  wrong format? The prompt override is fixing exactly that ambiguity.
- If `refined` does not improve on `naive`, the original case prompts may already be
  well-constrained. Try a different category or write a deliberately underspecified
  override to force a gap.

### The cost angle

Every Matrix cell shows the candidate's tokens split into **in** (the prompt) and **out**
(the response), and the **Tokens** row totals them per column. Hover a cell to see its
latency. The totals count the candidate's calls only; judge calls are not included.

A refined prompt is typically longer than a naive one, so the `refined` column has more
**input** tokens. Look at the **output** tokens as well: a prompt that asks for exactly one
word often cuts the response from a full sentence to a single token, and the column can end
up cheaper overall. In one run on Llama 3.2 3B over eight cases, `naive` used 680 in · 423
out and `refined` 1,360 in · 16 out. And if the refined prompt achieves the same score on a
smaller model that would otherwise require a model three times the size to reach that
score with a naive prompt, the overall cost is lower still. The math favours prompt
engineering.

---

## Reflection

- At what point does a refined prompt become overfit to the evaluation set? How would you
  test for that?
- Suppose you refined the prompt and the score went from 72% to 88% but not higher. What
  would your next move be — more few-shot examples, a different model, a different
  mechanism, or a review of the failing cases?
- If you were building a classification feature for production, how would you use this
  matrix experiment to decide which model to deploy?

---

Previous: [Lab 01 — Deterministic evaluation](01-deterministic-evaluation.md) |
Next: [Lab 03 — Similarity metrics](03-similarity-metrics.md)
