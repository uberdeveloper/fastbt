import pandas as pd
from fastbt.Meta import Broker
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
        self._login(**kwargs)
        self.fyers = fyersModel.FyersModel()

    @staticmethod
    def get_token(url, key='access_token'):
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
        app_id = kwargs.pop('app_id')
        app_secret = kwargs.pop('app_secret')
        username = kwargs.pop('username')
        password = kwargs.pop('password')
        dob = kwargs.pop('dob')
        app_session = accessToken.SessionModel(app_id, app_secret)
        response = app_session.auth()
        auth_code = response['data']['authorization_code']
        app_session.set_token(auth_code)
        url = app_session.generate_token()
        # Initiating the driver to log in
        driver = webdriver.Chrome()
        driver.get(url)
        # Auto login
        login_form = WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.ID, "myForm")))
        login_form.find_elements_by_id('fyers_id')[0].send_keys(username)
        login_form.find_elements_by_id('password')[0].send_keys(password)
        login_form.find_elements_by_name('panOrDob')[1].click()
        login_form.find_elements_by_id('dob')[0].send_keys(dob)
        driver.find_element_by_xpath('//button').click()
        time.sleep(2)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "email")))
        url = driver.current_url
        self._token = self.get_token(url)
        driver.close()


    def _shortcuts(self):
        self.profile = partial(self.fyers.get_profile, token=self._token)
        self.holdings = partial(self.fyers.holdings, token=self._token)
        self.orders = partial(self.fyers.orders, token=self._token)
        self.trades = partial(self.fyers.tradebook, token=self._token)
        self.positions = partial(self.fyers.positions, token=self._token)





