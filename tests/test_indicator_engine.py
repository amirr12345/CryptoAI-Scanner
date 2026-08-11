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