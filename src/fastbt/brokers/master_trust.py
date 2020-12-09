import pandas as pd
from fastbt.Meta import Broker,Status,pre,post

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MasterTrust(Broker):
    """
    Automated Trading class
    """
    def __init__(self, username, password,
                PIN, exchange='NSE',
                product='MIS'):
        self._username = user_id
        self._password = password
        self._pin = PIN
        self.exchange = exchange
        self.product = product
        self._store_access_token = True        
        super(MasterTrust, self).__init__()

    def _shortcuts(self):
        """
        Provides shortcuts to master trust function
        """
        pass

    def authenticate(self):
        """
        Authenticates a session if access token is already
        available by looking at the token.tok file.
        In case authentication fails, try a fresh login
        """
        pass
    
    def _login(self):
        pass
