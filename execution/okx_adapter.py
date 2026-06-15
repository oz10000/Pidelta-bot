# execution/okx_adapter.py
import time
import logging
from .okx_orders import OKXOrders
from config import MODE, TIME_DIFF_MAX_MS, TP_ATR_MULT, SL_ATR_MULT

logger = logging.getLogger(__name__)

class OKXAdapter:
    def __init__(self, api_key, secret_key, passphrase):
        self.orders = OKXOrders(api_key, secret_key, passphrase, MODE)

    def health_check(self):
        try:
            self.orders.fetch_balance()
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def check_server_time(self):
        server = self.orders.exchange.fetch_time()
        local = int(time.time() * 1000)
        diff = server - local
        return diff, abs(diff) <= TIME_DIFF_MAX_MS

    def fetch_position(self, symbol: str):
        positions = self.orders.fetch_positions([symbol])
        for pos in positions:
            if float(pos.get('contracts', 0)) != 0:
                return {
                    "side": pos['side'],
                    "contracts": float(pos['contracts']),
                    "entry_price": float(pos['entryPrice'])
                }
        return None

    def setup_symbol(self, symbol: str, leverage: int):
        self.orders.set_margin_and_leverage(symbol, leverage)

    def open_position(self, symbol: str, side: str, contracts: float):
        return self.orders.place_market_order(symbol, side, contracts, reduce_only=False)

    def set_tp_sl(self, symbol: str, side: str, contracts: float, entry_price: float, atr: float):
        if side == "long":
            tp_price = entry_price + TP_ATR_MULT * atr
            sl_price = entry_price - SL_ATR_MULT * atr
            tp_side = "sell"
            sl_side = "sell"
        else:
            tp_price = entry_price - TP_ATR_MULT * atr
            sl_price = entry_price + SL_ATR_MULT * atr
            tp_side = "buy"
            sl_side = "buy"
        tp = self.orders.place_take_profit(symbol, tp_side, contracts, tp_price)
        sl = self.orders.place_stop_loss(symbol, sl_side, contracts, sl_price)
        return tp, sl

    def close_position(self, symbol: str, side: str, contracts: float):
        close_side = "sell" if side == "long" else "buy"
        return self.orders.place_market_order(symbol, close_side, contracts, reduce_only=True)
