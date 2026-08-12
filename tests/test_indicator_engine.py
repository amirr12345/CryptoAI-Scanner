import pandas as pd

from indicators.indicator_engine import IndicatorEngine


def test_indicator_engine_adds_required_columns():
    rows = 60

    df = pd.DataFrame(
        {
            "open": range(100, 100 + rows),
            "high": range(101, 101 + rows),
            "low": range(99, 99 + rows),
            "close": range(100, 100 + rows),
            "volume": [1000] * rows,
        }
    )

    result = IndicatorEngine().calculate(df)

    required_columns = {
        "ema20",
        "ema50",
        "macd",
        "signal",
        "histogram",
        "rsi",
        "atr",
        "middle_band",
        "upper_band",
        "lower_band",
        "bandwidth",
        "volume_sma20",
        "volume_ratio",
    }

    assert required_columns.issubset(result.columns)


def test_indicator_engine_preserves_original_columns():
    rows = 60

    df = pd.DataFrame(
        {
            "open": range(100, 100 + rows),
            "high": range(101, 101 + rows),
            "low": range(99, 99 + rows),
            "close": range(100, 100 + rows),
            "volume": [1000] * rows,
        }
    )

    result = IndicatorEngine().calculate(df)

    for column in df.columns:
        assert column in result.columns


def test_indicator_engine_handles_empty_dataframe():
    df = pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"]
    )

    result = IndicatorEngine().calculate(df)

    assert result.empty
    assert list(result.columns) == list(df.columns)
def test_indicator_engine_includes_vwap():
    data = pd.DataFrame(
        {
            "timestamp": [1, 2, 3],
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [95.0, 96.0, 97.0],
            "close": [102.0, 104.0, 106.0],
            "volume": [100.0, 200.0, 300.0],
        }
    )

    engine = IndicatorEngine()

    result = engine.calculate(data)

    assert "vwap" in result.columns
    assert result["vwap"].notna().any()