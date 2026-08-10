"""
Project-wide constants for signals and scoring.
"""

# ==========================
# Detector Names
# ==========================

EMA = "EMA"
MACD = "MACD"
BOLLINGER = "BOLLINGER"
VOLUME = "VOLUME"


# ==========================
# EMA Signals
# ==========================

GOLDEN_CROSS = "GOLDEN_CROSS"
DEATH_CROSS = "DEATH_CROSS"


# ==========================
# MACD Signals
# ==========================

BULLISH_CROSS = "BULLISH_CROSS"
BEARISH_CROSS = "BEARISH_CROSS"


# ==========================
# Bollinger Signals
# ==========================

BREAKOUT_UP = "BREAKOUT_UP"
BREAKOUT_DOWN = "BREAKOUT_DOWN"
NO_SIGNAL = "NO_SIGNAL"


# ==========================
# Generic Cross
# ==========================

NO_CROSS = "NO_CROSS"


# ==========================
# Volume Signals
# ==========================

STRONG_CONFIRMATION = "STRONG_CONFIRMATION"
WEAK_CONFIRMATION = "WEAK_CONFIRMATION"
NO_CONFIRMATION = "NO_CONFIRMATION"


# ==========================
# Legacy / descriptive volume
# ==========================

HIGH_VOLUME = "HIGH_VOLUME"
LOW_VOLUME = "LOW_VOLUME"


# ==========================
# Detector Scores
# ==========================

EMA_GOLDEN_SCORE = 25
EMA_DEATH_SCORE = -25

MACD_BULLISH_SCORE = 20
MACD_BEARISH_SCORE = -20

BOLLINGER_BREAKOUT_SCORE = 20

VOLUME_CONFIRMATION_SCORE = 15

VOLUME_HIGH_SCORE = 10
VOLUME_LOW_SCORE = -5


# ==========================
# Signal Thresholds
# ==========================

STRONG_BUY_SCORE = 40
BUY_SCORE = 20

STRONG_SELL_SCORE = -40
SELL_SCORE = -20