import pandas as pd

from indicators.atr import ATRIndicator


def test_atr():

    df = pd.DataFrame(
        {
            "high": [11, 12, 13, 14, 15, 16, 17],
            "low": [9, 10, 11, 12, 13, 14, 15],
            "close": [10, 11, 12, 13, 14, 15, 16],
        }
    )

    atr = ATRIndicator(period=3).calculate(df)

    assert len(atr) == len(df)

    assert atr.iloc[-1] > 0