import requests
import json
from datetime import datetime as dt
import logging
import asyncio
import aiohttp




HEADERS = {
    "accept": "application/json",
    "content-type": "application/json"
}

LOGGER_FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=LOGGER_FORMAT, datefmt="[%H:%M:%S]")
log = logging.getLogger()
log.setLevel(logging.INFO)




def get_index_price():
    pass



# requests and returns a dictionary of all instruments for a given currency and instrument type
def get_instruments(currency = "ETH", expired = "False", instrument_type = "option"):
    instruments_url = "https://api.lyra.finance/public/get_instruments"

    payload = {
        "expired": False,
        "instrument_type": "option",
        "currency": "ETH"
    }

    instruments_response = requests.post(instruments_url, json=payload, headers=HEADERS)
    instruments = json.loads(instruments_response.text)

    return instruments["result"]




async def get_orderbook(instrument, loop, limit_sem):
    instrument_name = instrument["instrument_name"]
    ticker_url = "https://api.lyra.finance/public/get_ticker"
    payload = { "instrument_name": instrument_name }

    async with limit_sem:
        await asyncio.sleep(0.5)

        async with aiohttp.ClientSession(loop=loop) as session:
            async with session.post(ticker_url, json=payload, headers=HEADERS) as response:
                status = response.status
                log.info(f"Lyra orderbook request status: {status}")

                return await response.text()




# requests and returns all ticker data for all instruments (named "orderbooks" for the sake of consistency)
async def get_orderbooks(instruments, loop):
    # rate limit seems not to be an issue, can adjust at a later date if necessary
    limit_sem = asyncio.Semaphore(1000) 
    orderbooks_response = []
    orderbooks = []

    responses = await asyncio.gather(*[get_orderbook(instrument, loop, limit_sem) for instrument in instruments])

    for response in responses:
        orderbooks.append(json.loads(response)["result"])

    return orderbooks




def trim_orderbooks(orderbooks_arg):
    orderbooks = []
    for orderbook in orderbooks_arg:
        if float(orderbook["best_bid_amount"]) > 0 or float(orderbook["best_ask_amount"]) > 0:
            orderbooks.append(orderbook)

    return orderbooks



# takes orderbooks as argument and returns a simplified 2D list: ["lyra", [put_bid, put_ask, call_bid, call_ask, strike, expiry (DD:MM:YY), index]...[]]
def get_orderbooks_simple(orderbooks_arg):
    orderbooks = trim_orderbooks(orderbooks_arg)

    orderbooks_simple = ["lyra"]
    index_price = float(orderbooks[0]["index_price"])

    for orderbook in orderbooks:
        instrument_name = orderbook["instrument_name"][:-2]
        strike = float(orderbook["option_details"]["strike"])
        option_type = orderbook["option_details"]["option_type"] #"C" or "P"
        expiry = orderbook["option_details"]["expiry"] #(int) unix timestamp in seconds

        if option_type == "P":
                orderbooks_simple_element = [float(orderbook["best_bid_price"]) if float(orderbook["best_bid_amount"]) > 0 else -1, float(orderbook["best_ask_price"]) if float(orderbook["best_ask_amount"]) > 0 else -1, -1, -1, strike, expiry, index_price]

                for o in orderbooks:
                    if o["instrument_name"] == instrument_name + "-C":
                        orderbooks_simple_element[2] = float(o["best_bid_price"]) if float(o["best_bid_amount"]) > 0 else -1
                        orderbooks_simple_element[3] = float(o["best_ask_price"]) if float(o["best_ask_amount"]) > 0 else -1

                if orderbooks_simple_element[0] > 0 or orderbooks_simple_element[1] > 0 or orderbooks_simple_element[2] > 0 or orderbooks_simple_element[3] > 0:
                    orderbooks_simple.append(orderbooks_simple_element)

                continue

        if option_type == "C" and (float(orderbook["best_bid_amount"]) > 0 or float(orderbook["best_ask_amount"]) > 0):
            no_match = True
            for o in orderbooks:
                if o["instrument_name"] == instrument_name + "-P":
                    no_match = False
            if no_match:
                orderbooks_simple.append([-1, -1, float(orderbook["best_bid_price"]) if float(orderbook["best_bid_amount"]) > 0 else -1, float(orderbook["best_ask_price"]) if float(orderbook["best_ask_amount"]) > 0 else -1, strike, expiry, index_price])

    # convert to timestamp to 'DDMMYY'
    for i in range(1, len(orderbooks_simple)):
        orderbooks_simple[i][5] = dt.fromtimestamp(orderbooks_simple[i][5]).strftime('%d%b%y').upper()

    return orderbooks_simple




class Lyra:
    def __init__(self):
        self.instruments = get_instruments()
        loop = asyncio.new_event_loop()
        self.orderbooks = loop.run_until_complete(get_orderbooks(self.instruments, loop))
        loop.close()
        self.orderbooks_simple = get_orderbooks_simple(self.orderbooks)
        self.index_price = float(self.orderbooks[0]["index_price"])

