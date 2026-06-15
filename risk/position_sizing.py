# risk/position_sizing.py
from utils.precision import get_step_size

def calculate_contracts(
    exchange,
    symbol: str,
    equity: float,
    risk_per_trade: float,
    entry_price: float,
    sl_price: float,
    max_leverage: int
) -> float:
    """
    Calcula el número de contratos a negociar en función del riesgo.

    La fórmula utilizada es la correcta para futuros perpetuos USDT-M (1 contrato = 1 USD):
    contracts = (equity * risk_per_trade) / abs(entry_price - sl_price).
    El apalancamiento se utiliza para limitar la exposición máxima.
    """
    # Distancia del Stop Loss en valor absoluto
    sl_distance = abs(entry_price - sl_price)
    if sl_distance <= 0:
        return 0.0

    # Riesgo en dólares para esta operación
    risk_usd = equity * risk_per_trade

    # Número de contratos basado en el riesgo
    contracts = risk_usd / sl_distance

    # Exposición máxima permitida por el apalancamiento
    max_contracts = (equity * max_leverage) / entry_price
    contracts = min(contracts, max_contracts)

    # Redondeo al tamaño de paso permitido por el exchange
    step = get_step_size(exchange, symbol)
    contracts = round(contracts - (contracts % step), 6)

    return max(0.0, contracts)
