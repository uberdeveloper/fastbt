import pandas as pd
import pyotp
from fastbt.Meta import Broker, pre, post

from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from kiteconnect.exceptions import (
    TokenException,
)


def get_key(url, key="request_token"):
    """
    Get the required key from the query parameter
    """
    from urllib.parse import parse_qs, urlparse

    req = urlparse(url)
    key = parse_qs(req.query).get(key)
    if key is None:
        return None
    else:
        return key[0]


class Zerodha(Broker):
    """
    Automated Trading class
    """

    def __init__(
        self,
        api_key,
        secret,
        user_id,
        password,
        PIN,
        exchange="NSE",
        product="MIS",
        totp=None,
        is_pin=False,
    ):
        self._api_key = api_key
        self._secret = secret
        self._user_id = user_id
        self._password = password
        self._pin = PIN
        self._totp = totp
        self.is_pin = is_pin
        self.exchange = exchange
        self.product = product
        self._store_access_token = True
        super(Zerodha, self).__init__()

    @property
    def isNilPositions(self):
        """
        return True if there are no open positions
        else return False
        """
        temp = pd.DataFrame(self.positions()["net"])
        if temp.quantity.abs().sum() == 0:
            return True
        else:
            return False

    @property
    def isNilPositionsDay(self):
        """
        return True if there are no open positions for
        the day else return False
        """
        temp = pd.DataFrame(self.positions()["day"])
        if temp.quantity.abs().sum() == 0:
            return True
        else:
            return False

    @property
    def isNilOrders(self):
        """
        return True if there are no pending orders
        else return False
        """
        pending = [o for o in self.orders() if o.get("status", "PENDING") == "PENDING"]
        if len(pending) == 0:
            return True
        else:
            return False

    def cancel_all_orders(self, retries=5):
        """
        Cancel all existing orders
        """
        for o in self.orders():
            try:
                if o["status"] == "PENDING":
                    self.order_cancel(
                        variety=o["variety"],
                        order_id=o["order_id"],
                        parent_order_id=o["parent_order_id"],
                    )
            except Exception as e:
                print(e)
        i = 0
        while not (self.isNilOrders):
            print("Into the loop")
            i += 1
            for o in self.orders():
                try:
                    if o["status"] == "PENDING":
                        self.order_cancel(
                            variety=o["variety"],
                            order_id=o["order_id"],
                            parent_order_id=o["parent_order_id"],
                        )
                except Exception as e:
                    print(e)
            if i > retries:
                print("Breaking out of loop without canceling all orders")
                break

    def _shortcuts(self):
        """
        Provides shortcuts to kite functions by mapping functions.
        Instead of calling at.kite.quote, you would directly call
        at.quote
        Note
        -----
        1) Kite functions are initialized only after authentication
        1) Not all functions are supported
        """
        self.margins = self.kite.margins
        self.profile = self.kite.profile
        self.ltp = self.kite.ltp
        self.quote = self.kite.quote
        self.ohlc = self.kite.ohlc
        self.trades = self.kite.trades
        self.holdings = self.kite.holdings
        self._sides = {"BUY": "SELL", "SELL": "BUY"}

    def authenticate(self):
        """
        Authenticates a kite session if access token is already available
        Looks up token in token.tok file
        Useful for reconnecting instead of logging in again
        """
        try:
            self.kite = KiteConnect(api_key=self._api_key)
            with open("token.tok") as f:
                access_token = f.read()
            self.kite.set_access_token(access_token)
            self.kite.profile()
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )
            self._shortcuts()
        except TokenException:
            print("Into Exception")
            self._login()
            self._shortcuts()
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )
        except Exception:
            print("Unknown Exception")
            self._login()
            self._shortcuts()
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )

    def _login(self):
        import time

        self.kite = KiteConnect(api_key=self._api_key)
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=options)
        driver.get(self.kite.login_url())
        login_form = WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "login-form"))
        )
        login_form.find_elements_by_tag_name("input")[0].send_keys(self._user_id)
        login_form.find_elements_by_tag_name("input")[1].send_keys(self._password)
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "button-orange"))
        )
        driver.find_element_by_xpath('//button[@type="submit"]').click()
        totp_pass = pyotp.TOTP(self._totp).now()
        twofa_pass = self._pin if self.is_pin is True else totp_pass
        twofa_form = WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "twofa-form"))
        )
        twofa_form.find_elements_by_tag_name("input")[0].send_keys(twofa_pass)
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "button-orange"))
        )
        driver.find_element_by_xpath('//button[@type="submit"]').click()
        time.sleep(2)
        token = get_key(driver.current_url)
        access = self.kite.generate_session(
            request_token=token, api_secret=self._secret
        )
        self.kite.set_access_token(access["access_token"])
        with open("token.tok", "w") as f:
            f.write(access["access_token"])
        driver.close()

    def get_all_orders_and_positions(self, positions="day"):
        """
        Get the summary of all orders and positions
        """
        pos = pd.DataFrame(self.positions()[positions])
        orders = pd.DataFrame(self.orders())
        orders["qty"] = orders.eval("pending_quantity-cancelled_quantity")
        orders["typ"] = "orders"
        pos["qty"] = pos["quantity"].abs()
        pos["transaction_type"] = ["SELL" if qty < 0 else "BUY" for qty in pos.quantity]
        pos["typ"] = "positions"
        cols = ["tradingsymbol", "transaction_type", "qty", "typ"]
        return pd.concat([pos, orders], sort=False)[cols]

    def uncovered(self):
        """
        Return the list of uncovered positions
        A position is considered unconvered if there is no matching
        stop loss or target order.
        """
        pass

    def get_order_type(self, price, ltp, order):
        if order == "BUY":
            return "LIMIT" if price < ltp else "SL"
        elif order == "SELL":
            return "LIMIT" if price > ltp else "SL"

    @post
    def orders(self):
        status_map = {
            "OPEN": "PENDING",
            "COMPLETE": "COMPLETE",
            "CANCELLED": "CANCELED",
            "CANCELLED AMO": "CANCELED",
            "REJECTED": "REJECTED",
            "MODIFY_PENDING": "PENDING",
            "OPEN_PENDING": "PENDING",
            "CANCEL_PENDING": "PENDING",
            "AMO_REQ_RECEIVED": "PENDING",
            "TRIGGER_PENDING": "PENDING",
        }
        ords = self.kite.orders()
        # Update status
        for o in ords:
            o["status"] = status_map.get(o["status"], "PENDING")
        return ords

    @post
    def positions(self):
        """
        Return only the positions for the day
        """
        pos = self.kite.positions()["day"]
        for p in pos:
            if p["quantity"] > 0:
                p["side"] = "BUY"
            else:
                p["side"] = "SELL"
        return pos

    @pre
    def order_place(self, **kwargs):
        """
        Place an order
        """
        return self.kite.place_order(**kwargs)

    def order_cancel(self, order_id, variety="regular", parent_order_id=None):
        """
        Cancel an existing order
        """
        return self.kite.cancel_order(
            variety=variety, order_id=order_id, parent_order_id=parent_order_id
        )

    def order_modify(self, order_id, variety="regular", **kwargs):
        """
        Modify an existing order
        Note
        ----
        This is just a basic implementation
        So, all changes must be passed as keyword arguments
        """
        return self.kite.modify_order(order_id=order_id, variety=variety, **kwargs)

    def _custom_orders(self, data, **kwargs):
        """
        Generate custom orders.
        This is for customized usage
        data
            dataframe with the following columns
            open, symbol, price, side, quantity and stop_loss
        kwargs
            keyword arguments to be included in each order
        """
        cols = ["open", "symbol", "price", "quantity", "side", "stop_loss"]
        data = data[cols].to_dict(orient="records")
        exchange = kwargs.get("exchange", "NSE")
        sym = ["{e}:{s}".format(e=exchange, s=x["symbol"]) for x in data]
        ltps = self.ltp(sym)
        ltps = {k[4:]: v["last_price"] for k, v in ltps.items()}
        all_orders = []
        replace = {
            "symbol": "tradingsymbol",
            "side": "transaction_type",
        }
        for d in data:
            dct = d.copy()
            del dct["stop_loss"]
            ltp = ltps.get(d["symbol"])
            order_type = self.get_order_type(
                price=dct["price"], ltp=ltp, order=dct["side"]
            )
            dct["order_type"] = order_type
            dct["price"] = round(dct["price"], 2)
            # TO DO: Trigger greater if price is low to correct
            if order_type == "SL":
                dct["trigger_price"] = round(dct["open"] - 0.05, 2)
            dct.update(kwargs)
            del dct["open"]  # Since its no longer needed
            all_orders.append(self.rename(dct, keys=replace))
        # Second leg for covering orders
        for d in data:
            try:
                dct = d.copy()
                del dct["open"]  # Since this is not needed here
                ltp = ltps.get(dct["symbol"])
                dct["side"] = self._sides[dct["side"]]
                dct["stop_loss"] = round(dct["stop_loss"], 2)
                order_type = self.get_order_type(
                    price=dct["stop_loss"], ltp=ltp, order=dct["side"]
                )
                if order_type == "SL":
                    order_type = "SL-M"
                dct["order_type"] = order_type
                dct.update(kwargs)
                replace.update({"stop_loss": "trigger_price"})
                all_orders.append(self.rename(dct, keys=replace))
            except Exception as e:
                print(e, self.rename(dct))
        return all_orders

    def _create_stop(self, **kwargs):
        sl = self._create_stop_loss_orders(percent=3, **kwargs)
        orders = []
        for s in sl:
            try:
                dct = s.copy()
                dct.update(
                    {
                        "exchange": "NSE",
                        "product": "MIS",
                        "validity": "DAY",
                        "variety": "regular",
                    }
                )
                dct["trigger_price"] = s["price"]
                symbol = "{e}:{sym}".format(e="NSE", sym=s["symbol"])
                ltp = self.ltp(symbol)[symbol]["last_price"]
                order_type = self.get_order_type(s["price"], ltp, s["side"])
                dct["order_type"] = order_type
                orders.append(dct)
            except Exception as e:
                print(e)
        return orders

    def cover_all(self, **kwargs):
        """
        Place a stop loss for all uncovered orders
        """
        orders = self._create_stop(**kwargs)
        for o in orders:
            try:
                print(self.order_place(**o))
            except Exception as e:
                print(e)

    def close_all_positions(self, **kwargs):
        """
        Close all existing positions
        """
        positions = self.positions()
        if kwargs:
            positions = self.dict_filter(positions, **kwargs)
        if len(positions) > 0:
            for position in positions:
                qty = abs(position["quantity"])
                symbol = position["symbol"]
                side = self._sides[position["side"]]
                exchange = position["exchange"]
                product = position["product"]
                if qty > 0:
                    try:
                        self.order_place(
                            symbol=symbol,
                            quantity=qty,
                            order_type="MARKET",
                            side=side,
                            variety="regular",
                            exchange=exchange,
                            product=product,
                        )
                    except Exception as e:
                        print(e)

    def get_instrument_map(
        self, exchange="NSE", key="tradingsymbol", value="instrument_token"
    ):
        """
        Get the instrument map as a dictionary
        exchange
            exchange to fetch the symbols and tokens
        key
            dictionary key to be used as the key
            in the output
        value
            dictionary value to be used as the value
            in the output
        Note
        -----
        1) The instrument map is returned as a dictionary with
        key as the symbol and instrument token as value
        """
        instruments = self.kite.instruments(exchange=exchange)
        inst_map = {inst[key]: inst[value] for inst in instruments}
        return inst_map
