# Lab 03 — Similarity Metrics

## Goal

Score summarization cases with BLEU, ROUGE-L, and fuzzy match; understand what overlap
metrics measure and where they stop being useful.

---

## Concept

### The overlap intuition

BLEU and ROUGE-L both measure how much the model's output overlaps with a reference text
in terms of word sequences. They were developed for machine translation and summarization
evaluation in the early 2000s, when human ratings were slow and expensive. The appeal was
straightforward: if the model produces the same words in roughly the same order as a
professional translator, the translation is probably good.

BLEU measures precision: what fraction of the model's n-grams also appear in the
reference. ROUGE-L measures recall via the longest common subsequence: how much of the
reference's content is covered by the model's output. Both produce a number between 0 and 1.

Fuzzy match is character-level: it measures edit distance (the number of insertions,
deletions, and substitutions to turn one string into the other). It is simpler and faster
than BLEU/ROUGE-L, less theory-laden, and useful as a quick sanity check for near-exact
tasks.

### Where overlap metrics are useful

For tasks where the correct output is largely determined — structured extraction, keyword
lists, verbatim quotation — overlap metrics work well. A model that extracts the correct
entities from a document will produce output that closely matches the reference extraction,
and ROUGE-L will reflect that.

For summarization tasks, overlap metrics are useful as a cheap first signal. A summary
that scores below 0.2 on ROUGE-L is almost certainly missing large portions of the source
content or using radically different vocabulary. A score above 0.6 suggests substantial
overlap with the reference summary.

### Where overlap metrics mislead

The core problem is that overlap metrics are purely surface-level. They cannot distinguish
between a paraphrase that conveys the same meaning and a response that shares words with
the reference but is factually wrong. They reward verbosity (more words, more chances to
overlap with the reference) and penalize concise paraphrase.

Consider these two summaries of a source document that says "The merger was approved by
regulators after six months of review":

- Model A: "Regulators approved the merger following a six-month review period." — ROUGE-L
  close to 1.0, and the meaning is correct.
- Model B: "The merger received approval after a lengthy regulatory review." — ROUGE-L
  lower (different vocabulary), but the meaning is identical.
- Model C: "The merger was rejected by regulators after six months." — ROUGE-L moderate
  (shares most words), but the meaning is completely wrong.

An LLM judge would correctly rank Model A = Model B > Model C. ROUGE-L would rank
Model A > Model C > Model B — inverting the meaningful comparison.

This is not an argument against using BLEU and ROUGE-L. It is an argument for
understanding what they measure so you do not over-interpret a score.

### The three-mechanism comparison

The Playground lets you run all three similarity mechanisms at once on the same response.
This is useful for calibration: a response that scores consistently across BLEU, ROUGE-L,
and fuzzy is in a stable region. When ROUGE-L is high but BLEU is low, the response has
good content coverage but unusual phrasing. When fuzzy is high but ROUGE-L is low, the
surface forms are similar but the sequence structure differs.

---

## Steps

1. Click the **Playground** tab.

2. Select the `summarization` category from the **Category** dropdown.

3. Choose the first case. Read the prompt — it is a longer text with an instruction to
   summarize.

4. In the **Model** card, select your candidate model.

5. In the **Mechanisms** card, check **BLEU**, **ROUGE-L**, and **Fuzzy match**.
   (Exact match will be greyed out — it is not applicable to summarization cases because
   the reference is a free-form summary, not a fixed string.)

6. Click **Evaluate**.

7. Read the three score cards. Note:
   - The numerical score for each.
   - The detail string — for ROUGE-L it shows the LCS length and lengths of both
     strings; for BLEU it shows the precision scores.

8. Now add **LLM judge** to the selected mechanisms. Set a judge model.

9. Click **Evaluate** again on the same case.

10. Compare the LLM judge score with the ROUGE-L score. Are they in agreement? If they
    diverge, read the model's response and the reference carefully.

11. Try a second case in the `summarization` dataset. If the model produces a very concise
    summary, note how BLEU and ROUGE-L respond to brevity.

---

## What to look for

- A high ROUGE-L with a low BLEU often means the model produced a longer response that
  covers the reference content but adds extra material. BLEU penalizes this through its
  brevity penalty; ROUGE-L does not penalize length in the same way.
- A low ROUGE-L with a high LLM judge score is the clearest example of the overlap vs.
  meaning gap. The model paraphrased well; the judge noticed; the n-gram counter did not.
- Fuzzy match will score highest when the model echoes the reference nearly verbatim. If
  the model is instructed to "summarize in one sentence" and the reference is also one
  sentence, fuzzy and ROUGE-L tend to converge.

---

## Reflection

- Which of the three similarity metrics do you find most interpretable for summarization?
  Why?
- Is there a task in your own work where ROUGE-L would be a reliable proxy for quality?
  Where would it be dangerous to use alone?
- The LLM judge costs more (a second model call) but handles paraphrase correctly. How
  would you decide when the extra cost is justified?

---

Previous: [Lab 02 — Prompt refinement](02-prompt-refinement.md) |
Next: [Lab 04 — Execution-based evaluation](04-execution-based-evaluation.md)
