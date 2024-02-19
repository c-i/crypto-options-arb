import streamlit as st
import pandas as pd
import asyncio
import time
from arb_engine import *
import deribit_options_api as deribit
import aevo_options_api as aevo




def draw_streamlit_gui_marks(arb_dict_sorted):
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
    deribit_markets_simple = deribit.get_markets_simple(deribit_markets)
    
    aevo_markets = aevo.get_markets()
    aevo_markets_simple = aevo.get_markets_simple(aevo_markets)

    aggregated_markets = aggregate_markets(deribit_markets_simple, aevo_markets_simple)
    arb_dict_mark = arb_dict_from_mark(aggregated_markets)

    arb_dict_mark_sorted = sort_arb_dict_mark(arb_dict_mark)



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
    # print(aggregated_orderbooks)
    arb_dict_orderbooks = arb_dict_from_orderbooks(aggregated_orderbooks)
    # print(arb_dict_orderbooks)

    arb_dict_orderbooks_sorted = sort_arb_dict_orderbooks(arb_dict_orderbooks)
    # print(arb_dict_orderbooks_sorted)
    # print(simplify_aggregated_orderbooks(aggregated_orderbooks))


    draw_streamlit_gui_orderbooks(arb_dict_orderbooks_sorted)




if __name__ == "__main__":
    main()