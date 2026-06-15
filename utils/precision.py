# utils/precision.py
def get_step_size(exchange, symbol: str) -> float:
    """Obtiene el stepSize para la cantidad de contratos de un símbolo."""
    market = exchange.market(symbol)
    # Extracción del stepSize de la información del mercado
    step = market.get('limits', {}).get('amount', {}).get('step')
    if step is None:
        step = market.get('precision', {}).get('amount')
    if step is None:
        step = 0.001   # Valor predeterminado seguro para SOL, ETH y BTC
    return float(step)

def round_amount_by_step(amount: float, step: float) -> float:
    """Redondea la cantidad al stepSize más cercano."""
    if step <= 0:
        return amount
    return round(amount - (amount % step), 6)
