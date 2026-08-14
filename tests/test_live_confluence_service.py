from dataclasses import dataclass

from models.historical_context import (
    HistoricalContext,
)
from models.structure_setup import (
    StructureSetup,
)
from services.live_confluence_service import (
    LiveConfluenceResult,
    LiveConfluenceService,
)
from services.live_data_freshness import (
    DataFreshnessResult,
)


@dataclass
class FakeEngine:
    result: object

    def calculate(self, **kwargs):
        return self.result

    def evaluate(self, **kwargs):
        return self.result


class FakeFreshnessChecker:
    def __init__(
        self,
        result: DataFreshnessResult,
    ) -> None:
        self.result = result

    def check(self, **kwargs):
        return self.result


def make_setup(
    direction: str = "BULLISH",
    timestamp: int = 1000,
) -> StructureSetup:
    return StructureSetup(
        index=20,
        timestamp=timestamp,
        direction=direction,
        setup=(
            "BULLISH_STRUCTURE_SETUP"
            if direction == "BULLISH"
            else "BEARISH_STRUCTURE_SETUP"
        ),
        sweep_index=18,
        sweep_event="LIQUIDITY_SWEEP",
        mss_index=20,
        mss_event="MSS",
        level_price=100.0,
        sweep_excursion_pct=0.8,
        mss_displacement_pct=1.2,
        bars_between=2,
    )


def make_context(
    timestamp: int = 1000,
) -> HistoricalContext:
    return HistoricalContext(
        symbol="BTC",
        timestamp=timestamp,
        trade_count=100,
        lookback_seconds=3600,
        cvd_direction="BULLISH",
        cvd_strength=80.0,
        cvd_divergence="NONE",
        cvd_delta=50.0,
        cvd_change=60.0,
        vwap=101.0,
        previous_vwap=99.0,
        vwap_position="ABOVE_VWAP",
        vwap_distance_pct=1.0,
        vwap_slope=2.0,
        poc=100.0,
        vah=102.0,
        val=98.0,
        profile_position="BELOW_VALUE_AREA",
        historical=True,
    )


def make_confluence():
    from models.confluence_result import (
        ConfluenceResult,
    )

    return ConfluenceResult(
        direction="BULLISH",
        score=100.0,
        grade="A+",
        structure_points=40.0,
        cvd_points=25.0,
        profile_points=20.0,
        vwap_points=15.0,
        confirmations=(
            "Structure Setup confirmed",
            "CVD strong alignment",
            "Volume Profile location supportive",
            "VWAP directional alignment",
        ),
        conflicts=(),
        reasons=(
            "All major contexts align.",
        ),
        actionable=True,
    )


def make_candles():
    return [
        type(
            "Candle",
            (),
            {
                "timestamp": 1000,
            },
        )(),
        type(
            "Candle",
            (),
            {
                "timestamp": 1000,
            },
        )(),
        type(
            "Candle",
            (),
            {
                "timestamp": 1000,
            },
        )(),
    ]


def fresh_result() -> DataFreshnessResult:
    return DataFreshnessResult(
        latest_candle_timestamp=1000,
        latest_trade_timestamp=1300,
        candle_lag_seconds=300,
        max_allowed_lag_seconds=300,
        fresh=True,
        status="FRESH",
    )


def stale_result() -> DataFreshnessResult:
    return DataFreshnessResult(
        latest_candle_timestamp=1000,
        latest_trade_timestamp=1301,
        candle_lag_seconds=301,
        max_allowed_lag_seconds=300,
        fresh=False,
        status="STALE_CANDLES",
    )


def test_no_candles():
    service = LiveConfluenceService()

    result = service.evaluate(
        symbol="BTC",
        candles=[],
    )

    assert isinstance(
        result,
        LiveConfluenceResult,
    )

    assert result.status == "NO_CANDLES"


def test_stale_candles_stop_pipeline():
    structure = type(
        "Structure",
        (),
        {
            "swings": [object()],
        },
    )()

    service = LiveConfluenceService(
        market_structure_engine=FakeEngine(
            result=structure,
        ),
        freshness_checker=FakeFreshnessChecker(
            stale_result(),
        ),
    )

    result = service.evaluate(
        symbol="BTC",
        candles=make_candles(),
    )

    assert result.status == "STALE_CANDLES"
    assert result.setup is None
    assert result.confluence is None

    assert (
        "301s > 300s"
        in result.reason
    )


def test_fresh_data_allows_structure_analysis():
    structure = type(
        "Structure",
        (),
        {
            "swings": [],
        },
    )()

    service = LiveConfluenceService(
        market_structure_engine=FakeEngine(
            result=structure,
        ),
        freshness_checker=FakeFreshnessChecker(
            fresh_result(),
        ),
    )

    result = service.evaluate(
        symbol="BTC",
        candles=make_candles(),
    )

    assert result.status == "NO_STRUCTURE"


def test_no_structure_break():
    structure = type(
        "Structure",
        (),
        {
            "swings": [object()],
        },
    )()

    breaks = type(
        "Breaks",
        (),
        {
            "events": [],
        },
    )()

    service = LiveConfluenceService(
        market_structure_engine=FakeEngine(
            result=structure,
        ),
        structure_break_engine=FakeEngine(
            result=breaks,
        ),
        freshness_checker=FakeFreshnessChecker(
            fresh_result(),
        ),
    )

    result = service.evaluate(
        symbol="BTC",
        candles=make_candles(),
    )

    assert result.status == "NO_STRUCTURE_BREAK"


def test_no_liquidity_sweep():
    structure = type(
        "Structure",
        (),
        {
            "swings": [object()],
        },
    )()

    breaks = type(
        "Breaks",
        (),
        {
            "events": [object()],
        },
    )()

    sweeps = type(
        "Sweeps",
        (),
        {
            "events": [],
        },
    )()

    service = LiveConfluenceService(
        market_structure_engine=FakeEngine(
            result=structure,
        ),
        structure_break_engine=FakeEngine(
            result=breaks,
        ),
        liquidity_sweep_engine=FakeEngine(
            result=sweeps,
        ),
        freshness_checker=FakeFreshnessChecker(
            fresh_result(),
        ),
    )

    result = service.evaluate(
        symbol="BTC",
        candles=make_candles(),
    )

    assert result.status == "NO_LIQUIDITY_SWEEP"


def test_no_structure_setup():
    structure = type(
        "Structure",
        (),
        {
            "swings": [object()],
        },
    )()

    breaks = type(
        "Breaks",
        (),
        {
            "events": [object()],
        },
    )()

    sweeps = type(
        "Sweeps",
        (),
        {
            "events": [object()],
        },
    )()

    setups = type(
        "Setups",
        (),
        {
            "setups": [],
        },
    )()

    service = LiveConfluenceService(
        market_structure_engine=FakeEngine(
            result=structure,
        ),
        structure_break_engine=FakeEngine(
            result=breaks,
        ),
        liquidity_sweep_engine=FakeEngine(
            result=sweeps,
        ),
        structure_setup_engine=FakeEngine(
            result=setups,
        ),
        freshness_checker=FakeFreshnessChecker(
            fresh_result(),
        ),
    )

    result = service.evaluate(
        symbol="BTC",
        candles=make_candles(),
    )

    assert result.status == "NO_STRUCTURE_SETUP"


def test_no_historical_data():
    setup = make_setup()

    structure = type(
        "Structure",
        (),
        {
            "swings": [object()],
        },
    )()

    breaks = type(
        "Breaks",
        (),
        {
            "events": [object()],
        },
    )()

    sweeps = type(
        "Sweeps",
        (),
        {
            "events": [object()],
        },
    )()

    setups = type(
        "Setups",
        (),
        {
            "setups": [setup],
        },
    )()

    service = LiveConfluenceService(
        market_structure_engine=FakeEngine(
            result=structure,
        ),
        structure_break_engine=FakeEngine(
            result=breaks,
        ),
        liquidity_sweep_engine=FakeEngine(
            result=sweeps,
        ),
        structure_setup_engine=FakeEngine(
            result=setups,
        ),
        historical_context_engine=FakeEngine(
            result=None,
        ),
        freshness_checker=FakeFreshnessChecker(
            fresh_result(),
        ),
    )

    service.historical_context.calculate = (
        lambda **kwargs: (
            _ for _ in ()
        ).throw(
            ValueError(
                "No historical trades available."
            )
        )
    )

    result = service.evaluate(
        symbol="BTC",
        candles=make_candles(),
        latest_trade_timestamp=1300,
    )

    assert result.status == "NO_HISTORICAL_DATA"
    assert result.setup == setup
    assert result.confluence is None


def test_full_pipeline_evaluates():
    setup = make_setup()
    context = make_context()

    structure = type(
        "Structure",
        (),
        {
            "swings": [object()],
        },
    )()

    breaks = type(
        "Breaks",
        (),
        {
            "events": [object()],
        },
    )()

    sweeps = type(
        "Sweeps",
        (),
        {
            "events": [object()],
        },
    )()

    setups = type(
        "Setups",
        (),
        {
            "setups": [setup],
        },
    )()

    confluence = make_confluence()

    service = LiveConfluenceService(
        market_structure_engine=FakeEngine(
            result=structure,
        ),
        structure_break_engine=FakeEngine(
            result=breaks,
        ),
        liquidity_sweep_engine=FakeEngine(
            result=sweeps,
        ),
        structure_setup_engine=FakeEngine(
            result=setups,
        ),
        historical_context_engine=FakeEngine(
            result=context,
        ),
        historical_confluence_engine=FakeEngine(
            result=confluence,
        ),
        freshness_checker=FakeFreshnessChecker(
            fresh_result(),
        ),
    )

    result = service.evaluate(
        symbol="BTC",
        candles=make_candles(),
        latest_trade_timestamp=1300,
    )

    assert result.status == "EVALUATED"
    assert result.setup == setup
    assert result.confluence is not None
    assert result.confluence.grade == "A+"
    assert result.confluence.actionable is True