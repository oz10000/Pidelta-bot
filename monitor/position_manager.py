# monitor/position_manager.py
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def has_open_position(self):
        return self.state.get('open', False)

    def open_position(self, symbol: str, side: str, contracts: float, entry_price: float, tp_price: float, sl_price: float, atr: float):
        self.state = {
            "open": True,
            "symbol": symbol,
            "side": side,
            "contracts": contracts,
            "entry_price": entry_price,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "entry_atr": atr,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._save()
        logger.info(f"Posición registrada: {side} {contracts} contratos de {symbol} @ {entry_price}")

    def close_position(self):
        self.state = {"open": False}
        self._save()
        logger.info("Estado de la posición reiniciado.")

    # Métodos preparados para futuras extensiones (p. ej., trailing stop)
    def update(self, current_price, atr, score):
        pass

    def break_even(self):
        pass

    def trailing_stop(self):
        pass

    def trailing_take_profit(self):
        pass
