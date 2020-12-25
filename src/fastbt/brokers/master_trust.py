import os
import requests
from fastbt.Meta import Broker,Status,pre,post
from requests_oauthlib import OAuth2Session

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_authorization_url():
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    authorization_url, _state = oauth.authorization_url(authorization_base_url, access_type="authorization_code")
    return authorization_url

def fetch_all_contracts(exchanges=['NSE','NFO']):
    """
    Fetch all contracts for the given list of exchanges
    exchanges
        exchanges as a list
    """
    url = 'https://masterswift.mastertrust.co.in/api/v2/contracts.json?exchanges={exc}'
    # All contracts are stored as dictionary keys
    contracts = {}
    for e in exchanges:
        url2 = url.format(exc=e)
        req = requests.get(url2).json()
        for k,v in req.items():
            for c in v:
                symbol = c['trading_symbol']
                code = c['code']
                contracts[f"{e}:{symbol}"] = code
    return contracts

def get_instrument_token(contracts, exchange, symbol):
    """
    Fetch the instrument token
    contracts
        the contracts master as a dictionary
    exchange
        exchange to look up for
    symbol
        symbol to look up for
    """
    return contracts.get(f"{exchange}:{symbol}") 

class MasterTrust(Broker):
    """
    Automated Trading class
    """
    def __init__(self, client_id, password,
                PIN, secret, exchange='NSE',
                product='MIS', token_file='token.tok'):
        self._client_id = client_id 
        self._password = password
        self._pin = PIN
        self._secret = secret
        self.exchange = exchange
        self.product = product
        self._store_access_token = True        
        self._access_token = None
        self.token_file = token_file
        self.base_url = 'https://masterswift-beta.mastertrust.co.in'
        self.authorization_base_url = f"{self.base_url}/oauth2/auth"
        self.token_url = f"{self.base_url}/oauth2/token"
        super(MasterTrust, self).__init__()
        try:
            with open(self.token_file, 'r') as f:
                access_token = f.read()
            self._access_token = access_token
        except Exception as e:
            print('Token not found',e)

        self._headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self._access_token}',
            'Cache-Control': 'no-cache'
        }

    @property
    def headers(self):
        return self._headers

    @property
    def access_token(self):
        return self._access_token

    @property
    def client_id(self):
        return self._client_id

    def get_authorization_url(self, client_id='APIUSER', redirect_uri='http://127.0.0.1/',
            scope=['orders']):
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        authorization_url, _state = oauth.authorization_url(self.authorization_base_url,
                access_type="authorization_code")
        return authorization_url

    def get_access_token(self, url, redirect_uri='http://127.0.0.1/',
            scope=['orders']):
        # to make oauth2 work with http
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        oauth = OAuth2Session('APIUSER',redirect_uri=redirect_uri, scope=scope)
        token = oauth.fetch_token(self.token_url, authorization_response=url, client_secret=self._secret)
        access_token = token['access_token']
        self._access_token = access_token
        with open(self.token_file, "w") as f:
            f.write(access_token)
        return access_token
            
    def _shortcuts(self):
        """
        Provides shortcuts to master trust function
        """
        pass

    def authenticate(self, force=False):
        """
        Authenticates a session if access token is already
        available by looking at the token.tok file.
        In case authentication fails, try a fresh login
        force
            Force an authentication even if tokens exists
        """
        try:
            if not(force):
                with open(self.token_file, 'r') as f:
                    access_token = f.read()
                self._access_token = access_token
            else:
                login_url = self._login()
                access_token = self.get_access_token(login_url)
        except Exception as e:
            print(e)
            login_url = self._login()
            access_token = self.get_access_token(login_url)

    def _login(self):
        import time
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)
        url = self.get_authorization_url()
        driver.get(url)
        time.sleep(2)
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-container")))
        driver.find_element_by_name('login_id').send_keys(self._client_id)
        driver.find_element_by_name('password').send_keys(self._password)
        driver.find_element_by_xpath('//button[@type="submit"]').click()
        time.sleep(2)
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-container")))
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(self._pin)
        driver.find_element_by_xpath('//button[@type="submit"]').click() 
        time.sleep(2)
        current_url = driver.current_url
        driver.close()
        return current_url 


    def _response(self, response, full=False):
        """
        response
            response is the raw response from broker
        full
            if True, the entire json response is returned
            useful for debugging purposes and getting extra information
        """
        try:
            resp = response.json()
            if full or (resp.get('status') == 'error'):
                return resp
            else:
                return resp['data']
        except:
            return {}
    
    def profile(self):
        """
        Get the profile for the user
        """
        url = f"{self.base_url}/api/v1/user/profile"
        payload = {'client_id': self.client_id} 
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp) 

    @post
    def positions(self):
        """
        Return only the positions for the day
        """
        url = f"{self.base_url}/api/v1/positions" 
        payload = {'client_id': self.client_id, 'type':'live'}
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp)

    @post
    def completed_orders(self):
        """
        Return the completed orders for the day
        """
        url = f"{self.base_url}/api/v1/orders" 
        payload = {'client_id': self.client_id, 'type':'completed'}
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp).get('orders', [])

    @post
    def pending_orders(self):
        """
        Return the completed orders for the day
        """
        url = f"{self.base_url}/api/v1/orders" 
        payload = {'client_id': self.client_id, 'type':'pending'}
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp).get('orders', [])

    def orders(self):
        """
        Return the entire orderbook for the day including
        completed and pending orders
        """
        pending = self.pending_orders()
        completed = self.completed_orders()
        pending.extend(completed) 
        return pending 

    def trades(self):
        """
        Return the tradebook for the day
        """
        url = f"{self.base_url}/api/v1/trades" 
        payload = {'client_id': self.client_id}
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp).get('trades', [])


    def realized_mtm(self):
        """
        Get the realized MTM
        """
        positions = self.positions()
        if len(positions)>0:
            return sum([float(p['realized_mtm']) for p in positions])
        else:
            # Return 0 in case of no transactions
            return 0

    def unrealized_mtm(self):
        """
        Get the unrealized MTM
        """
        positions = self.positions()
        if len(positions)==0:
            collect = {p['symbol']:0 for p in positions}
        else:
            collect = {}
            for p in positions:
                if p['net_quantity'] > 0:
                    collect[p['symbol']] = (p['ltp']-(-p['net_amount']/p['net_quantity']))*p['net_quantity']-p['realized_mtm']
                elif p['net_quantity'] < 0:
                    collect[p['symbol']] = (p['ltp']-(-p['net_amount']/p['net_quantity']))*p['net_quantity']-p['realized_mtm']
                else:
                    collect[p['symbol']] = 0
        return sum(list(collect.values()))

    def mtm(self, mode=None):
        """
        Get the mtm
        """
        if mode == 'realized':
            return self.realized_mtm()
        elif mode == 'unrealized':
            return self.unrealized_mtm()
        else:
            return self.realized_mtm() + self.unrealized_mtm()

    def net_qty(self, symbol):
        """
        Get the net quantity
        """
        positions = self.positions()
        if symbol is None:
            return {p['symbol']:p['net_quantity'] for p in positions}
        else:
            for p in positions:
                if p['symbol'] == symbol:
                    return p['net_quantity']
            return 0

    def order_place(self, **kwargs):
        """
        Place an order
        """
        url = f"{self.base_url}/api/v1/orders" 
        payload = kwargs.copy() 
        resp = requests.post(url, headers=self.headers, params=payload)
        return self._response(resp)

    def order_modify(self, **kwargs):
        """
        Place an order
        """
        url = f"{self.base_url}/api/v1/orders" 
        payload = kwargs.copy() 
        resp = requests.put(url, headers=self.headers, params=payload)
        return self._response(resp)

    def order_cancel(self, **kwargs):
        """
        Place an order
        """
        url = f"{self.base_url}/api/v1/orders" 
        payload = kwargs.copy() 
        resp = requests.delete(url, headers=self.headers, params=payload)
        return self._response(resp)

    def place_bracket_order(self, **kwargs):
        """
        Place a bracket order
        """
        url = f"{self.base_url}/api/v1/orders/bracket" 
        payload = kwargs.copy() 
        resp = requests.post(url, headers=self.headers, params=payload)
        return self._response(resp)

    def modify_bracket_order(self,**kwargs):
        """
        Modify an existing bracket order
        """
        url = f"{self.base_url}/api/v1/orders/bracket/"
        print(url)
        payload = kwargs.copy() 
        resp = requests.post(url, headers=self.headers, params=payload)
        print('resp', resp)
        return resp.json()
    
    def exit_bracket_order(self, **kwargs):
        """
        Exit at existing bracket order
        """
        url = f"{self.base_url}/api/v1/orders/bracket/"
        payload = kwargs.copy() 
        resp = requests.delete(url, headers=self.headers, params=payload)
        return resp.json()






