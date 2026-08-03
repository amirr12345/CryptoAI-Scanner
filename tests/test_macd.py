import pandas as pd

from indicators.macd import MACDIndicator


def test_macd_output():

    df = pd.DataFrame(
        {
            "close": [
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
            ]
        }
    )

    macd = MACDIndicator().calculate(df)

    assert "macd" in macd.columns
    assert "signal" in macd.columns
    assert "histogram" in macd.columns

    assert len(macd) == len(df)
