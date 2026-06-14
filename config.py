# config.py
import os

# Modo: 'demo' o 'live'
MODE = "demo"

# Símbolo (swap perpetuo)
SYMBOL = "SOL/USDT:USDT"
TIMEFRAME = "5m"
LEVERAGE = 9

# Porcentajes de TP/SL (1.2% y 1.5% por defecto)
TP_PCT = 0.012
SL_PCT = 0.015

# Umbral de score para activar señal
SCORE_THRESHOLD = 0.15

# Diferencia horaria máxima permitida (ms)
TIME_DIFF_MAX_MS = 2000   # mayor para PyDroid

# Rutas
STATE_FILE = "state/position_state.json"
LOG_FILE = "logs/trading.log"

# Credenciales (se pedirán al inicio si no están en vars de entorno)
API_KEY = os.getenv("OKX_API_KEY")
SECRET_KEY = os.getenv("OKX_SECRET")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")
