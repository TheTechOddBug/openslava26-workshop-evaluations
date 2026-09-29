# Lab 06 — Judge Reliability

## Goal

Use the Judge reliability view to measure how consistently a judge model agrees with a
stronger reference judge. Understand self-preference bias and how the meta-evaluation
metrics are interpreted.

---

## Concept

### The judge is not infallible

Lab 05 introduced the LLM judge as a tool for scoring open-ended responses. The natural
follow-up question is: how much should you trust it?

The answer depends on the judge, the task, and the dataset. A judge model that agrees
strongly with a human expert (or a stronger reference model) on a set of responses is
well-calibrated for that task. A judge that produces scores uncorrelated with the
reference is unreliable regardless of how authoritative it sounds.

Meta-evaluation — evaluating the evaluator — is the discipline of measuring this
reliability. It is not optional if you want to use LLM judgments as a production signal.
Deploying an uncalibrated judge is worse than using no automatic evaluation at all: you
will have false confidence in scores that do not reflect real quality.

### Self-preference bias

One well-documented failure mode for LLM judges is self-preference: when a model is asked
to grade a response it could have written, it tends to score responses that match its own
style higher than responses that do not. This applies even when the responses are equally
correct or informative.

The practical consequence is that if you use the same model as both candidate and judge,
the scores are upward-biased. A model grading its own outputs will appear more capable
than it is, because it is evaluating on a metric that correlates with its own generation
tendencies.

The app flags this condition. If you select the same model for both the candidate and
the judge under test, the interface warns you. This is not a hard block — there are
legitimate reasons to observe the effect — but the warning is there because the scores
from a self-evaluating setup should not be treated as unbiased ground truth.

### Position bias — the Compare view

Another well-documented failure mode is position bias: when a judge compares two answers,
it can favour whichever one appears first (or second), independent of quality. The
**Compare** tab makes this measurable. It asks the judge which of two answers is better,
then — with "Swap positions" enabled — asks again with the two answers in swapped
positions. If the winner is the same answer both times, the judge is judging quality. If
the winner flips to whatever now sits in the favoured position, the verdict was driven by
order, not content, and the app flags position bias. A judge that fails this swap test
cannot be trusted for pairwise ranking without averaging over both orderings.

### Ensemble judging — the Ensemble view

A single judge is one noisy opinion. The **Ensemble** tab scores one answer with several
judges at once and reports their average plus the spread (standard deviation) of their
scores. Averaging independent judges reduces the influence of any single model's quirks,
much as averaging several human raters does. The spread is itself a signal: when the
judges cluster tightly the average is trustworthy; when they disagree widely, the task is
hard to judge and no single number should be taken at face value.

### Agreement metrics

The Judge reliability view reports four metrics, all derived from comparing the "judge
under test" scores against the "reference judge" scores on a random sample of cases:

**Pearson r** measures linear correlation between the two judges' scores. A value close to
1.0 means the judges rank responses in the same order and assign similar magnitudes.
A value near 0 means the judges are effectively unrelated.

**Spearman ρ** measures rank correlation — it cares about the ordering but not the
magnitudes. Spearman is more robust to one judge using a compressed range (e.g., clustering
scores near 0.5) while the other uses the full range.

**Rank agreement** is a direct concordance measure: the fraction of case pairs where both
judges agree on which response is better.

**Mean absolute error (MAE)** measures the average difference between the two judges'
scores, dimension by dimension on the 0–10 scale. MAE is more interpretable than
correlation for diagnosing magnitude bias: an MAE of 1.0 means the judges differ by
about one point out of ten on average.

The verdict is computed from Pearson r and MAE together:
- Pearson ≥ 0.7 and MAE ≤ 1.5: **reliable**
- Pearson ≥ 0.4: **uncertain**
- Otherwise: **unreliable**

The dimension breakdown shows MAE per dimension, which lets you identify where the judges
disagree most. If the two judges agree on correctness but diverge sharply on robustness,
that tells you the robustness rubric is underspecified or that the two models have
different implicit standards for edge-case handling.

### What the reference judge means

The reference judge is assumed to be a stronger, more calibrated model. In practice, this
is usually the largest frontier model available to you — for example, GPT-4o or Claude
Sonnet as a reference against a local Qwen3 judge.

"Stronger" means two things: (1) more likely to be consistently calibrated, and (2) more
likely to match human expert judgment if you ran a human validation study. It does not
mean the reference judge is infallible — it means it is your best available proxy for
ground truth.

If you want to validate the reference judge itself, you would need human-rated labels for
the same sample. That is the end of the meta-evaluation chain: at some point, you have to
anchor to human judgment. The meta-evaluation here automates the step below that anchor.

---

## Steps

1. Click the **Judge reliability** tab.

2. In the **Setup** card:
   - **Dataset category**: select `writing`, `instruction_following`, or `code_review`.
     The view uses all cases in the selected category.
   - **Candidate model**: choose the model that will generate the answers.
   - **Judge under test**: choose the model you want to evaluate as a judge. Start with a
     local model (e.g. Qwen3 4B) to see what a smaller judge looks like.
   - **Reference judge**: choose a stronger model — ideally a cloud model if you have
     keys, or the largest local model if not.

3. Click **Measure agreement**.

4. The button label changes through two phases: "Generating answers…" (the candidate
   is responding to every case in the dataset), then "Comparing judges…" (the reference
   judge is re-scoring a sample).

5. When done, read the three result cards:
   - **Verdict**: reliable, uncertain, or unreliable.
   - **Agreement metrics**: Pearson r, Spearman ρ, rank agreement, mean absolute error.
   - **Error by dimension**: a bar chart showing MAE per dimension. Longer bars indicate
     more disagreement.

6. Note the sample size shown in the verdict card. This is the number of cases the
   reference judge re-scored.

7. Run the experiment again with the same model as both candidate and judge. Compare the
   verdict and metrics. Does the self-evaluating setup look more reliable or less reliable
   than the cross-model setup? (The self-preference effect often shows up as lower
   reference judge agreement, because the reference judge applies different standards
   than the candidate model's own style.)

---

## What to look for

- The dimension breakdown is the most diagnostic part of the output. A high MAE on
  correctness is serious — the two judges fundamentally disagree on factual accuracy.
  A high MAE on efficiency or clarity is less alarming — these are more subjective
  dimensions.
- Pearson r measures linear agreement; if one judge compresses all scores into a narrow
  band, Pearson will be low even if the ordering is perfectly correlated. In that case,
  Spearman ρ will be higher, and the MAE will tell you about the magnitude compression.
- A "reliable" verdict with Pearson = 0.72 and MAE = 1.4 means the judge is trustworthy
  but not perfect. You would still want to spot-check 10–20 individual cases before
  deploying it in production.

---

## Reflection

- If a judge scores as "unreliable" on a dataset, what are your options? Can you improve
  the judge by giving it a more explicit rubric? By using a different model? By narrowing
  the task scope?
- How many cases do you think you need in the sample for the agreement metrics to be
  statistically meaningful? What would you do if your dataset has only 10 cases?
- This app compares two model judges. How would you compare a model judge against a human
  judge? What would that workflow look like in a real evaluation pipeline?

---

Previous: [Lab 05 — LLM as judge](05-llm-as-judge.md) |
Next: [Lab 07 — The full matrix](07-the-full-matrix.md)
