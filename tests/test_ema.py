import pandas as pd

from indicators.ema import EMAIndicator


def test_ema_calculation():

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
            ]
        }
    )

    ema = EMAIndicator(5).calculate(df)

    assert len(ema) == len(df)

    assert ema.iloc[-1] > ema.iloc[0]

    assert ema.iloc[-1] < df["close"].iloc[-1]
