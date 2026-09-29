from workshop_evals.domain.models import AgreementVerdict
from workshop_evals.domain.statistics import (
    agreement_verdict,
    mae,
    pearson,
    rank_agreement,
    spearman,
)


class TestPearson:
    def test_perfect_positive(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert abs(pearson(xs, ys) - 1.0) < 1e-9

    def test_perfect_negative(self):
        xs = [1.0, 2.0, 3.0]
        ys = [3.0, 2.0, 1.0]
        assert abs(pearson(xs, ys) + 1.0) < 1e-9

    def test_constant_y_returns_zero(self):
        xs = [1.0, 2.0, 3.0]
        ys = [5.0, 5.0, 5.0]
        assert pearson(xs, ys) == 0.0

    def test_constant_x_returns_zero(self):
        xs = [3.0, 3.0, 3.0]
        ys = [1.0, 2.0, 3.0]
        assert pearson(xs, ys) == 0.0

    def test_single_element_returns_zero(self):
        assert pearson([1.0], [1.0]) == 0.0

    def test_empty_returns_zero(self):
        assert pearson([], []) == 0.0

    def test_result_in_range(self):
        xs = [1.0, 2.0, 3.0, 4.0]
        ys = [1.0, 2.0, 3.0, 100.0]
        r = pearson(xs, ys)
        assert -1.0 <= r <= 1.0
        assert r > 0.0  # positive trend

    def test_returns_float(self):
        assert isinstance(pearson([1.0, 2.0], [2.0, 1.0]), float)


class TestSpearman:
    def test_monotone_increasing(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert abs(spearman(xs, ys) - 1.0) < 1e-9

    def test_monotone_decreasing(self):
        xs = [1.0, 2.0, 3.0]
        ys = [3.0, 2.0, 1.0]
        assert abs(spearman(xs, ys) + 1.0) < 1e-9

    def test_ties_handled_without_error(self):
        xs = [1.0, 1.0, 2.0]
        ys = [1.0, 2.0, 3.0]
        result = spearman(xs, ys)
        assert -1.0 <= result <= 1.0

    def test_all_ties(self):
        # Constant series → rank variance is 0 → 0.0
        xs = [5.0, 5.0, 5.0]
        ys = [1.0, 2.0, 3.0]
        assert spearman(xs, ys) == 0.0

    def test_single_element_returns_zero(self):
        assert spearman([1.0], [1.0]) == 0.0

    def test_non_linear_monotone(self):
        # Exponential relationship → perfect Spearman
        xs = [1.0, 2.0, 3.0, 4.0]
        ys = [2.0, 4.0, 8.0, 16.0]
        assert abs(spearman(xs, ys) - 1.0) < 1e-9


class TestRankAgreement:
    def test_all_concordant(self):
        xs = [1.0, 2.0, 3.0]
        ys = [1.0, 2.0, 3.0]
        assert rank_agreement(xs, ys) == 1.0

    def test_all_discordant(self):
        xs = [1.0, 2.0, 3.0]
        ys = [3.0, 2.0, 1.0]
        assert rank_agreement(xs, ys) == 0.0

    def test_all_tied_pairs(self):
        # dx=0 and dy=0 for every pair → total=0 → 0.0
        xs = [1.0, 1.0, 1.0]
        ys = [2.0, 2.0, 2.0]
        assert rank_agreement(xs, ys) == 0.0

    def test_partial(self):
        xs = [1.0, 2.0, 3.0]
        ys = [1.0, 3.0, 2.0]
        # (0,1): concordant; (0,2): concordant; (1,2): discordant → 2/3
        assert abs(rank_agreement(xs, ys) - 2.0 / 3.0) < 1e-9

    def test_empty_returns_zero(self):
        assert rank_agreement([], []) == 0.0

    def test_single_element_returns_zero(self):
        assert rank_agreement([5.0], [3.0]) == 0.0

    def test_result_in_range(self):
        xs = [3.0, 1.0, 4.0, 1.0, 5.0]
        ys = [2.0, 7.0, 1.0, 8.0, 2.0]
        r = rank_agreement(xs, ys)
        assert 0.0 <= r <= 1.0


class TestMae:
    def test_identical_sequences(self):
        assert mae([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_known_value(self):
        result = mae([1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
        assert abs(result - 1.0) < 1e-9

    def test_empty_returns_zero(self):
        assert mae([], []) == 0.0

    def test_symmetry(self):
        xs = [5.0, 3.0, 1.0]
        ys = [1.0, 2.0, 6.0]
        assert abs(mae(xs, ys) - mae(ys, xs)) < 1e-9

    def test_single_element(self):
        assert abs(mae([3.0], [1.0]) - 2.0) < 1e-9

    def test_large_difference(self):
        result = mae([0.0, 0.0], [10.0, 10.0])
        assert abs(result - 10.0) < 1e-9


class TestAgreementVerdict:
    def test_reliable_clear(self):
        assert agreement_verdict(0.9, 0.5) == AgreementVerdict.RELIABLE

    def test_reliable_at_boundary(self):
        assert agreement_verdict(0.7, 1.5) == AgreementVerdict.RELIABLE

    def test_questionable_high_mae(self):
        # Pearson >= 0.7 but MAE > 1.5 → not RELIABLE → QUESTIONABLE
        assert agreement_verdict(0.75, 2.0) == AgreementVerdict.QUESTIONABLE

    def test_questionable_lower_pearson(self):
        assert agreement_verdict(0.5, 0.1) == AgreementVerdict.QUESTIONABLE

    def test_questionable_at_boundary(self):
        assert agreement_verdict(0.4, 99.0) == AgreementVerdict.QUESTIONABLE

    def test_unreliable_clear(self):
        assert agreement_verdict(0.1, 5.0) == AgreementVerdict.UNRELIABLE

    def test_unreliable_below_questionable_boundary(self):
        assert agreement_verdict(0.39, 0.1) == AgreementVerdict.UNRELIABLE

    def test_unreliable_zero_pearson(self):
        assert agreement_verdict(0.0, 0.0) == AgreementVerdict.UNRELIABLE

    def test_reliable_returns_enum(self):
        assert isinstance(agreement_verdict(0.8, 1.0), AgreementVerdict)
