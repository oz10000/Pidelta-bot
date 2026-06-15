# config.py
import os

# --- Modo de operación ---
MODE = "demo"  # "demo" or "live". WARNING: 'live' will use real funds.

# --- Activos a operar (Orden de prioridad: SOL, ETH, BTC) ---
ASSETS = ["SOL/USDT:USDT", "ETH/USDT:USDT", "BTC/USDT:USDT"]

# --- Parámetros de trading ---
TIMEFRAME = "5m"
RISK_PER_TRADE = 0.02       # Riesgo por operación (2% del capital)
MAX_LEVERAGE = 9            # Apalancamiento máximo fijo
TP_ATR_MULT = 1.2           # Take Profit = 1.2 * ATR
SL_ATR_MULT = 1.5           # Stop Loss = 1.5 * ATR
SCORE_THRESHOLD = 0.15      # Umbral mínimo de señal
TIME_DIFF_MAX_MS = 2000     # Máxima diferencia horaria permitida (ms)

# --- Filtro de horario (UTC) ---
TRADE_HOURS_START = 8       # 08:00 UTC
TRADE_HOURS_END = 20        # 20:00 UTC

# --- Rutas de persistencia y logs ---
STATE_FILE = "state/position_state.json"
LOG_FILE = "logs/trading.log"

# --- Credenciales de la API (se leen de variables de entorno) ---
API_KEY = os.getenv("OKX_API_KEY")
SECRET_KEY = os.getenv("OKX_SECRET")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")
