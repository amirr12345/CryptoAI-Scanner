import pandas as pd

from indicators.volume_indicator import VolumeIndicator


def test_volume_indicator():

    df = pd.DataFrame(
        {
            "volume": list(range(1, 31))
        }
    )

    indicator = VolumeIndicator()

    result = indicator.calculate(df)

    assert "volume_sma20" in result.columns

    assert "volume_ratio" in result.columns

    assert result["volume_sma20"].iloc[-1] > 0

    assert result["volume_ratio"].iloc[-1] > 0