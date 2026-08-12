import pandas as pd
import pytest

from indicators.vwap_indicator import VWAPIndicator


def test_vwap_calculation():
    data = pd.DataFrame(
        {
            "high": [12.0, 14.0],
            "low": [8.0, 10.0],
            "close": [10.0, 12.0],
            "volume": [100.0, 200.0],
        }
    )

    indicator = VWAPIndicator()

    result = indicator.calculate(data)

    # Candle 1:
    # Typical = (12 + 8 + 10) / 3 = 10
    # VWAP = 10
    #
    # Candle 2:
    # Typical = (14 + 10 + 12) / 3 = 12
    # VWAP = (10*100 + 12*200) / 300
    #      = 11.333333...
    assert result["vwap"].iloc[0] == pytest.approx(
        10.0
    )

    assert result["vwap"].iloc[1] == pytest.approx(
        11.3333333333
    )


def test_vwap_handles_zero_volume():
    data = pd.DataFrame(
        {
            "high": [12.0, 14.0],
            "low": [8.0, 10.0],
            "close": [10.0, 12.0],
            "volume": [0.0, 0.0],
        }
    )

    indicator = VWAPIndicator()

    result = indicator.calculate(data)

    assert result["vwap"].isna().all()


def test_vwap_ignores_zero_volume_after_valid_volume():
    data = pd.DataFrame(
        {
            "high": [12.0, 14.0],
            "low": [8.0, 10.0],
            "close": [10.0, 12.0],
            "volume": [100.0, 0.0],
        }
    )

    indicator = VWAPIndicator()

    result = indicator.calculate(data)

    assert result["vwap"].iloc[0] == pytest.approx(
        10.0
    )

    assert result["vwap"].iloc[1] == pytest.approx(
        10.0
    )


def test_vwap_rejects_missing_columns():
    data = pd.DataFrame(
        {
            "high": [12.0],
            "low": [8.0],
            "close": [10.0],
        }
    )

    indicator = VWAPIndicator()

    with pytest.raises(
        ValueError,
        match="Missing required columns",
    ):
        indicator.calculate(data)


def test_vwap_rejects_negative_volume():
    data = pd.DataFrame(
        {
            "high": [12.0],
            "low": [8.0],
            "close": [10.0],
            "volume": [-1.0],
        }
    )

    indicator = VWAPIndicator()

    with pytest.raises(
        ValueError,
        match="VWAP volume cannot be negative",
    ):
        indicator.calculate(data)


def test_vwap_rejects_non_numeric_values():
    data = pd.DataFrame(
        {
            "high": [12.0],
            "low": [8.0],
            "close": ["invalid"],
            "volume": [100.0],
        }
    )

    indicator = VWAPIndicator()

    with pytest.raises(
        ValueError,
        match="VWAP input contains non-numeric values",
    ):
        indicator.calculate(data)


def test_vwap_empty_dataframe():
    data = pd.DataFrame(
        columns=[
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    indicator = VWAPIndicator()

    result = indicator.calculate(data)

    assert result.empty
    assert "vwap" in result.columns