# Lab 01 — Deterministic Evaluation

## Goal

Run a real evaluation using exact match on the `sentiment_classification` dataset,
observe the score, and understand what it means for a baseline to exist.

---

## Concept

### The value of a number

Until you run an evaluation, "this model performs well on sentiment" is an opinion. After
you run one, it is a number — 72%, 91%, or whatever the model actually earns. Numbers have
properties opinions do not: they are reproducible, comparable across time, and sharable
without ambiguity.

The first lab is about producing that number and understanding what it means.

### Exact match — simple and rigorous

Exact match is the simplest possible scoring mechanism: normalize the model's response and
the reference answer (lowercase, strip trailing punctuation), then check whether one
contains the other. If the reference is pipe-separated (e.g. `positive|POSITIVE`), any
variant triggers a pass.

It sounds trivial, but for classification tasks it is perfectly correct. A sentiment
classifier that is supposed to output "positive", "negative", or "neutral" either does or
does not do that. There is no partial credit to model. The mechanism is free, instant, and
fully deterministic: run it a thousand times on the same input and you get the same answer
every time.

The limitation is symmetrical with the strength: exact match only works when the expected
output is categorical or structured. It tells you nothing about the quality of a
summarization or the correctness of a reasoning chain. Labs 03 and 05 address those cases.

### Mechanisms are additive — verdicts can diverge

The Playground lets you select multiple mechanisms simultaneously. The same model response
is then scored by each independently. This is useful because different mechanisms capture
different dimensions of correctness:

- Exact match says: is the label right?
- An LLM judge might say: is the response well-reasoned, even if the final label is wrong?

Running both simultaneously makes the divergence visible in one shot. A response can pass
exact match (correct label, short) and still earn a poor LLM judge score (no explanation,
terse to the point of being unhelpful). Or vice versa: a thoughtful, well-written response
with the wrong label passes the judge and fails exact match. Neither view is "the truth";
together they reveal more than either alone.

---

## Steps

1. Open the app at `http://localhost:5173` and confirm the **Playground** tab is active.

2. In the **Prompt** card, confirm the **From dataset** tab is selected.

3. In the **Category** dropdown, select `sentiment_classification`.

4. In the **Case** dropdown, leave the first case selected. Read the prompt — it is a
   short product review.

5. In the **Model** card, select a candidate model. If Ollama is running, choose
   **Qwen3 4B (local)**. If you are in offline demo mode, any model works.

6. In the **Mechanisms** card, check **Exact match**. Leave all other mechanisms
   unchecked.

7. Click **Evaluate**.

8. Read the right panel:
   - The **Model response** card shows what the model returned.
   - The **Scores** card shows the Exact match result: a score (0.0 or 1.0), a pass/fail
     verdict, and a detail string showing what was matched.

9. Try a few more cases: use the **Case** dropdown to step through the dataset. Note which
   ones pass and which fail, and look at the model's response when it fails — is the label
   wrong, or is the response formatted unexpectedly?

10. Now add the **LLM judge** mechanism alongside exact match. A **Judge model** selector
    appears — pick a model (the same model you used as candidate, or a different one).

11. Click **Evaluate** again. Compare the two score cards:
    - Does the LLM judge score correlate with the exact match verdict?
    - Find a case where they disagree. What does the model's response look like there?

---

## What to look for

- A score of 0.0 on exact match almost always means the model returned extra text around
  the label — for example "The sentiment is positive." instead of just "positive". This is
  a prompt-engineering signal, not a model capability signal: the model understood the task
  but was not constrained to the output format. A one-line instruction ("Respond with
  exactly one word: positive, negative, or neutral.") typically fixes it.
- Exact match on classification is a binary grader. Every case is either right or wrong.
  When you average over the dataset in the Matrix view (next lab), the score becomes an
  accuracy percentage — a clean, interpretable metric.
- The LLM judge score is continuous. A response that gets the label wrong but explains its
  reasoning well may score 0.5 or 0.6. Notice that this continuous signal is harder to act
  on for a classification task: what does 0.6 mean, and how do you improve it?

---

## Reflection

- If the model scored below 100% on exact match, look at the failing cases. Is the failure
  a prompt format issue, a genuine model error, or an ambiguous input?
- Would you trust a 100% exact-match score on 5 cases? On 50 cases? What sample size would
  you need to feel confident the score reflects real capability?
- The LLM judge can score any open-ended response. But for a classification task, exact
  match gives you a cleaner number. What does this tell you about the relationship between
  task structure and the right choice of mechanism?

---

Previous: [Lab 00 — Introduction](00-introduction.md) |
Next: [Lab 02 — Prompt refinement](02-prompt-refinement.md)
