# execution/okx_orders.py
import ccxt

class OKXOrders:
    def __init__(self, api_key: str, secret_key: str, passphrase: str, mode: str = "demo"):
        self.exchange = ccxt.okx({
            "apiKey": api_key,
            "secret": secret_key,
            "password": passphrase,
            "enableRateLimit": True,
        })
        # Configura el modo de trading (demo o real)
        if mode == "demo":
            self.exchange.set_sandbox_mode(True)
        else:
            self.exchange.set_sandbox_mode(False)

    def fetch_balance(self):
        return self.exchange.fetch_balance()

    def fetch_positions(self, symbols=None):
        if symbols:
            return self.exchange.fetch_positions(symbols)
        return self.exchange.fetch_positions()

    def fetch_open_orders(self, symbol=None):
        return self.exchange.fetch_open_orders(symbol)

    def cancel_all_orders(self, symbol):
        orders = self.fetch_open_orders(symbol)
        for o in orders:
            self.exchange.cancel_order(o['id'], symbol)

    def set_margin_and_leverage(self, symbol: str, leverage: int, td_mode: str = "isolated"):
        """Configura el modo de margen y el apalancamiento para un símbolo."""
        instId = symbol.replace("/", "-").replace(":USDT", "-SWAP")
        self.exchange.private_post_account_set_margin_mode({"instId": instId, "marginMode": td_mode})
        self.exchange.set_leverage(leverage, symbol, {"tdMode": td_mode})
        self.exchange.private_post_account_set_position_mode({"posMode": "net_mode"}) # Usamos net_mode para simplificar

    def place_market_order(self, symbol: str, side: str, contracts: float, reduce_only: bool = False):
        """Coloca una orden de mercado."""
        params = {"tdMode": "isolated"}
        if reduce_only:
            params["reduceOnly"] = True
        return self.exchange.create_order(symbol, "market", side, contracts, None, params)

    def place_take_profit(self, symbol: str, side: str, contracts: float, stop_price: float, reduce_only: bool = True):
        """Coloca una orden condicional de Take Profit (mercado)."""
        params = {"tdMode": "isolated", "reduceOnly": reduce_only, "stopPrice": stop_price}
        return self.exchange.create_order(symbol, "take_profit_market", side, contracts, None, params)

    def place_stop_loss(self, symbol: str, side: str, contracts: float, stop_price: float, reduce_only: bool = True):
        """Coloca una orden condicional de Stop Loss (mercado)."""
        params = {"tdMode": "isolated", "reduceOnly": reduce_only, "stopPrice": stop_price}
        return self.exchange.create_order(symbol, "stop_market", side, contracts, None, params)
