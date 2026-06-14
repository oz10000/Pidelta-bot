# signal/signal_engine.py
def compute_signal(df_sol, df_btc, df_eth):
    """
    Ejemplo simple: LONG si el precio sube, SHORT si baja.
    REEMPLAZAR POR TU VERDADERO MOTOR PyDROID.
    """
    if len(df_sol) < 2:
        return {"signal": "NONE", "score": 0.0}
    close_curr = df_sol["close"].iloc[-1]
    close_prev = df_sol["close"].iloc[-2]
    if close_curr > close_prev:
        signal = "LONG"
        score = 0.6
    elif close_curr < close_prev:
        signal = "SHORT"
        score = -0.6
    else:
        signal = "NONE"
        score = 0.0
    return {"signal": signal, "score": score, "tp_pct": None, "sl_pct": None}
