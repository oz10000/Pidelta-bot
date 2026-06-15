# signal/signal_engine.py
import numpy as np
import pandas as pd
import math
from typing import Dict

# ==================== PARÁMETROS CONGELADOS ====================
EMA_PERIOD = 20
ADX_PERIOD = 14
ATR_PERIOD = 14
CORR_WINDOW = 50
ADX_THRESHOLD = 25
SIGMOID_SCALE = 10.0
MIN_CANDLES = max(EMA_PERIOD, ADX_PERIOD, ATR_PERIOD, CORR_WINDOW) + 10

# ==================== INDICADORES TÉCNICOS ====================
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def true_range(df: pd.DataFrame) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']
    return pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

def atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    return true_range(df).rolling(period).mean()

def wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1/period, adjust=False).mean()

def adx(df: pd.DataFrame, period: int = ADX_PERIOD) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']

    tr = true_range(df)

    up_move = high.diff()
    down_move = low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr_smooth = wilder_smooth(tr, period)
    plus_di = 100 * wilder_smooth(pd.Series(plus_dm), period) / atr_smooth
    minus_di = 100 * wilder_smooth(pd.Series(minus_dm), period) / atr_smooth

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
    return wilder_smooth(dx, period)

# ==================== COMPONENTES DE LA SEÑAL ====================
def _micro_signal(df: pd.DataFrame) -> float:
    if len(df) < EMA_PERIOD + 2:
        return 0.0
    e = ema(df['close'], EMA_PERIOD)
    slope = e.iloc[-1] - e.iloc[-2]
    a = atr(df).iloc[-1]
    if pd.isna(a) or a == 0:
        return 0.0
    return slope / a

def _regime(df: pd.DataFrame) -> float:
    if len(df) < ADX_PERIOD + 1:
        return 0.0
    a = adx(df).iloc[-1]
    return 1.0 if not pd.isna(a) and a > ADX_THRESHOLD else 0.0

def _macro_signal(df_primary: pd.DataFrame, df_btc: pd.DataFrame, df_eth: pd.DataFrame) -> float:
    if len(df_btc) < EMA_PERIOD + 1 or len(df_eth) < EMA_PERIOD + 1 or len(df_primary) < CORR_WINDOW:
        return 0.0

    e_btc = ema(df_btc['close'], EMA_PERIOD)
    e_eth = ema(df_eth['close'], EMA_PERIOD)
    btc_slope = e_btc.iloc[-1] - e_btc.iloc[-2]
    eth_slope = e_eth.iloc[-1] - e_eth.iloc[-2]

    # La alineación de la pendiente actúa como un filtro maestro: si BTC y ETH no se mueven en la misma dirección, el macro es 0.
    if btc_slope * eth_slope <= 0:
        return 0.0

    # Correlaciones de los últimos CORR_WINDOW períodos
    corr_btc = df_btc['close'].iloc[-CORR_WINDOW:].corr(df_primary['close'].iloc[-CORR_WINDOW:])
    corr_eth = df_eth['close'].iloc[-CORR_WINDOW:].corr(df_primary['close'].iloc[-CORR_WINDOW:])
    if pd.isna(corr_btc) or pd.isna(corr_eth):
        return 0.0

    mean_corr = (corr_btc + corr_eth) / 2.0
    # Función sigmoide para convertir la correlación en un valor entre 0 y 1
    z = SIGMOID_SCALE * (mean_corr - 0.5)
    if z > 50:
        return 1.0
    if z < -50:
        return 0.0
    return float(np.clip(1.0 / (1.0 + math.exp(-z)), 0.0, 1.0))

# ==================== GENERACIÓN DE LA SEÑAL ====================
def compute_signal_for_asset(
    symbol: str,
    df_self: pd.DataFrame,
    df_btc: pd.DataFrame,
    df_eth: pd.DataFrame
) -> Dict:
    """Genera la señal de trading para un activo específico."""
    if len(df_self) < MIN_CANDLES or len(df_btc) < MIN_CANDLES or len(df_eth) < MIN_CANDLES:
        return {"asset": symbol, "signal": "none", "score": 0.0, "atr": 0.0, "adx": 0.0}

    micro = _micro_signal(df_self)
    regime = _regime(df_self)
    macro = _macro_signal(df_self, df_btc, df_eth)

    raw_score = micro * regime * macro
    score = math.tanh(raw_score)

    atr_val = atr(df_self).iloc[-1] if len(df_self) >= ATR_PERIOD else 0.0
    adx_val = adx(df_self).iloc[-1] if len(df_self) >= ADX_PERIOD else 0.0

    if score > 0.15:
        signal = "long"
    elif score < -0.15:
        signal = "short"
    else:
        signal = "none"

    return {
        "asset": symbol,
        "signal": signal,
        "score": score,
        "atr": atr_val,
        "adx": adx_val
    }
