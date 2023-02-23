from fastbt.Meta import Broker, pre, post
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from fyers_api import accessToken, fyersModel
from functools import partial


class Fyers(Broker):
    """
    Automated Trading class
    """

    def __init__(self):
        """
        To be implemented
        """
        super(Fyers, self).__init__()

    def authenticate(self, **kwargs):
        """
        Fyers authentication to be implemented
        """
        try:
            with open("fyers-token.tok", "r") as f:
                self._token = f.read()
            self.fyers = fyersModel.FyersModel()
            self._shortcuts()
            code = self.fyers.get_profile(self._token)["code"]
            if code == 401:
                print("Authentication failure, logging in again")
                self._login(**kwargs)
                self.fyers = fyersModel.FyersModel()
                self._shortcuts()
        except Exception as E:
            print("Into Exception", E)
            self._login(**kwargs)
            self.fyers = fyersModel.FyersModel()
            self._shortcuts()

    @staticmethod
    def get_token(url, key="access_token"):
        """
        Get the access token from the url
        url
            the url returned
        key
            the key to fetch
        Note
        -----
        By default, it is expected that when the query string
        is parsed, it would have a parameter with the name
        **access_token** and using the parse function this would
        fetch a list with a single element
        """
        import urllib.parse

        parsed = urllib.parse.urlparse(url)
        return urllib.parse.parse_qs(parsed.query)[key][0]

    def _login(self, **kwargs):
        import time

        app_id = kwargs.pop("app_id")
        app_secret = kwargs.pop("app_secret")
        username = kwargs.pop("username")
        password = kwargs.pop("password")
        dob = kwargs.pop("dob")
        app_session = accessToken.SessionModel(app_id, app_secret)
        response = app_session.auth()
        auth_code = response["data"]["authorization_code"]
        app_session.set_token(auth_code)
        url = app_session.generate_token()
        # Initiating the driver to log in
        driver = webdriver.Chrome()
        driver.get(url)
        # Auto login
        login_form = WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.ID, "myForm"))
        )
        login_form.find_elements_by_id("fyers_id")[0].send_keys(username)
        login_form.find_elements_by_id("password")[0].send_keys(password)
        login_form.find_elements_by_class_name("login-dob")[0].click()
        login_form.find_elements_by_id("dob")[0].send_keys(dob)
        driver.find_element_by_id("btn_id").click()
        time.sleep(2)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        url = driver.current_url
        token = self.get_token(url)
        self._token = token
        with open("fyers-token.tok", "w") as f:
            f.write(token)
        driver.close()

    def _shortcuts(self):
        self.holdings = partial(self.fyers.holdings, token=self._token)
        self.trades = partial(self.fyers.tradebook, token=self._token)
        self.positions = partial(self.fyers.positions, token=self._token)

    def _fetch(self, data):
        """
        Fetch the necessary data from the request
        data
            the data dictionary returned from the request
        returns None in case of other status codes
        """
        if data["code"] in [200, 201]:
            return data["data"]
        else:
            return None

    @post
    def profile(self):
        prof = self.fyers.get_profile(self._token)
        prof = self._fetch(prof)
        if prof:
            prof["result"]
        else:
            return {}

    @pre
    def order_place(self, **kwargs):
        """
        Place an order
        """
        return self.fyers.place_orders(token=self._token, data=kwargs)

    def order_cancel(self, order_id):
        return self.fyers.delete_orders(token=self._token, data={"id": order_id})

    @post
    def orders(self):
        ords = self.fyers.orders(token=self._token)
        ords = self._fetch(ords)
        if ords:
            all_orders = ords["orderBook"]
            for o in all_orders:
                if o["side"] == 1:
                    o["side"] = "BUY"
                elif o["side"] == -1:
                    o["side"] = "SELL"
            # update status
            status_map = {
                1: "CANCELED",
                2: "COMPLETE",
                4: "PENDING",
                5: "REJECTED",
                6: "PENDING",
            }
            for o in all_orders:
                o["status"] = status_map.get(o["status"], "PENDING")
            return all_orders
        else:
            return []
