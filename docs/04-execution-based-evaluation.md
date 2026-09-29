# Lab 04 — Execution-Based Evaluation

## Goal

Score code generation cases with code execution and SQL cases with SQL execution.
Understand why running the output as a program is a more powerful test than comparing
its text.

---

## Concept

### The problem with grading code by reading it

When you look at a piece of code and decide it is correct, you are mentally simulating
the execution: you trace through the logic, check the data types, imagine the edge cases.
That simulation is imperfect, slow, and hard to automate. Text comparison is worse: two
functions that look different can be semantically identical, and two functions that look
similar can produce different outputs on certain inputs.

The correct grader for code is code. Write a test suite that expresses what the function
must do, run the model's output against that suite, and the result is a binary verdict:
pass or fail. The grader does not care whether the model used a loop or a list
comprehension, whether it named the variable `i` or `idx`, or whether it included
comments. It only asks: does this code produce the right answer?

This is what the `code_exec` mechanism does. It extracts code from the model's response
(handling fenced blocks, reasoning-model think tags, and various formatting conventions),
appends the test suite from the dataset, and runs the result in a subprocess. If the
tests pass and the exit code is zero, the score is 1.0.

The `sql_exec` mechanism applies the same logic to SQL: the model's query and the
reference query are both executed against an in-memory SQLite database (schema and data
provided in the case), and the result sets are compared. The comparison is exact if the
reference query includes an `ORDER BY` clause; otherwise it is multiset (order-
insensitive). A correct SQL query scores 1.0 regardless of whether it is written as a
join, a subquery, or a CTE.

### Deterministic and powerful

Both mechanisms share two properties that make them especially valuable:

**Determinism.** Given the same response and the same test suite, the score is always the
same. There is no variability from a judge model's interpretation, no sensitivity to
prompt wording, no randomness.

**Functional correctness.** The grader cares only about whether the code does what it is
supposed to do. It captures off-by-one errors, wrong variable names, missing edge case
handling, and SQL mistakes that would produce subtly wrong result sets — things that a
reading-based grader would easily miss.

The practical implication: for any task where you can express the acceptance criteria as
executable tests, you should. It is free, it is robust, and it is the closest you can get
to what actually matters in production — does the code work?

### The output extraction challenge

Language models do not always return clean code. They may include explanatory prose, wrap
the code in markdown fences, or output a `<think>` block before the answer (common in
reasoning models like Qwen3). The extraction step handles all of these: it looks for a
fenced code block, falls back to a raw code scan, and validates the result with an AST
parser before running it.

This means your evaluation is robust to formatting variation — but it also means you do
not need to prompt the model to return clean code. You can evaluate whatever the model
naturally produces and let the extractor do the cleanup.

---

## Steps — Code execution

1. Click the **Playground** tab.

2. Select the `code_generation` category.

3. Choose the first case. The prompt will describe a programming problem.

4. Select your candidate model.

5. In the **Mechanisms** card, check **Code execution**. Note that the mechanism is
   enabled for this category — the case supplies a test suite.

6. Click **Evaluate**.

7. In the right panel, read the model's response. The model likely returned a code block,
   possibly with an explanation.

8. Look at the score card:
   - Score 1.0 means the extracted code passed all tests.
   - Score 0.0 means it failed. The detail string will include the test output.

9. Try two or three more cases from the same dataset. Note the pass rate informally.

---

## Steps — SQL execution

1. Stay in the **Playground** tab.

2. Select the `sql` category.

3. Choose the first case. Read the prompt — it describes a database query problem.

4. Select your candidate model.

5. Check **SQL execution** in the **Mechanisms** card.

6. Click **Evaluate**.

7. Read the score card. The detail string describes whether the result sets matched or
   diverged, and (on failure) what the expected and actual sets looked like.

8. Try a case from `reasoning` and check **Numeric tolerance**. Note that this is also a
   deterministic mechanism — it extracts the final number from the response and checks
   it within a 1% relative tolerance. Arithmetic is graded by arithmetic.

---

## What to look for

- When code execution scores 0.0, read the detail carefully. Common failure modes:
  - Syntax error: the model returned non-compilable code.
  - Test assertion error: the logic is wrong.
  - Timeout: the model produced an algorithm too slow for the test limits.
  Each failure mode points to a different intervention.
- For SQL, note whether the failing case uses `ORDER BY`. Without it, the comparison is
  a multiset comparison — the model can return rows in any order.
- Compare the code execution score with what you would have said reading the code. Do you
  agree with the grader? If a human would have passed the code but the grader fails it,
  the test suite may be too strict; if the grader passes code you find wrong, the test
  suite may be incomplete.

---

## Reflection

- Execution-based evaluation is binary. A function either passes all tests or it does not.
  Is there a case where you would want a partial-credit score for code?
- The test suite is part of the evaluation. Who should write it, and how do you ensure it
  covers the right cases without over-specifying (making the grader reject correct
  alternative solutions)?
- Could you apply execution-based evaluation to a non-code task? What would be the
  analogue of a "test suite" for a structured data extraction task?

---

Previous: [Lab 03 — Similarity metrics](03-similarity-metrics.md) |
Next: [Lab 05 — LLM as judge](05-llm-as-judge.md)
