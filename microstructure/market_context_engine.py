from __future__ import annotations

from indicators.vwap_context import VWAPContext, build_vwap_context
from microstructure.bucketed_cvd_divergence import (
    BucketedCVDAnalyzer,
)
from microstructure.cvd_strength import (
    CVDStrengthAnalyzer,
)
from microstructure.market_context_fusion import (
    MarketContextFusionEngine,
)
from microstructure.time_bucketed_cvd import (
    TimeBucketedCVDEngine,
)
from microstructure.volume_profile import (
    VolumeProfileEngine,
)
from models.market_context_snapshot import (
    MarketContextSnapshot,
)
from models.trade import Trade


class MarketContextEngine:
    """
    Build a complete market context from normalized trades
    and VWAP data.

    This engine is provider-agnostic.
    """

    def __init__(
        self,
        bucket_interval_seconds: int = 60,
        cvd_lookback: int = 5,
        cvd_swing_window: int = 2,
        volume_profile_bins: int = 24,
        value_area_pct: float = 70.0,
    ):
        self.bucket_interval_seconds = (
            bucket_interval_seconds
        )

        self.cvd_lookback = cvd_lookback
        self.cvd_swing_window = cvd_swing_window

        self.volume_profile_bins = (
            volume_profile_bins
        )

        self.value_area_pct = value_area_pct

        self.time_bucketed_cvd = (
            TimeBucketedCVDEngine()
        )

        self.cvd_analyzer = (
            BucketedCVDAnalyzer()
        )

        self.cvd_strength = (
            CVDStrengthAnalyzer()
        )

        self.volume_profile = (
            VolumeProfileEngine()
        )

        self.fusion = (
            MarketContextFusionEngine()
        )

    def build(
        self,
        trades: list[Trade],
        current_price: float,
        vwap: float,
        previous_vwap: float | None = None,
    ) -> MarketContextSnapshot:
        """
        Build complete market context.

        Parameters
        ----------
        trades:
            Normalized executed trades.

        current_price:
            Latest market price.

        vwap:
            Latest VWAP value.

        previous_vwap:
            Previous VWAP value used for slope calculation.
        """

        if not trades:
            raise ValueError(
                "Trades are required for market context."
            )

        vwap_context = build_vwap_context(
            price=current_price,
            vwap=vwap,
            previous_vwap=previous_vwap,
        )

        buckets = (
            self.time_bucketed_cvd.calculate(
                trades=trades,
                interval_seconds=(
                    self.bucket_interval_seconds
                ),
            )
        )

        bucket_analysis = (
            self.cvd_analyzer.analyze(
                buckets=buckets,
                swing_window=self.cvd_swing_window,
            )
        )

        cvd_strength = (
            self.cvd_strength.analyze(
                buckets=buckets,
                analysis=bucket_analysis,
                lookback=self.cvd_lookback,
            )
        )

        volume_profile = (
            self.volume_profile.calculate(
                trades=trades,
                bins=self.volume_profile_bins,
                value_area_pct=self.value_area_pct,
                current_price=current_price,
            )
        )

        fusion = self.fusion.combine(
            cvd=cvd_strength,
            vwap=vwap_context,
            profile=volume_profile,
        )

        return MarketContextSnapshot(
            cvd=cvd_strength,
            vwap=vwap_context,
            volume_profile=volume_profile,
            fusion=fusion,
        )