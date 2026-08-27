from microstructure.session_ranking import (
    SessionRankingEngine,
    wilson_lower_bound,
)


def test_small_sample_is_not_ranked():
    rows = [
        {
            "session_name": "LONDON",
            "quality": 10.0,
            "trade_count": 1000,
            "order_flow_strength": 90.0,
            "cvd_strength": 90.0,
            "liquidity_score": 0.9,
            "classification": "BEST",
            "execute": True,
        }
        for _ in range(2)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    assert len(result) == 1
    assert result[0].rank == 0
    assert result[0].confidence == "NOT_RANKED"


def test_large_sample_gets_high_confidence():
    rows = [
        {
            "session_name": "LONDON",
            "quality": 9.0,
            "trade_count": 1500,
            "order_flow_strength": 80.0,
            "cvd_strength": 80.0,
            "liquidity_score": 0.8,
            "classification": "BEST",
            "execute": True,
        }
        for _ in range(25)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    assert result[0].rank == 1
    assert result[0].confidence == "HIGH"
    assert result[0].observed_score > 0.0


def test_bad_session_is_penalized():
    good_rows = [
        {
            "session_name": "LONDON",
            "quality": 9.0,
            "trade_count": 2000,
            "order_flow_strength": 80.0,
            "cvd_strength": 80.0,
            "liquidity_score": 0.9,
            "classification": "BEST",
            "execute": True,
        }
        for _ in range(20)
    ]

    bad_rows = [
        {
            "session_name": "OFF_HOURS",
            "quality": 4.0,
            "trade_count": 100,
            "order_flow_strength": 10.0,
            "cvd_strength": 15.0,
            "liquidity_score": 0.2,
            "classification": "AVOID",
            "execute": False,
        }
        for _ in range(20)
    ]

    result = SessionRankingEngine.rank(
        good_rows + bad_rows
    )

    assert result[0].session_name == "LONDON"
    assert (
        result[1].session_name
        == "OFF_HOURS"
    )


def test_wilson_lower_bound_penalizes_small_sample():
    small = wilson_lower_bound(
        success_count=5,
        sample_count=5,
    )

    large = wilson_lower_bound(
        success_count=90,
        sample_count=100,
    )

    assert small < large


def test_wilson_bound_is_valid():
    value = wilson_lower_bound(
        success_count=50,
        sample_count=100,
    )

    assert 0.0 <= value <= 1.0