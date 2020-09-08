from fastbt.Meta import Broker,Status,pre,post
from py5paisa import FivePaisaClient

class FivePaisa(Broker):
    """
    Automated trading class for five paisa
    """
    def __init__(self, email, password, dob):
        """
        Initialize the broker
        """
        self._email = email
        self._password = password
        self._dob = dob
        super(FivePaisa, self).__init__()
        print('Hi Five paisa')


    def _shortcuts(self):
        """
        Provides shortcut functions to predefined methods
        This is a just a mapping of the generic class
        methods to the broker specific method
        For shortcuts to work, user should have been authenticated
        """
        self.margins = self.fivepaisa.margin
        self.orders = self.fivepaisa.order_book
        self.positions = self.fivepaisa.positions

    def authenticate(self):
        client = FivePaisaClient(email=self._email, passwd=self._password,
                dob=self._dob)
        client.login()
        self.fivepaisa = client
        self._shortcuts()
