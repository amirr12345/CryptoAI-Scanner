from models.liquidity_sweep import LiquiditySweep
from models.structure_break import StructureBreak
from microstructure.structure_setup import (
    StructureSetupEngine,
)


def bullish_sweep(
    index: int = 10,
) -> LiquiditySweep:
    return LiquiditySweep(
        index=index,
        timestamp=index,
        event="BULLISH_LIQUIDITY_SWEEP",
        direction="BULLISH",
        level_index=8,
        level_price=100.0,
        level_kind="LOW",
        candle_high=105.0,
        candle_low=95.0,
        candle_close=101.0,
        excursion=5.0,
        excursion_pct=5.0,
        rejection=6.0,
        rejection_pct=6.0,
    )


def bearish_sweep(
    index: int = 10,
) -> LiquiditySweep:
    return LiquiditySweep(
        index=index,
        timestamp=index,
        event="BEARISH_LIQUIDITY_SWEEP",
        direction="BEARISH",
        level_index=8,
        level_price=100.0,
        level_kind="HIGH",
        candle_high=105.0,
        candle_low=96.0,
        candle_close=99.0,
        excursion=5.0,
        excursion_pct=5.0,
        rejection=6.0,
        rejection_pct=6.0,
    )


def bullish_mss(
    index: int = 12,
) -> StructureBreak:
    return StructureBreak(
        index=index,
        timestamp=index,
        price=105.0,
        event="MSS",
        direction="BULLISH",
        broken_index=9,
        broken_price=102.0,
        displacement=3.0,
        displacement_pct=2.94,
    )


def bearish_mss(
    index: int = 12,
) -> StructureBreak:
    return StructureBreak(
        index=index,
        timestamp=index,
        price=95.0,
        event="MSS",
        direction="BEARISH",
        broken_index=9,
        broken_price=98.0,
        displacement=-3.0,
        displacement_pct=3.06,
    )


def test_builds_bullish_structure_setup():
    result = StructureSetupEngine().calculate(
        sweeps=[bullish_sweep(10)],
        structure_breaks=[bullish_mss(12)],
    )

    assert len(result.setups) == 1

    setup = result.setups[0]

    assert setup.direction == "BULLISH"
    assert (
        setup.setup
        == "BULLISH_STRUCTURE_SETUP"
    )

    assert setup.sweep_index == 10
    assert setup.mss_index == 12
    assert setup.bars_between == 2

    assert result.latest_direction == "BULLISH"
    assert result.bullish_setup_count == 1
    assert result.bearish_setup_count == 0


def test_builds_bearish_structure_setup():
    result = StructureSetupEngine().calculate(
        sweeps=[bearish_sweep(10)],
        structure_breaks=[bearish_mss(13)],
    )

    assert len(result.setups) == 1

    setup = result.setups[0]

    assert setup.direction == "BEARISH"
    assert (
        setup.setup
        == "BEARISH_STRUCTURE_SETUP"
    )

    assert setup.sweep_index == 10
    assert setup.mss_index == 13
    assert setup.bars_between == 3

    assert result.latest_direction == "BEARISH"
    assert result.bullish_setup_count == 0
    assert result.bearish_setup_count == 1


def test_mss_before_sweep_is_rejected():
    result = StructureSetupEngine().calculate(
        sweeps=[bullish_sweep(12)],
        structure_breaks=[bullish_mss(10)],
    )

    assert result.setups == []


def test_opposite_direction_is_rejected():
    result = StructureSetupEngine().calculate(
        sweeps=[bullish_sweep(10)],
        structure_breaks=[bearish_mss(12)],
    )

    assert result.setups == []


def test_choch_does_not_create_setup():
    choch = StructureBreak(
        index=12,
        timestamp=12,
        price=105.0,
        event="CHoCH",
        direction="BULLISH",
        broken_index=9,
        broken_price=102.0,
        displacement=3.0,
        displacement_pct=2.94,
    )

    result = StructureSetupEngine().calculate(
        sweeps=[bullish_sweep(10)],
        structure_breaks=[choch],
    )

    assert result.setups == []


def test_bos_does_not_create_setup():
    bos = StructureBreak(
        index=12,
        timestamp=12,
        price=105.0,
        event="BOS",
        direction="BULLISH",
        broken_index=9,
        broken_price=102.0,
        displacement=3.0,
        displacement_pct=2.94,
    )

    result = StructureSetupEngine().calculate(
        sweeps=[bullish_sweep(10)],
        structure_breaks=[bos],
    )

    assert result.setups == []


def test_max_bars_after_sweep_is_respected():
    result = StructureSetupEngine().calculate(
        sweeps=[bullish_sweep(10)],
        structure_breaks=[bullish_mss(21)],
        max_bars_after_sweep=10,
    )

    assert result.setups == []


def test_same_sweep_is_not_consumed_twice():
    result = StructureSetupEngine().calculate(
        sweeps=[bullish_sweep(10)],
        structure_breaks=[
            bullish_mss(11),
            bullish_mss(12),
        ],
    )

    assert len(result.setups) == 1


def test_closest_valid_sweep_is_selected():
    sweeps = [
        bullish_sweep(5),
        bullish_sweep(10),
    ]

    result = StructureSetupEngine().calculate(
        sweeps=sweeps,
        structure_breaks=[
            bullish_mss(12),
        ],
    )

    assert len(result.setups) == 1
    assert result.setups[0].sweep_index == 10


def test_empty_inputs_return_empty_result():
    result = StructureSetupEngine().calculate(
        sweeps=[],
        structure_breaks=[],
    )

    assert result.setups == []
    assert result.latest_setup == "NONE"
    assert result.latest_direction == "NEUTRAL"
    assert result.bullish_setup_count == 0
    assert result.bearish_setup_count == 0


def test_rejects_negative_max_bars():
    result_sweep = bullish_sweep(10)
    result_mss = bullish_mss(12)

    try:
        StructureSetupEngine().calculate(
            sweeps=[result_sweep],
            structure_breaks=[result_mss],
            max_bars_after_sweep=-1,
        )
    except ValueError as exc:
        assert (
            "Max bars after sweep cannot be negative"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )


def test_latest_setup_matches_last_setup():
    result = StructureSetupEngine().calculate(
        sweeps=[
            bullish_sweep(10),
            bearish_sweep(20),
        ],
        structure_breaks=[
            bullish_mss(12),
            bearish_mss(22),
        ],
    )

    assert len(result.setups) == 2

    assert (
        result.latest_setup
        == result.setups[-1].setup
    )

    assert (
        result.latest_direction
        == result.setups[-1].direction
    )