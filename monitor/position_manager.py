# monitor/position_manager.py
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, state_file):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def has_open_position(self):
        return self.state.get("open", False)

    def open_position(self, symbol, side, contracts, entry_price, tp_price, sl_price):
        self.state = {
            "open": True,
            "symbol": symbol,
            "side": side,
            "contracts": contracts,
            "entry_price": entry_price,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._save_state()
        logger.info(f"Posición abierta: {side} {contracts} {symbol} @ {entry_price}")

    def close_position(self):
        self.state = {"open": False}
        self._save_state()
        logger.info("Posición cerrada (estado persistente limpiado)")

    def update(self, current_price, atr, score):
        pass

    def break_even(self):
        pass

    def trailing_stop(self):
        pass

    def trailing_take_profit(self):
        pass
