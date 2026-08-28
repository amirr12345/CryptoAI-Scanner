from microstructure.session_ranking import (
    SessionRankingEngine,
    SessionPerformance,
    wilson_lower_bound,
)


def make_row(
    session_name="LONDON",
    quality=9.0,
    trade_count=1500,
    order_flow_strength=80.0,
    cvd_strength=80.0,
    liquidity_score=0.8,
    classification="BEST",
    execute=True,
):
    return {
        "session_name": session_name,
        "quality": quality,
        "trade_count": trade_count,
        "order_flow_strength": order_flow_strength,
        "cvd_strength": cvd_strength,
        "liquidity_score": liquidity_score,
        "classification": classification,
        "execute": execute,
    }


def test_small_sample_is_not_ranked():

    rows = [
        make_row()
        for _ in range(2)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    assert len(result) == 1

    assert result[0].rank == 0

    assert (
        result[0].confidence
        == "NOT_RANKED"
    )


def test_large_sample_gets_high_confidence():

    rows = [
        make_row()
        for _ in range(25)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    assert result[0].rank == 1

    assert (
        result[0].confidence
        == "HIGH"
    )

    assert (
        result[0].observed_score
        > 0.0
    )


def test_bad_session_is_ranked_below_good_session():

    good_rows = [
        make_row(
            session_name="LONDON",
            quality=9.0,
            order_flow_strength=80.0,
            cvd_strength=80.0,
            liquidity_score=0.9,
            classification="BEST",
            execute=True,
        )
        for _ in range(20)
    ]

    bad_rows = [
        make_row(
            session_name="OFF_HOURS",
            quality=4.0,
            trade_count=100,
            order_flow_strength=10.0,
            cvd_strength=15.0,
            liquidity_score=0.2,
            classification="AVOID",
            execute=False,
        )
        for _ in range(20)
    ]

    result = SessionRankingEngine.rank(
        good_rows
        + bad_rows
    )

    assert (
        result[0].session_name
        == "LONDON"
    )

    assert (
        result[1].session_name
        == "OFF_HOURS"
    )


def test_session_lookup():

    rows = [
        make_row(
            session_name="LONDON",
        )
        for _ in range(20)
    ]

    rows += [
        make_row(
            session_name="NEW_YORK",
        )
        for _ in range(20)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    london = (
        SessionRankingEngine.get_session(
            result,
            "LONDON",
        )
    )

    assert london is not None

    assert (
        london.session_name
        == "LONDON"
    )


def test_ranked_high_quality_session_can_execute():

    rows = [
        make_row(
            session_name="LONDON",
            quality=9.2,
            order_flow_strength=85.0,
            cvd_strength=85.0,
            liquidity_score=0.9,
            classification="BEST",
            execute=True,
        )
        for _ in range(30)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    decision = (
        SessionRankingEngine.decide(
            performance=result[0],
            primary_grade="A+",
            primary_conflict=False,
        )
    )

    assert (
        decision.decision
        == "EXECUTE"
    )

    assert (
        decision.confidence
        == "HIGH"
    )


def test_medium_confidence_waits():

    rows = [
        make_row(
            session_name="LONDON",
            quality=9.0,
            order_flow_strength=85.0,
            cvd_strength=85.0,
            liquidity_score=0.9,
            classification="BEST",
            execute=True,
        )
        for _ in range(15)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    decision = (
        SessionRankingEngine.decide(
            performance=result[0],
            primary_grade="A+",
            primary_conflict=False,
        )
    )

    assert (
        decision.decision
        == "WAIT"
    )

    assert (
        decision.confidence
        == "MEDIUM"
    )


def test_primary_conflict_blocks():

    rows = [
        make_row(
            quality=9.5,
            classification="BEST",
            execute=True,
        )
        for _ in range(30)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    decision = (
        SessionRankingEngine.decide(
            performance=result[0],
            primary_grade="A+",
            primary_conflict=True,
        )
    )

    assert (
        decision.decision
        == "BLOCK"
    )


def test_low_quality_session_blocks():

    rows = [
        make_row(
            quality=4.5,
            order_flow_strength=10.0,
            cvd_strength=10.0,
            liquidity_score=0.2,
            classification="AVOID",
            execute=False,
        )
        for _ in range(30)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    decision = (
        SessionRankingEngine.decide(
            performance=result[0],
            primary_grade="A+",
            primary_conflict=False,
        )
    )

    assert (
        decision.decision
        == "BLOCK"
    )


def test_low_best_rate_waits():

    rows = []

    for _ in range(30):

        rows.append(
            make_row(
                quality=8.5,
                classification="GOOD",
                execute=False,
            )
        )

    result = SessionRankingEngine.rank(
        rows
    )

    decision = (
        SessionRankingEngine.decide(
            performance=result[0],
            primary_grade="A+",
            primary_conflict=False,
        )
    )

    assert (
        decision.decision
        == "WAIT"
    )


def test_high_avoid_rate_waits():

    rows = []

    for _ in range(20):

        rows.append(
            make_row(
                quality=9.0,
                classification="BEST",
                execute=True,
            )
        )

    for _ in range(10):

        rows.append(
            make_row(
                quality=4.0,
                classification="AVOID",
                execute=False,
            )
        )

    result = SessionRankingEngine.rank(
        rows
    )

    decision = (
        SessionRankingEngine.decide(
            performance=result[0],
            primary_grade="A+",
            primary_conflict=False,
        )
    )

    assert (
        decision.decision
        == "WAIT"
    )


def test_b_grade_waits():

    rows = [
        make_row()
        for _ in range(30)
    ]

    result = SessionRankingEngine.rank(
        rows
    )

    decision = (
        SessionRankingEngine.decide(
            performance=result[0],
            primary_grade="B",
            primary_conflict=False,
        )
    )

    assert (
        decision.decision
        == "WAIT"
    )


def test_missing_performance_waits():

    decision = (
        SessionRankingEngine.decide(
            performance=None,
            primary_grade="A+",
            primary_conflict=False,
        )
    )

    assert (
        decision.decision
        == "WAIT"
    )

    assert (
        decision.confidence
        == "NOT_RANKED"
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