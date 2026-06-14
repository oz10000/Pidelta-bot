
import numpy as np
import pandas as pd
import math

# ==================== PARAMETERS (FROZEN) ====================
EMA_PERIOD = 20
ADX_PERIOD = 14
ATR_PERIOD = 14

CORR_WINDOW = 50
ADX_THRESHOLD = 25

SIGMOID_SCALE = 10.0
SCORE_THRESHOLD = 0.15


# ==================== INDICATORS ====================

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def atr(df):
    high = df['high']
    low = df['low']
    close = df['close']

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    return tr.rolling(ATR_PERIOD).mean()


def adx(df):
    high = df['high']
    low = df['low']
    close = df['close']

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr_val = tr.rolling(ADX_PERIOD).mean()

    up = high.diff()
    down = -low.diff()

    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)

    plus_di = 100 * pd.Series(plus_dm).rolling(ADX_PERIOD).mean() / atr_val
    minus_di = 100 * pd.Series(minus_dm).rolling(ADX_PERIOD).mean() / atr_val

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
    return dx.rolling(ADX_PERIOD).mean()


# ==================== MACRO ENGINE (FIXED) ====================

def compute_macro_signal(df_btc, df_eth, df_sol):
    """
    Output: macro ∈ [0,1]
    Fully aligned, no scalar/series mixing bugs.
    """

    btc_close = df_btc['close']
    eth_close = df_eth['close']
    sol_close = df_sol['close']

    # EMA series (NOT scalar)
    btc_ema = ema(btc_close, EMA_PERIOD)
    eth_ema = ema(eth_close, EMA_PERIOD)

    # slope as last finite difference (fixed scalar extraction)
    btc_slope = btc_ema.iloc[-1] - btc_ema.iloc[-2]
    eth_slope = eth_ema.iloc[-1] - eth_ema.iloc[-2]

    alignment = 1.0 if (btc_slope * eth_slope > 0) else 0.0
    if alignment == 0.0:
        return 0.0

    # rolling correlation (aligned automatically)
    corr_btc = btc_close.rolling(CORR_WINDOW).corr(sol_close).iloc[-1]
    corr_eth = eth_close.rolling(CORR_WINDOW).corr(sol_close).iloc[-1]

    if np.isnan(corr_btc) or np.isnan(corr_eth):
        return 0.0

    mean_corr = (corr_btc + corr_eth) / 2.0

    # stabilized sigmoid
    macro = 1.0 / (1.0 + math.exp(-SIGMOID_SCALE * (mean_corr - 0.5)))

    return float(np.clip(macro, 0.0, 1.0))


# ==================== MICRO ENGINE (FIXED) ====================

def compute_micro_signal(df_sol):
    """
    Normalized directional pressure.
    FIX: EMA slope normalized by ATR (correct MST-consistent scaling)
    """

    close = df_sol['close']

    ema_series = ema(close, EMA_PERIOD)

    # FIX: scalar slope extraction
    slope = ema_series.iloc[-1] - ema_series.iloc[-2]

    atr_val = atr(df_sol).iloc[-1]
    if atr_val == 0 or np.isnan(atr_val):
        return 0.0

    return slope / atr_val


# ==================== REGIME ====================

def compute_regime(df_sol):
    value = adx(df_sol).iloc[-1]
    if np.isnan(value):
        return 0.0
    return 1.0 if value > ADX_THRESHOLD else 0.0


# ==================== FULL SIGNAL ====================

def compute_signal(df_sol, df_btc, df_eth):
    """
    Clean deterministic signal object.
    """

    micro = compute_micro_signal(df_sol)
    regime = compute_regime(df_sol)
    macro = compute_macro_signal(df_btc, df_eth, df_sol)

    raw_score = micro * regime * macro
    score = math.tanh(raw_score)

    if score > SCORE_THRESHOLD:
        signal = "LONG"
    elif score < -SCORE_THRESHOLD:
        signal = "SHORT"
    else:
        signal = "NONE"

    return {
        "micro": micro,
        "macro": macro,
        "regime": regime,
        "score": score,
        "signal": signal
    }
