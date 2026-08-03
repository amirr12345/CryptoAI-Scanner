import pandas as pd

from indicators.bollinger import BollingerIndicator


def test_bollinger():

    prices = list(range(100, 130))

    df = pd.DataFrame({
        "close": prices
    })

    bb = BollingerIndicator().calculate(df)

    assert len(bb) == len(df)

    assert "upper" in bb.columns
    assert "middle" in bb.columns
    assert "lower" in bb.columns
    assert "bandwidth" in bb.columns

    assert bb["upper"].iloc[-1] > bb["middle"].iloc[-1]
    assert bb["lower"].iloc[-1] < bb["middle"].iloc[-1]