import requests
import asyncio
import aiohttp
import logging
import time
import json
from datetime import datetime as dt
from datetime import timezone



HEADERS = {"accept": "application/json"}

LOGGER_FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=LOGGER_FORMAT, datefmt="[%H:%M:%S]")
log = logging.getLogger()
log.setLevel(logging.INFO)




def get_index_price(asset = "ETH"):
    index_price_url = f"https://api.aevo.xyz/index?asset={asset}"

    index_price_response = requests.get(index_price_url, headers=HEADERS)
    index_price = float(json.loads(index_price_response.text)["price"])

    return index_price



# requests and returns a dictionary of all market data for asset (does not include bids/asks, only mark prices)
def get_markets(asset = "ETH", remove_inactive=True):
    markets_url = f"https://api.aevo.xyz/markets?asset={asset}&instrument_type=OPTION"

    markets_response = requests.get(markets_url, headers=HEADERS)
    
    if not remove_inactive:
        return json.loads(markets_response)

    markets = []
    for market in json.loads(markets_response.text):
        if market["is_active"]:
            markets.append(market)
        
    return markets
    

    

# takes get_markets http response and formats into a 2D list which is returned (does not include bids/asks, only mark prices)
def get_markets_simple(markets_arg):
    # ["aevo", [put mark, call mark, strike, expiry (DD:MM:YY), index]...[]]

    index_price = 0.0
    option_type = ""
    expiry = 0.0
    strike = 0.0
    markets_simple = ["aevo"]
    markets_simple_element = [-1, -1, strike, expiry, index_price]


    for market in markets_arg:
        index_price = float(market["index_price"])
        option_type = market["option_type"]
        expiry = float(market["expiry"])
        strike = float(market["strike"])

        if option_type == "put":
            markets_simple_element = [float(market["mark_price"]), -1, strike, expiry, index_price]

            for m in markets_arg:
                if m["strike"] == strike and m["expiry"] == expiry and m["option_type"] == "call": 
                    markets_simple_element[1] = float(m["mark_price"])
                    
            markets_simple.append(markets_simple_element)

            continue

        if option_type == "call":
            no_match = True
            for m in markets_arg:
                if m["strike"] == strike and m["expiry"] == expiry and m["option_type"] == "put":
                    no_match = False
            if no_match:
                markets_simple.append([-1, float(market["mark_price"]), strike, expiry, index_price])

    # using enumerate because regular iterating and reassignment caused issues (idk why)
    for i in range(1, len(markets_simple)):
        markets_simple[i][3] = dt.fromtimestamp(markets_simple[i][3] / 1000000000, timezone.utc).strftime('%d%b%y').upper()

    return markets_simple



# requests one orderbook
async def get_orderbook(market, loop, limit_sem):
    instrument_name = market["instrument_name"]

    async with limit_sem:
        await asyncio.sleep(0.5)

        async with aiohttp.ClientSession(loop=loop) as session:
            async with session.get(f"https://api.aevo.xyz/orderbook?instrument_name={instrument_name}") as response:
                status = response.status
                log.info(f"Aevo orderbook request status: {status}")

                return await response.text()


# takes markets and requests orderbook for each instrument_name in markets then returns list of all orderbooks
# orderbooks[n]["bids"] and ["asks]: Array of 3 elements, price in USD, contract amount, and IV respectively.
async def get_orderbooks(markets_arg, loop):
    # limit seems to be 20 at a time followed by pause
    limit_sem = asyncio.Semaphore(20)
    orderbooks_response = []
    orderbooks = []

    responses = await asyncio.gather(*[get_orderbook(market, loop, limit_sem) for market in markets_arg])

    for response in responses:
        orderbooks.append(json.loads(response))

    return orderbooks




def trim_orderbooks(orderbooks_arg):
    orderbooks = []
    for orderbook in orderbooks_arg:
        if len(orderbook["bids"]) > 0 or len(orderbook["asks"]) > 0:
            orderbooks.append(orderbook)

    return orderbooks



# takes orderbooks as argument and returns a simplified 2D list: ["aevo", [put_bid, put_ask, call_bid, call_ask, strike, expiry (DD:MM:YY), index]...[]]
def get_orderbooks_simple(orderbooks_arg):
    orderbooks = trim_orderbooks(orderbooks_arg)
    
    orderbooks_simple = ["aevo"]
    index_price = get_index_price()

    for orderbook in orderbooks:
        instrument_name = orderbook["instrument_name"][:-2]
        strike = float(instrument_name[instrument_name.rfind("-") + 1:])
        option_type = orderbook["instrument_name"][-1:]
        expiry = instrument_name[instrument_name.find("-") + 1: instrument_name.rfind("-")]

        if option_type == "P":
            orderbooks_simple_element = [float(orderbook["bids"][0][0]) if len(orderbook["bids"]) > 0 else -1, float(orderbook["asks"][0][0]) if len(orderbook["asks"]) > 0 else -1, -1, -1, strike, expiry, index_price]

            for o in orderbooks:
                if o["instrument_name"] == instrument_name + "-C":
                    orderbooks_simple_element[2] = float(o["bids"][0][0]) if len(o["bids"]) > 0 else -1
                    orderbooks_simple_element[3] = float(o["asks"][0][0]) if len(o["asks"]) > 0 else -1

            if orderbooks_simple_element[0] > 0 or orderbooks_simple_element[1] > 0 or orderbooks_simple_element[2] > 0 or orderbooks_simple_element[3] > 0:
                orderbooks_simple.append(orderbooks_simple_element)

            continue

        if option_type == "C" and (len(orderbook["bids"]) > 0 or len(orderbook["asks"]) > 0):
            no_match = True
            for o in orderbooks:
                if o["instrument_name"] == instrument_name + "-P":
                    no_match = False
            if no_match:
                orderbooks_simple.append([-1, -1, float(o["bids"][0][0]) if len(o["bids"]) > 0 else -1, float(o["asks"][0][0]) if len(o["asks"]) > 0 else -1, strike, expiry, index_price])


    return orderbooks_simple




class Aevo:
    def __init__(self):
        loop = asyncio.new_event_loop()
        self.index_price = get_index_price()
        self.markets = get_markets()
        self.markets_simple = get_markets_simple(self.markets)
        self.orderbooks = loop.run_until_complete(get_orderbooks(self.markets, loop))
        loop.close()
        self.orderbooks_simple = get_orderbooks_simple(self.orderbooks)
