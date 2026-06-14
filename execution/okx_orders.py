# execution/okx_orders.py
import ccxt

class OKXOrders:
    def __init__(self, api_key, secret_key, passphrase, mode="demo"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.mode = mode
        self.exchange = ccxt.okx({
            "apiKey": api_key,
            "secret": secret_key,
            "password": passphrase,
            "enableRateLimit": True,
        })
        if mode == "demo":
            self.exchange.set_sandbox_mode(True)
        else:
            self.exchange.set_sandbox_mode(False)

    def fetch_balance(self):
        return self.exchange.fetch_balance()

    def fetch_positions(self, symbol=None):
        if symbol:
            return self.exchange.fetch_positions([symbol])
        return self.exchange.fetch_positions()

    def fetch_open_orders(self, symbol=None):
        return self.exchange.fetch_open_orders(symbol)

    def cancel_order(self, order_id, symbol):
        return self.exchange.cancel_order(order_id, symbol)

    def set_leverage(self, symbol, leverage, td_mode="isolated"):
        return self.exchange.set_leverage(leverage, symbol, {"tdMode": td_mode})

    def set_margin_mode(self, symbol, td_mode="isolated"):
        instId = symbol.replace("/", "-").replace(":USDT", "-SWAP")
        return self.exchange.private_post_account_set_margin_mode({"instId": instId, "marginMode": td_mode})

    def set_position_mode(self, pos_mode="net_mode"):
        return self.exchange.private_post_account_set_position_mode({"posMode": pos_mode})

    def place_market_order(self, symbol, side, amount, td_mode="isolated", reduce_only=False):
        params = {"tdMode": td_mode}
        if reduce_only:
            params["reduceOnly"] = True
        return self.exchange.create_order(symbol, "market", side, amount, None, params)

    def place_take_profit_market(self, symbol, side, amount, stop_price, td_mode="isolated", reduce_only=True):
        params = {"tdMode": td_mode, "reduceOnly": reduce_only, "stopPrice": stop_price}
        return self.exchange.create_order(symbol, "take_profit_market", side, amount, None, params)

    def place_stop_market(self, symbol, side, amount, stop_price, td_mode="isolated", reduce_only=True):
        params = {"tdMode": td_mode, "reduceOnly": reduce_only, "stopPrice": stop_price}
        return self.exchange.create_order(symbol, "stop_market", side, amount, None, params)
