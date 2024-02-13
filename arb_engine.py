# should probably make classes
import aevo_options_api as aevo
import deribit_options_api as deribit
# import numpy as np
import asyncio
import math
import time
import copy
from datetime import datetime as dt
import pandas as pd
import streamlit as st
import tkinter as tk
from tkinter import ttk
import tkinter.scrolledtext as scrolledtext 

# temporary, set up class variables per module later
DERIBIT_URL = "https://www.deribit.com/options/ETH/ETH-"
AEVO_URL = "https://app.aevo.xyz/option/eth"




def aggregate_markets(*markets_simple_args):
    # markets_simple format: [[put mark, call mark, strike, expiry (DD:MM:YY), index]...[]]
    # aggregated_markets format: {expiry1: {strike1: [[[put, label]...[]], [[call, label]...[]]]}, ... , strike_n: []}, ... , expiry_n: {...}}

    # [["market_1", [], ..., []]...["market_n", [], ..., []]]
    markets = list(markets_simple_args)
    aggregated_markets = {}
    # max of indexes to be safe
    indices = [markets[0][1][4]]
    average_index = indices[0]

    for market in markets:
        exchange = market[0]

        for m in market[1:]:
            expiry = m[3]
            strike = m[2]
            put_mark = m[0]
            call_mark = m[1]

            if expiry not in aggregated_markets:
                aggregated_markets[expiry] = {strike: [[[put_mark, exchange]], [[call_mark, exchange]]]}
            else:
                if strike not in aggregated_markets[expiry]:
                    aggregated_markets[expiry][strike] = [[[put_mark, exchange]], [[call_mark, exchange]]]
                else:
                    aggregated_markets[expiry][strike][0].append([put_mark, exchange])
                    aggregated_markets[expiry][strike][1].append([call_mark, exchange])

        if market[1][4] not in indices:
            indices.append(market[1][4])

    average_index = sum(indices) / len(indices)
    aggregated_markets["index"] = average_index

    return aggregated_markets




def trim_aggregated_markets(aggregated_markets):
    aggregated_markets_trimmed = {}

    for expiry in aggregated_markets:
        if expiry == "index":
            break

        aggregated_markets_trimmed[expiry] = {}

        for strike in aggregated_markets[expiry]:
            marks = [[], []]
            for put_mark in aggregated_markets[expiry][strike][0]:
                if put_mark[0] > 0:
                    marks[0].append(put_mark)

            for call_mark in aggregated_markets[expiry][strike][1]:
                if call_mark[0] > 0:
                    marks[1].append(call_mark)
            
            if len(marks[0]) > 0 and len(marks[1]) > 0:
                aggregated_markets_trimmed[expiry][strike] = marks

    aggregated_markets_trimmed["index"] = aggregated_markets["index"]

    return aggregated_markets_trimmed




# {expiry: {strike: [[[best_put, exchange], [best_call, exchange], absolute_profit, percent_profit], ... []], ... strike_n: []}, ... expiry_n: ... }
def arb_dict_from_mark(aggregated_markets, rounded=True, precision=3):
    arb_dict = trim_aggregated_markets(aggregated_markets)
    index = arb_dict["index"]
    
    for expiry in arb_dict:
        if expiry == "index":
            break

        for strike in arb_dict[expiry]:
            max_put = arb_dict[expiry][strike][0][0]
            min_put = arb_dict[expiry][strike][0][0]
            max_call = arb_dict[expiry][strike][1][0]
            min_call = arb_dict[expiry][strike][1][0]

            for put_mark in arb_dict[expiry][strike][0]:
                if put_mark[0] > max_put[0]:
                    max_put = put_mark
                if put_mark[0] < min_put[0]:
                    min_put = put_mark


            for call_mark in arb_dict[expiry][strike][1]:
                if call_mark[0] > max_call[0]:
                    max_call = call_mark
                if call_mark[0] < min_call[0]:
                    min_call = call_mark


            if (max_put[0] - min_call[0]) > (max_call[0] - min_put[0]):
                if rounded:
                    best_marks = [[round(max_put[0], precision), max_put[1]], [round(min_call[0], precision), min_call[1]]]
                else:
                    best_marks = [max_put, min_call]

            else:
                if rounded:
                    best_marks = [[round(min_put[0], precision), min_put[1]], [round(max_call[0], precision), max_call[1]]]
                else:
                    best_marks = [min_put, max_call]

            arb_dict[expiry][strike] = [best_marks[0], best_marks[1]]

            expected_profit = abs((index + best_marks[0][0]) - (strike + best_marks[1][0]))
            if rounded:
                arb_dict[expiry][strike].append(round(expected_profit, precision))
                arb_dict[expiry][strike].append(round(expected_profit / (index + best_marks[0][0] + best_marks[1][0]) * 100, precision))
            else:
                arb_dict[expiry][strike].append(expected_profit)
                arb_dict[expiry][strike].append(expected_profit / (index + best_marks[0][0] + best_marks[1][0]) * 100)

    return arb_dict




def sort_arb_dict_mark(arb_dict_mark):
    # temporary fix, want to avoid pop() eventually
    arb_dict_mark.pop("index")
    arb_dict_sorted = {expiry: strike for expiry, strike in sorted(arb_dict_mark.items(), key= lambda item: dt.timestamp(dt.strptime(item[0], "%d%b%y")))}

    for expiry in arb_dict_mark:
        arb_dict_sorted[expiry] = {strike: info for strike, info in sorted(arb_dict_mark[expiry].items(), key=lambda item: item[1][3], reverse=True)}

    return arb_dict_sorted




def aggregate_orderbooks(*orderbooks_simple_args):
    # orderbooks_simple_args: ([exchange, [put_bid, put_ask, call_bid, call_ask, strike, expiry, index], ... ,[]], ... , [exchange_n, [], ... []])
    # aggregated_orderbooks format: {expiry1: {strike1: [[[put_bid, label]...[]], [[put_ask, label]...[]], [[call_bid, label], [[call_ask, label], ...[]]]}, ... , strike_n: [[], [], [], []]}, ... , expiry_n: {...}}
    orderbooks = list(orderbooks_simple_args)
    print(orderbooks[0])
    aggregated_orderbooks = {}
    # max of indexes between exchanges just to be safe
    indices = [orderbooks[0][1][6]]
    average_index = indices[0]

    for orderbook in orderbooks:
        exchange = orderbook[0]

        for o in orderbook[1:]:
            expiry = o[5]
            strike = o[4]
            put_bid = o[0]
            put_ask = o[1]
            call_bid = o[2]
            call_ask = o[3]

            if expiry not in aggregated_orderbooks:
                aggregated_orderbooks[expiry] = {strike: [[[put_bid, exchange]], [[put_ask, exchange]], [[call_bid, exchange]], [[call_ask, exchange]]]}
            else:
                if strike not in aggregated_orderbooks[expiry]:
                    aggregated_orderbooks[expiry][strike] = [[[put_bid, exchange]], [[put_ask, exchange]], [[call_bid, exchange]], [[call_ask, exchange]]]
                else:
                    aggregated_orderbooks[expiry][strike][0].append([put_bid, exchange])
                    aggregated_orderbooks[expiry][strike][1].append([put_ask, exchange])
                    aggregated_orderbooks[expiry][strike][2].append([call_bid, exchange])
                    aggregated_orderbooks[expiry][strike][3].append([call_ask, exchange])

        if orderbook[1][6] not in indices:
            indices.append(orderbook[1][6])

    average_index = sum(indices) / len(indices)
    aggregated_orderbooks["index"] = average_index

    return aggregated_orderbooks



# only retain max bids and min asks
def simplify_aggregated_orderbooks(aggregated_orderbooks):
    aggregated_orderbooks_simple = {}

    for expiry in aggregated_orderbooks:
        if expiry == "index":
            break

        aggregated_orderbooks_simple[expiry] = {}

        for strike in aggregated_orderbooks[expiry]:
            orders = [aggregated_orderbooks[expiry][strike][0][0], aggregated_orderbooks[expiry][strike][1][0], aggregated_orderbooks[expiry][strike][2][0], aggregated_orderbooks[expiry][strike][3][0]]
            
            for put_bid in aggregated_orderbooks[expiry][strike][0]:
                if put_bid[0] > orders[0][0]:
                    orders[0] = put_bid

            for put_ask in aggregated_orderbooks[expiry][strike][1]:
                if put_ask[0] > orders[1][0]:
                    orders[1] = put_ask
            
            for call_bid in aggregated_orderbooks[expiry][strike][2]:
                if call_bid[0] > orders[2][0]:
                    orders[2] = call_bid
            
            for call_ask in aggregated_orderbooks[expiry][strike][3]:
                if call_ask[0] > orders[3][0]:
                    orders[3] = call_ask
            
            if orders[0][0] <= 0 or orders[3][0] <= 0:
                orders[0] = None
                orders[3] = None

            if orders[1][0] <= 0 or orders[2][0] <= 0:
                orders[1] = None
                orders[2] = None

            if orders[0] != None or orders[1] != None:
                aggregated_orderbooks_simple[expiry][strike] = orders

    aggregated_orderbooks_simple["index"] = aggregated_orderbooks["index"]

    return aggregated_orderbooks_simple
          
            
# later add annualised return
# {expiry: {strike: [[[best_put_bid, exchange], [best_put_ask, exchange], [best_call_bid, exchange], [best_call_ask, exchange], absolute_profit, percent_profit], ... []], ... strike_n: []}, ... expiry_n: ... }
def arb_dict_from_orderbooks(aggregated_orderbooks_arg):
    orderbooks = simplify_aggregated_orderbooks(aggregated_orderbooks_arg)
    index = orderbooks["index"]
    time_now = time.time()
    arb_dict = {}
    
    for expiry in orderbooks:
        if expiry == "index":
            break

        for strike in orderbooks[expiry]:
            # profit calculation is incorrect: fix
            # for one, current configuration allows asks to be larger than bids, implying you buy the more expensive option and sell the cheaper one (for negative profit)
            # abs((index + put) - (strike + call)), %of (index + put + call)
            abs_profit = -1
            percent_profit = -1
            orders = orderbooks[expiry][strike]

            # if nonempty and index + put_bid > strike + call_ask (since we can only market buy asks and sell bids, and we want to buy the cheaper side of the put-call parity equation and sell the more expensive side)
            if orders[0] != None and ((index + orders[0][0]) > (strike + orders[3][0])):
                abs_profit = abs((index + orders[0][0]) - (strike + orders[3][0]))
                percent_profit = abs_profit / (index + orders[0][0] + orders[3][0]) * 100
            else:
                orders[0] = None
                orders[3] = None
            
            if orders[1] != None and ((index + orders[1][0]) < (strike + orders[2][0])):
                this_profit = abs((index + orders[1][0]) - (strike + orders[2][0]))
                
                if this_profit > abs_profit:
                    abs_profit = this_profit
                    percent_profit = abs_profit / (index + orders[1][0] + orders[2][0]) * 100

                    orders[0] = None
                    orders[3] = None

                else:
                    orders[1] = None
                    orders[2] = None
            else:
                orders[1] = None
                orders[2] = None

            expiry_unix = dt.timestamp(dt.strptime(expiry, "%d%b%y"))
            apy = math.ceil((1 + expiry_unix - time_now) / 86400) * percent_profit / 365
            
            if orders[0] != None or orders[1] != None:
                arb_dict[expiry] = {}
                arb_dict[expiry][strike] = orders
                arb_dict[expiry][strike].append(abs_profit)
                arb_dict[expiry][strike].append(percent_profit)
                arb_dict[expiry][strike].append(apy)

    arb_dict["index"] = index

    return arb_dict




def sort_arb_dict_orderbooks(arb_dict_orderbooks):
    # temporary fix, want to avoid pop() eventually
    index = arb_dict_orderbooks["index"]
    arb_dict_orderbooks.pop("index")
    arb_dict_sorted = {expiry: strike for expiry, strike in sorted(arb_dict_orderbooks.items(), key= lambda item: dt.timestamp(dt.strptime(item[0], "%d%b%y")))}

    for expiry in arb_dict_orderbooks:
        arb_dict_sorted[expiry] = {strike: info for strike, info in sorted(arb_dict_orderbooks[expiry].items(), key=lambda item: item[1][5], reverse=True)}

    arb_dict_sorted["index"] = index
    return arb_dict_sorted


def draw_gui(arb_dict):
    root = tk.Tk()
    root.title("orderbook")
    # root.geometry("800x500")
    
    frm = ttk.Frame(root, padding=10)
    frm.grid()

    text = ""

    for expiry in arb_dict:
        for strike in arb_dict[expiry]:
            text += f"{expiry}: {strike}:     [{round(arb_dict[expiry][strike][0][0], 3)}, {arb_dict[expiry][strike][0][1]}],     [{round(arb_dict[expiry][strike][1][0], 3)}, {arb_dict[expiry][strike][1][1]}],     {round(arb_dict[expiry][strike][2], 3)},     {round(arb_dict[expiry][strike][3], 3)}% \n"

    text_area = scrolledtext.ScrolledText(root, width=110, height = 50)
    text_area.grid()
    text_area.insert(tk.INSERT, text)
 
    # ttk.Button(frm, text="Quit", command=root.destroy).grid(column=1, row=0)
    root.mainloop()




def draw_streamlit_gui(arb_dict_sorted):
    expiries = list(arb_dict_sorted.keys())
    # arb_df_list = []

    for expiry in expiries:
        for strike in arb_dict_sorted[expiry]:
            arb_dict_sorted[expiry][strike][0] = str(arb_dict_sorted[expiry][strike][0])
            arb_dict_sorted[expiry][strike][1] = str(arb_dict_sorted[expiry][strike][1])

        arb_df = pd.DataFrame.from_dict(data=arb_dict_sorted[expiry], orient="index", columns=["Put mark", "Call mark", "Profit", "%Profit"])
        # arb_df_list.append(arb_df)

        st.subheader(expiry)
        st.dataframe(arb_df)




def draw_streamlit_gui_orderbooks(arb_dict_orderbooks_sorted):
    expiries = list(arb_dict_orderbooks_sorted.keys())
    # arb_df_list = []
    index = arb_dict_orderbooks_sorted["index"]
    st.subheader("Ethereum index price: " + str(index))

    for expiry in expiries:
        if expiry == "index":
            break

        for strike in arb_dict_orderbooks_sorted[expiry]:
            arb_dict_orderbooks_sorted[expiry][strike][0] = str(arb_dict_orderbooks_sorted[expiry][strike][0])
            arb_dict_orderbooks_sorted[expiry][strike][1] = str(arb_dict_orderbooks_sorted[expiry][strike][1])
            arb_dict_orderbooks_sorted[expiry][strike][2] = str(arb_dict_orderbooks_sorted[expiry][strike][2])
            arb_dict_orderbooks_sorted[expiry][strike][3] = str(arb_dict_orderbooks_sorted[expiry][strike][3])

        arb_df = pd.DataFrame.from_dict(data=arb_dict_orderbooks_sorted[expiry], orient="index", columns=["Put bid", "Put ask", "Call bid", "Call ask", "Profit", "%Profit", "APY"])
        # arb_df_list.append(arb_df)

        st.subheader(expiry)
        st.dataframe(arb_df)




def main():
    deribit_markets = deribit.get_markets()
    # print(deribit_markets[140:170])
    deribit_markets_simple = deribit.get_markets_simple(deribit_markets)
    
    # print(deribit_orderbooks_simple)
    aevo_markets = aevo.get_markets()
    aevo_markets_simple = aevo.get_markets_simple(aevo_markets)

    aggregated_markets = aggregate_markets(deribit_markets_simple, aevo_markets_simple)
    arb_dict_mark = arb_dict_from_mark(aggregated_markets)

    arb_dict_mark_sorted = sort_arb_dict_mark(arb_dict_mark)
    # print(arb_dict_mark_sorted)



    deribit_orderbooks_simple = deribit.get_orderbooks_simple(deribit_markets)

    start = time.perf_counter()
    loop = asyncio.new_event_loop()
    aevo_orderbooks = loop.run_until_complete(aevo.get_orderbooks(aevo_markets, loop))
    loop.close()
    # print("event loop is closed: " + str(loop.is_closed()))
    end = time.perf_counter()
    aevo_orderbooks_simple = aevo.get_orderbooks_simple(aevo_orderbooks)
    # print(aevo_orderbooks_simple)
    # print(end-start)
    
    aggregated_orderbooks = aggregate_orderbooks(deribit_orderbooks_simple, aevo_orderbooks_simple)
    print(aggregated_orderbooks)
    arb_dict_orderbooks = arb_dict_from_orderbooks(aggregated_orderbooks)
    print(arb_dict_orderbooks)

    arb_dict_orderbooks_sorted = sort_arb_dict_orderbooks(arb_dict_orderbooks)
    # print(arb_dict_orderbooks_sorted)
    # print(simplify_aggregated_orderbooks(aggregated_orderbooks))


    draw_streamlit_gui_orderbooks(arb_dict_orderbooks_sorted)
   


    # print(aevo_markets[0:5])

    # print(deribit_markets[0:5])

    # print(arb_dict_sorted)

    # draw_gui(arb_dict_sorted)

    # draw_streamlit_gui(arb_dict_sorted)




if __name__ == "__main__":
    main()