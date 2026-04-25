import pytest
from proxy_agent.filters.lynch import score_lynch
from proxy_agent.state import LynchScore


def _data(**kwargs) -> dict:
    return kwargs


class TestEarningsGrowthScore:
    def test_sweet_spot_scores_2(self):
        score = score_lynch("TEST", _data(eps_cagr_3yr=20.0))
        assert score.earnings_growth_score == 2

    def test_lower_band_scores_1(self):
        score = score_lynch("TEST", _data(eps_cagr_3yr=12.0))
        assert score.earnings_growth_score == 1

    def test_too_high_scores_1(self):
        score = score_lynch("TEST", _data(eps_cagr_3yr=35.0))
        assert score.earnings_growth_score == 1

    def test_below_threshold_scores_0(self):
        score = score_lynch("TEST", _data(eps_cagr_3yr=5.0))
        assert score.earnings_growth_score == 0

    def test_falls_back_to_yfinance_growth(self):
        # yfinance earnings_growth is a fraction (0.18 = 18%)
        score = score_lynch("TEST", _data(earnings_growth=0.18))
        assert score.earnings_growth_score == 2


class TestPEGScore:
    def test_peg_under_1_scores_2(self):
        score = score_lynch("TEST", _data(peg_ratio=0.8))
        assert score.peg_score == 2

    def test_peg_between_1_and_1_5_scores_1(self):
        score = score_lynch("TEST", _data(peg_ratio=1.2))
        assert score.peg_score == 1

    def test_peg_above_1_5_scores_0(self):
        score = score_lynch("TEST", _data(peg_ratio=2.5))
        assert score.peg_score == 0

    def test_peg_computed_from_pe_and_growth(self):
        # PE=15, EPS CAGR=20% → PEG = 15/20 = 0.75 → score 2
        score = score_lynch("TEST", _data(pe_ratio_screener=15.0, eps_cagr_3yr=20.0))
        assert score.peg_score == 2


class TestDebtScore:
    def test_low_debt_scores_2(self):
        score = score_lynch("TEST", _data(debt_to_equity_screener=0.3))
        assert score.debt_score == 2

    def test_moderate_debt_scores_1(self):
        score = score_lynch("TEST", _data(debt_to_equity_screener=0.7))
        assert score.debt_score == 1

    def test_high_debt_scores_0(self):
        score = score_lynch("TEST", _data(debt_to_equity_screener=1.5))
        assert score.debt_score == 0

    def test_yfinance_percentage_form_normalised(self):
        # yfinance reports D/E as e.g. 45.2 (meaning 0.452)
        score = score_lynch("TEST", _data(debt_to_equity=30.0))
        assert score.debt_score == 2


class TestPromoterScore:
    def test_high_promoter_scores_2(self):
        score = score_lynch("TEST", _data(promoter_holding=60.0))
        assert score.promoter_score == 2

    def test_moderate_promoter_scores_1(self):
        score = score_lynch("TEST", _data(promoter_holding=45.0))
        assert score.promoter_score == 1

    def test_low_promoter_scores_0(self):
        score = score_lynch("TEST", _data(promoter_holding=20.0))
        assert score.promoter_score == 0


class TestRunwayScore:
    def test_enabler_scores_2(self):
        score = score_lynch("TEST", _data(), is_enabler=True)
        assert score.runway_score == 2

    def test_non_enabler_with_data_scores_1(self):
        score = score_lynch("TEST", _data(pe_ratio=20.0), is_enabler=False)
        assert score.runway_score == 1


class TestTotal:
    def test_perfect_stock_scores_10(self):
        data = _data(
            eps_cagr_3yr=20.0,
            peg_ratio=0.8,
            debt_to_equity_screener=0.2,
            promoter_holding=55.0,
        )
        score = score_lynch("TEST", data, is_enabler=True)
        assert score.total == 10
        assert score.grade == "STRONG"

    def test_weak_stock(self):
        score = score_lynch("TEST", _data(eps_cagr_3yr=3.0, peg_ratio=3.0, debt_to_equity_screener=2.0))
        assert score.grade == "WEAK"

    def test_grade_moderate(self):
        data = _data(eps_cagr_3yr=12.0, peg_ratio=1.2, debt_to_equity_screener=0.7)
        score = score_lynch("TEST", data)
        assert score.grade == "MODERATE"
