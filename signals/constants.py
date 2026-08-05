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
# Signal Types
# ==========================

GOLDEN_CROSS = "GOLDEN_CROSS"
DEATH_CROSS = "DEATH_CROSS"

BULLISH_CROSS = "BULLISH_CROSS"
BEARISH_CROSS = "BEARISH_CROSS"

UPPER_BREAKOUT = "UPPER_BREAKOUT"
LOWER_BREAKOUT = "LOWER_BREAKOUT"

INSIDE_BANDS = "INSIDE_BANDS"

NO_CROSS = "NO_CROSS"

# ==========================
# Scores
# ==========================

EMA_GOLDEN_SCORE = 25
EMA_DEATH_SCORE = -25

MACD_BULLISH_SCORE = 20
MACD_BEARISH_SCORE = -20

BOLLINGER_BREAKOUT_SCORE = 15
VOLUME_CONFIRMATION_SCORE = 10