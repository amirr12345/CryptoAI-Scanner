import pandas as pd

from indicators.rsi import RSIIndicator


def test_rsi_range():

    df = pd.DataFrame(
        {
            "close": [
                10,
                11,
                12,
                11,
                12,
                13,
                12,
                14,
                15,
                14,
                16,
                17,
                18,
                19,
                20,
            ]
        }
    )

    rsi = RSIIndicator().calculate(df)

    value = float(rsi.iloc[-1])

    assert 0 <= value <= 100
