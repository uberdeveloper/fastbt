from fastbt.Meta import Broker,Status,pre,post
from py5paisa import FivePaisaClient
from py5paisa.order import Order,Exchange,ExchangeSegment,OrderFor,OrderType,OrderValidity,AHPlaced 

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

class FivePaisa(Broker):
    """
    Automated trading class for five paisa
    """
    exchange = {
            'NSE': Exchange.NSE,
            'BSE': Exchange.BSE,
            'MCX': Exchange.MCX
            }

    exchange_segment = {
            'EQ': ExchangeSegment.CASH,
            'FO': ExchangeSegment.DERIVATIVE
            }

    side = {
            'BUY': OrderType.BUY,
            'SELL': OrderType.SELL
            }
    
    def __init__(self, email, password, dob):
        """
        Initialize the broker
        """
        self._email = email
        self._password = password
        self._dob = dob
        super(FivePaisa, self).__init__()
        self.contracts = {}
        print('Hi Five paisa')

    def _shortcuts(self):
        """
        Provides shortcut functions to predefined methods
        This is a just a mapping of the generic class
        methods to the broker specific method
        For shortcuts to work, user should have been authenticated
        """
        self.margins = self.fivepaisa.margin
        self.positions = self.fivepaisa.positions

    def authenticate(self):
        client = FivePaisaClient(email=self._email, passwd=self._password,
                dob=self._dob)
        client.login()
        self.fivepaisa = client
        self._shortcuts()
        
    def _get_instrument_token(self, symbol, exchange='NSE', contracts=None):
        if not(contracts):
            contracts = self.contracts
        return get_instrument_token(contracts=contracts, exchange=exchange, symbol=symbol)

    @post
    def orders(self):
        return self.fivepaisa.order_book()
   
    @pre
    def order_place(self, **kwargs):
       """
       Place an order
       """
       defaults = {
               'exchange': 'NSE',
               'exchange_segment': 'EQ',
               'order_type': 'LIMIT',
               'product': 'MIS',
        }
       for k,v in defaults.items():
           pass
       symbol = kwargs.get('symbol')
       code = int(self.master.get(symbol))
       order = Order(order_type=self.side.get('BUY'), scrip_code=code, quantity=1,exchange=Exchange.NSE)
       print(order.scrip_code, order.quantity, order.order_type)
       print(order)
       self.fivepaisa.place_order(order)
