# Lab 07 — The Full Matrix

## Goal

Run a multi-model, multi-mechanism matrix to explore where models differ and where they
converge. Use offline demo mode if you do not have models available. Consider how the
evaluation loop you have built today would fit into a CI pipeline.

---

## Concept

### From a single cell to a full sweep

Every lab until now has been a targeted experiment: one case, one model, a few mechanisms.
The Matrix view removes those constraints. You select multiple cases, define multiple
candidates (each potentially a different model and prompt), choose multiple mechanisms,
and the app evaluates every combination in parallel.

The result is a table where patterns become visible. A model that excels on classification
but struggles on code generation tells you something about its training data and capability
boundaries. A model that passes exact match at 100% but scores 0.5 on the LLM judge
tells you the responses are technically correct but thin. A mechanism that always returns
0.0 for a particular model is a signal worth investigating — is the output format wrong,
or is the model genuinely failing the task?

The value of the matrix grows with scale, but even a 5×3 table (five cases, three
candidates) surfaces patterns that sequential spot-checking would miss.

### Offline demo mode

If you do not have local models installed or cloud API keys, the backend can be started
with `WORKSHOP_EVALS_FAKE_LLM=1`. In this mode, all model calls return canned responses
instantly. The scores you see are not meaningful — they reflect fixed fake outputs, not
real model capabilities — but the UI, the matrix layout, the progress bar, and all the
controls work exactly as they would with real models.

Offline demo mode is useful for exploring the interface before a workshop session, for
demonstrating the workflow on a machine without a GPU, or for testing UI changes without
incurring API costs.

### Evals as a CI gate

This workshop is a manual, exploratory setting. In production, the evaluation matrix
would run automatically on every pull request or model update. The pattern is
straightforward:

1. Maintain a fixed evaluation dataset — the same cases every run.
2. Define an acceptance threshold for each mechanism (e.g. exact match accuracy ≥ 0.90,
   LLM judge average ≥ 0.75).
3. Run the matrix against each model version being tested.
4. Block promotion if any mechanism falls below threshold.

This is equivalent to a test suite for model behavior. Just as unit tests catch regressions
in code, an eval matrix catches regressions in model output quality. The backend's
`POST /api/runs` endpoint is the natural integration point: CI calls it, polls
`GET /api/runs/{id}` until status is completed, checks the scores, and exits with an
appropriate code.

The datasets and thresholds are the specification. If you cannot write them down, you
cannot automate the gate.

---

## Steps

1. Click the **Matrix** tab.

2. **Set up the cases.** Choose `sentiment_classification` from the **Category** dropdown.
   Select all available cases by clicking each checkbox, or use the first 8–10.

3. **Set up the candidates.** You will create three candidates:

   - **Candidate 1** — Label: `small-naive`. Model: smallest available (e.g. Llama 3.2 3B
     or Qwen3 4B). No prompt override.

   - Click **Add candidate**. **Candidate 2** — Label: `small-refined`. Same model as
     candidate 1. In the **Prompt override** field, paste a refined version of the prompt
     (e.g. the one from Lab 02, or write your own with explicit label definitions and an
     output format constraint).

   - Click **Add candidate** again. **Candidate 3** — Label: `large-naive`. Model: the
     largest available model. No prompt override.

4. **Set up the mechanisms.** Check **Exact match**. If you have a judge model available,
   also check **LLM judge** and select the judge.

5. Click **Run matrix**.

6. Watch the progress bar. The total number of cells is (number of cases) × (number of
   candidates) × (number of mechanisms per case). They run in parallel.

7. When complete, read the table. Look for the pattern described in Lab 02: does
   `small-refined` score close to `large-naive`? Does it exceed `small-naive`?

8. Add a fourth candidate: same large model, with the refined prompt. Label it
   `large-refined`. Run again. This gives you the full 2×2: small vs large, naive vs
   refined.

---

## What to look for

- The column that performs best overall is the one you would deploy — but "best" depends on
  cost. A `small-refined` candidate that matches `large-naive` at a lower token count is
  the Pareto-optimal choice.
- Cells that fail with `error` chips indicate a mechanism configuration issue or a model
  that did not return parseable output. Click through to the Playground to debug a single
  failing cell.
- If you ran with both exact match and LLM judge, compare the two rows in each column.
  A candidate that passes exact match reliably but scores 0.5–0.7 on the judge is giving
  correct but thin answers. The judge is picking up on quality dimensions the exact match
  cannot see.

### Offline demo mode walkthrough

If you started the backend with `WORKSHOP_EVALS_FAKE_LLM=1`:

1. Set up the matrix as above.
2. Run it. Cells will complete nearly instantly.
3. The scores will not reflect real model capability. Use this time to explore the
   interface: resize the browser, try adding more candidates, note how the table scrolls,
   observe the progress indicator.
4. The real value of offline mode is UI familiarity before a session where real models
   are available.

---

## Thinking about CI integration

Before wrapping up, consider the following scenario for a real project:

- You have a classification feature powered by a language model.
- You define 30 test cases covering common inputs, edge cases, and a few adversarial ones.
- You set thresholds: exact match accuracy ≥ 0.90, LLM judge average ≥ 0.75.
- Every time the model configuration changes (new model version, new prompt, new
  temperature), CI runs the matrix and compares against thresholds.
- A regression on either metric blocks the deployment.

This is not hypothetical — it is exactly how evaluation-driven development works for
production AI systems. The tools you used in this workshop are the building blocks.
The discipline is: define the criteria before you ship, not after you see failures.

---

## Reflection

- Which mechanism would you trust most as a CI gate for a classification task? For a code
  generation task? For a customer-facing writing task?
- The evaluation set is a specification. Who owns it, and who can change it? What is the
  risk of a developer modifying the evaluation set to make a failing candidate pass?
- You ran evaluations manually today. What would an automated version of this workflow
  look like in your current project? What is the biggest obstacle to implementing it?

---

Previous: [Lab 06 — Judge reliability](06-judge-reliability.md) |
Back to: [Workshop index](README.md)
