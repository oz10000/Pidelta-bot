# execution/okx_adapter.py
import time
import logging
from .okx_orders import OKXOrders
from config import MODE, SYMBOL, LEVERAGE, TIME_DIFF_MAX_MS

logger = logging.getLogger(__name__)

class OKXAdapter:
    def __init__(self, api_key, secret_key, passphrase):
        self.orders = OKXOrders(api_key, secret_key, passphrase, MODE)
        self.symbol = SYMBOL

    def health_check(self):
        try:
            bal = self.orders.fetch_balance()
            if bal is None:
                return False, "No balance"
            self.orders.set_margin_mode(self.symbol, "isolated")
            self.orders.set_leverage(self.symbol, LEVERAGE, "isolated")
            self.orders.set_position_mode("net_mode")
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def check_server_time(self):
        server_time = self.orders.exchange.fetch_time()
        local_time = int(time.time() * 1000)
        diff = server_time - local_time
        return diff, abs(diff) <= TIME_DIFF_MAX_MS

    def fetch_position(self):
        positions = self.orders.fetch_positions(self.symbol)
        for pos in positions:
            if float(pos['contracts']) != 0:
                return {
                    "side": pos['side'],
                    "contracts": float(pos['contracts']),
                    "entry_price": float(pos['entryPrice'])
                }
        return None

    def place_market_order(self, side, contracts):
        return self.orders.place_market_order(self.symbol, side, contracts, "isolated", reduce_only=False)

    def place_tp_sl(self, side, contracts, entry_price, tp_pct, sl_pct):
        if side == "long":
            tp_side = "sell"
            tp_price = entry_price * (1 + tp_pct)
            sl_side = "sell"
            sl_price = entry_price * (1 - sl_pct)
        else:
            tp_side = "buy"
            tp_price = entry_price * (1 - tp_pct)
            sl_side = "buy"
            sl_price = entry_price * (1 + sl_pct)
        tp_order = self.orders.place_take_profit_market(self.symbol, tp_side, contracts, tp_price, "isolated", reduce_only=True)
        sl_order = self.orders.place_stop_market(self.symbol, sl_side, contracts, sl_price, "isolated", reduce_only=True)
        return tp_order, sl_order

    def close_position(self, side, contracts):
        close_side = "sell" if side == "long" else "buy"
        return self.orders.place_market_order(self.symbol, close_side, contracts, "isolated", reduce_only=True)
