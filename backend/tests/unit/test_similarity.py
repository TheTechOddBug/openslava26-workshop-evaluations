from workshop_evals.domain.scoring.similarity import bleu, fuzzy, rouge_l


class TestBleu:
    def test_identical(self):
        score, _ = bleu("the cat sat on the mat", "the cat sat on the mat")
        assert score > 0.99

    def test_completely_disjoint(self):
        score, _ = bleu("one two three four", "five six seven eight")
        assert score < 0.05

    def test_empty_response(self):
        score, detail = bleu("", "something")
        assert score == 0.0
        assert "empty" in detail.lower()

    def test_empty_reference(self):
        score, detail = bleu("something", "")
        assert score == 0.0
        assert "empty" in detail.lower()

    def test_partial_overlap(self):
        # Three tokens from a six-token reference; score should be between 0 and 1
        score, _ = bleu("the cat sat", "the cat sat on the mat")
        assert 0.0 < score < 1.0

    def test_brevity_penalty_applied(self):
        # Very short hypothesis gets a severe brevity penalty
        score_short, _ = bleu("cat", "the cat sat on the mat")
        score_full, _ = bleu("the cat sat on the mat", "the cat sat on the mat")
        assert score_short < score_full

    def test_returns_float(self):
        score, _ = bleu("hello world", "hello world")
        assert isinstance(score, float)

    def test_detail_contains_bp(self):
        _, detail = bleu("hello", "hello")
        assert "bp=" in detail

    def test_single_token_identical(self):
        # Single-token case: only 1-gram is computed; brevity penalty = 1
        score, _ = bleu("hello", "hello")
        assert score > 0.9

    def test_extra_words_reduce_score(self):
        # Extra words in hypothesis cause precision to drop vs exact match
        score_exact, _ = bleu("the cat sat", "the cat sat")
        score_extra, _ = bleu("the cat sat on the mat now", "the cat sat")
        assert score_extra <= score_exact


class TestRougeL:
    def test_identical(self):
        score, _ = rouge_l("the cat sat", "the cat sat")
        assert score > 0.99

    def test_completely_disjoint(self):
        score, _ = rouge_l("one two three", "four five six")
        assert score == 0.0

    def test_empty_response(self):
        score, detail = rouge_l("", "something")
        assert score == 0.0
        assert "empty" in detail.lower()

    def test_empty_reference(self):
        score, detail = rouge_l("something", "")
        assert score == 0.0
        assert "empty" in detail.lower()

    def test_partial_overlap(self):
        score, _ = rouge_l("the cat", "the cat sat on the mat")
        assert 0.0 < score < 1.0

    def test_returns_float(self):
        score, _ = rouge_l("hello world", "hello")
        assert isinstance(score, float)

    def test_known_lcs(self):
        # hyp = "A B C", ref = "A C B" → LCS length = 2 (A + either B or C)
        score, detail = rouge_l("A B C", "A C B")
        assert "lcs=2" in detail

    def test_symmetry_approximately(self):
        # F1 with beta=1 is symmetric when precision == recall, but not in general;
        # at least both orderings should give scores > 0
        s1, _ = rouge_l("a b c d", "a b")
        s2, _ = rouge_l("a b", "a b c d")
        assert s1 > 0.0
        assert s2 > 0.0

    def test_detail_contains_lcs_precision_recall(self):
        _, detail = rouge_l("a b c", "a b c")
        assert "lcs=" in detail
        assert "P=" in detail
        assert "R=" in detail


class TestFuzzy:
    def test_identical(self):
        score, _ = fuzzy("hello world", "hello world")
        assert score == 1.0

    def test_completely_different(self):
        score, _ = fuzzy("abcdef", "xyz123")
        # No characters in common → very low ratio
        assert score < 0.4

    def test_both_empty(self):
        score, _ = fuzzy("", "")
        assert score == 1.0

    def test_one_empty(self):
        score, _ = fuzzy("hello", "")
        assert score == 0.0

    def test_case_normalized(self):
        # After lowercase both are identical
        score, _ = fuzzy("Hello World", "hello world")
        assert score == 1.0

    def test_partial_match(self):
        score, _ = fuzzy("hello world", "hello")
        assert 0.0 < score < 1.0

    def test_returns_float(self):
        score, _ = fuzzy("abc", "abc")
        assert isinstance(score, float)

    def test_detail_contains_ratio(self):
        _, detail = fuzzy("abc", "abd")
        assert "ratio=" in detail

    def test_score_in_range(self):
        for a, b in [("abc", "abd"), ("x", "xyz"), ("", "a"), ("foo bar", "bar foo")]:
            score, _ = fuzzy(a, b)
            assert 0.0 <= score <= 1.0
