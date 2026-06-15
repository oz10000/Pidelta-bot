# data/market_data.py
import ccxt
import pandas as pd

# Cliente público de Binance sin necesidad de API key
_binance = ccxt.binance({'enableRateLimit': True})

def fetch_ohlcv(symbol: str, timeframe: str = '5m', limit: int = 200) -> pd.DataFrame:
    """Descarga velas OHLCV de Binance y las devuelve como un DataFrame."""
    if symbol.endswith(':USDT'):
        symbol = symbol.replace(':USDT', '')

    ohlcv = _binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    return df
