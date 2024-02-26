import requests
import json
from datetime import datetime as dt



def get_index_price(index_name = "eth_usdc"):
    index_price_url = f"https://www.deribit.com/api/v2/public/get_index_price?index_name={index_name}"

    index_price_response = requests.get(index_price_url)
    index_price = float(json.loads(index_price_response.text)["result"]["index_price"])

    return index_price




def get_markets(currency = "ETH", remove_inactive=True):
    markets_url = f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={currency}&kind=option"
    
    markets_response = requests.get(markets_url)

    if not remove_inactive:
        return json.loads(markets_response.text)["result"]

    markets = []
    for market in json.loads(markets_response.text)["result"]:
        if market["ask_price"] != None or market["bid_price"] != None:
            markets.append(market)

    return markets




def get_markets_simple(markets_arg, quote_usdc = True):
    # ["deribit", [put mark, call mark, strike, expiry (DD:MM:YY), index]...[]]
    # use mid_price as mark price?

    index_price = get_index_price()
    markets_simple = ["deribit"]
    
    for market in markets_arg:
        instrument_name = market["instrument_name"][:-2]
        strike = float(instrument_name[instrument_name.rfind("-") + 1:])
        option_type = market["instrument_name"][-1:]
        expiry = market["underlying_index"][market["underlying_index"].find("-") + 1:]
        
        # not sure whether to use mid_price or mark_price, mid_price for now
        if option_type == "P":
            markets_simple_element = [market["mid_price"] if market["mid_price"] != None else -1, -1, strike, expiry, index_price]

            for m in markets_arg:
                if m["instrument_name"] == (instrument_name + "-C"):
                    markets_simple_element[1] = m["mid_price"] if m["mid_price"] != None else -1
            
            if markets_simple_element[0] > 0 or markets_simple_element[1] > 0:
                markets_simple.append(markets_simple_element)
            
            continue

        if option_type == "C" and market["mid_price"] != None:
            no_match = True
            for m in markets_arg:
                if m["instrument_name"] == (instrument_name + "-P"):
                    no_match = False
            if no_match:
                markets_simple.append([-1, market["mid_price"], strike, expiry, index_price])

    # may run into issue of price being inaccurate due to delay between get_markets request, get_index request, and manipulation of markets list
    for i in range(1, len(markets_simple)):
        if quote_usdc:
            markets_simple[i][0] = markets_simple[i][0] * index_price if markets_simple[i][0] > 0 else -1
            markets_simple[i][1] = markets_simple[i][1] * index_price if markets_simple[i][1] > 0 else -1

        # print(markets_simple[i][3])
        markets_simple[i][3] = dt.fromtimestamp(dt.timestamp(dt.strptime(markets_simple[i][3], "%d%b%y"))).strftime('%d%b%y').upper()

    return markets_simple
    


# takes orderbooks as argument and returns a simplified 2D list: ["deribit", [put_bid, put_ask, call_bid, call_ask, strike, expiry (DD:MM:YY), index]...[]]    
def get_orderbooks_simple(markets_arg, quote_usdc=True):

    index_price = get_index_price()
    orderbooks_simple = ["deribit"]

    for market in markets_arg:
        instrument_name = market["instrument_name"][:-2]
        strike = float(instrument_name[instrument_name.rfind("-") + 1:])
        option_type = market["instrument_name"][-1:]
        expiry = market["underlying_index"][market["underlying_index"].find("-") + 1:]
        bid_price = market["bid_price"]
        ask_price = market["ask_price"]
        
        # not sure whether to use mid_price or mark_price, mid_price for now
        if option_type == "P":
            orderbooks_simple_element = [market["bid_price"] if market["bid_price"] != None else -1, market["ask_price"] if market["ask_price"] != None else -1, -1, -1, strike, expiry, index_price]

            for m in markets_arg:
                if m["instrument_name"] == (instrument_name + "-C"):
                    orderbooks_simple_element[2] = m["bid_price"] if m["bid_price"] != None else -1
                    orderbooks_simple_element[3] = m["ask_price"] if m["ask_price"] != None else -1

            if orderbooks_simple_element[0] > 0 or orderbooks_simple_element[1] > 0 or orderbooks_simple_element[2] > 0 or orderbooks_simple_element[3] > 0:
                orderbooks_simple.append(orderbooks_simple_element)
            
            continue

        if option_type == "C" and (market["bid_price"] != None or market["ask_price"] != None):
            no_match = True
            for m in markets_arg:
                if m["instrument_name"] == (instrument_name + "-P"):
                    no_match = False
            if no_match:
                orderbooks_simple.append([-1, -1, market["bid_price"] if market["bid_price"] != None else -1, market["ask_price"] if market["ask_price"] != None else -1, strike, expiry, index_price])

    
    for i in range(1, len(orderbooks_simple)):
        if quote_usdc:
            orderbooks_simple[i][0] = orderbooks_simple[i][0] * index_price if orderbooks_simple[i][0] > 0 else -1
            orderbooks_simple[i][1] = orderbooks_simple[i][1] * index_price if orderbooks_simple[i][1] > 0 else -1
            orderbooks_simple[i][2] = orderbooks_simple[i][2] * index_price if orderbooks_simple[i][2] > 0 else -1
            orderbooks_simple[i][3] = orderbooks_simple[i][3] * index_price if orderbooks_simple[i][3] > 0 else -1

        orderbooks_simple[i][5] = dt.fromtimestamp(dt.timestamp(dt.strptime(orderbooks_simple[i][5], "%d%b%y"))).strftime('%d%b%y').upper()
    
    return orderbooks_simple




class Deribit:
    def __init__(self):
        self.index_price = get_index_price()
        self.markets = get_markets()
        self.markets_simple = get_markets_simple(self.markets)
        self.orderbooks_simple = get_orderbooks_simple(self.markets)
        


        