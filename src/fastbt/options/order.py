from dataclasses import dataclass
from typing import Optional
import uuid
import pendulum

@dataclass
class Order:
    symbol:str
    side:str
    quantity:int=1
    internal_id:Optional[str] = None
    timestamp:Optional[pendulum.datetime] = None
    order_type:str = 'MARKET' 
    broker_timestamp:Optional[pendulum.datetime] = None
    exchange_timestamp:Optional[pendulum.datetime] = None
    order_id:Optional[str] = None
    exchange_order_id:Optional[str] = None
    price:Optional[float] = None
    trigger_price:float = 0.0
    average_price:Optional[float] = None
    pending_quantity:Optional[int] = None
    filled_quantity:Optional[int] = None
    cancelled_quantity:Optional[int] = None
    disclosed_quantity:Optional[int] = None
    validity:str = 'DAY'
    status:Optional [str] = None

    def __post_init__(self):
        self.internal_id = uuid.uuid4().hex
        self.timestamp = pendulum.now()


    

