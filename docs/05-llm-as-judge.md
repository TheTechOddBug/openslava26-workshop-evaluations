# Lab 05 — LLM as Judge

## Goal

Score open-ended model responses using the LLM judge mechanism. Understand the five
rubric dimensions, when to use a reference answer, and how the choice of judge model
affects the scores.

---

## Concept

### Why you need a judge for open-ended tasks

Classification and code generation have verifiable correct answers. Summarization, writing,
reasoning explanation, and instruction following do not — or rather, they have a space of
acceptable answers, not a single one. A well-written summary is better than a poorly-written
one even if neither matches the reference word for word.

The only scalable way to grade open-ended quality is to use another model as the grader.
This approach — LLM as judge — outsources the evaluation of flexible criteria to a model
that can interpret rubric dimensions, compare responses, and produce a score without
requiring a fixed reference string.

The key limitation is that the judge is itself a language model, subject to all the
instabilities of language models: it can be inconsistent, influenced by irrelevant
features of the response, or simply wrong. That is why the next lab addresses judge
reliability. For now, the goal is to understand what the judge measures.

### The five dimensions

The LLM judge in this app scores responses on five dimensions, each on a 0–10 scale:

| Dimension | What it measures |
|---|---|
| Correctness | Factual or functional accuracy — is the answer actually right? |
| Completeness | Coverage — does the answer address all parts of the question? |
| Robustness | Handling of edge cases, ambiguity, and unusual inputs |
| Clarity | Readability and structure — is the response easy to follow? |
| Efficiency | Conciseness and approach quality — is the solution economical? |

The five scores are combined into a single weighted average in the range [0, 1]. The
weights vary by category: for code generation, correctness and robustness carry more
weight; for refactoring, clarity counts more; for reasoning tasks, completeness is
weighted higher. The final number is a single score you can track over time and compare
across runs.

### Reference-guided vs reference-free

The judge prompt accepts an optional reference answer. When one is present, the judge is
asked to compare the model's response against it explicitly. This is called reference-
guided evaluation. It produces more consistent scores for tasks where there is a clear
ideal answer, because the judge has an anchor.

When no reference is provided, the judge uses its own expert knowledge to evaluate the
response. This is reference-free evaluation. It is more flexible and suitable for tasks
where the correct answer is not known in advance — but it is also more variable, because
the judge's knowledge and priors now determine the standard.

For the categories in this dataset, most cases include a reference answer. The dataset
schema stores it in the `reference` field, and the app passes it to the judge automatically.

### "Give the judge an out"

One practical recommendation from Anthropic's documentation on agent evaluation is to
allow the judge to return "Unknown" when it cannot determine a reliable score. This
matters because a judge that is forced to produce a number will produce one — even if the
evidence is insufficient. Allowing the model to abstain on uncertain cases makes the
scores it does produce more trustworthy.

The judge in this app is prompted to return a numeric score for each dimension, but the
detail string it produces captures its justification. Low-confidence responses tend to
produce hedged justifications that you can spot-check.

### Choosing a judge model

The general recommendation is to use a **different model** as the judge than the one you
used as the candidate. If the same model grades its own outputs, it may be biased toward
its own style and phrasing — it knows how it would have answered the question and may
reward responses that resemble that approach. The app enforces a soft distinction through
the role system: models can be configured as `candidate`, `judge`, or `both`. When a
model's role is `judge`, it appears in the judge selector but not the candidate selector.

As a practical rule: use the strongest available judge you can afford. A weak judge
produces inconsistent scores. A strong judge — typically a large frontier model — is more
calibrated, more consistent across runs, and less susceptible to surface-level features
of the response.

One caveat that bites in practice: **avoid reasoning models as judges** unless you give
them a large token budget. A reasoning model (Qwen3, for example) spends tokens on an
internal chain of thought before answering. Asked to return a compact rubric JSON, it can
consume its entire budget thinking and never emit the JSON — the judge then returns an
empty response and the score comes back as zero with no dimensions. A small non-reasoning
model that answers directly is a more reliable judge than a larger reasoning model that
runs out of budget mid-thought. The app defaults the judge selector to a non-reasoning
model for exactly this reason; if you deliberately pick a reasoning judge and see an empty
score, that is the cause.

---

## Steps

1. Click the **Playground** tab.

2. Select the `writing` category (or `instruction_following` — both are judge-evaluated
   datasets).

3. Choose a case. Read the prompt.

4. In the **Model** card, select your candidate model.

5. In the **Mechanisms** card, check **LLM judge**. A **Judge model** selector appears
   below the mechanism list.

6. Select a judge model. If you have both local and cloud models available, try a cloud
   model as the judge first.

7. Click **Evaluate**.

8. In the right panel, read:
   - The model's response.
   - The score card: the overall score, the pass/fail verdict, and the breakdown by
     dimension. The detail string contains the judge's justification.

9. Now run the same case again with a **different candidate model** (use the **Model**
   dropdown in the left panel and evaluate again). Compare the two score cards. Is the
   dimension breakdown different?

10. Optionally: run the same case with the same model as both candidate and judge. Note
    the warning the app displays — or observe whether the scores appear inflated compared
    to the cross-model case.

---

## What to look for

- Which dimension is typically lowest? For instruction-following tasks, completeness often
  reveals gaps before correctness does.
- Read the justification in the detail string. Does it match your own read of the response?
  If the judge gives a high completeness score to a response you found thin, that is
  evidence of judge miscalibration for this task.
- Compare the judge's dimension scores with your own mental rating. Where you agree, the
  judge is reliable. Where you disagree substantially, consider whether the rubric weights
  are appropriate for this category.

---

## Reflection

- The judge is itself a language model. Its scores are not ground truth — they are one
  model's opinion. How would you validate that the judge is grading correctly for a given
  task?
- If you were building a production eval pipeline, would you use the same judge model for
  all categories, or would you calibrate the judge per category? What would that
  calibration process look like?
- The five dimensions have weights that differ by category. If you were adding a new
  category to this dataset (say, a customer service conversation), how would you set the
  weights? Which dimension would you weight most?

---

Previous: [Lab 04 — Execution-based evaluation](04-execution-based-evaluation.md) |
Next: [Lab 06 — Judge reliability](06-judge-reliability.md)
