import streamlit as st
import pandas as pd
import asyncio
import time
import arb_engine
from deribit_options_api import Deribit
from aevo_options_api import Aevo




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
    deribit = Deribit()
    aevo = Aevo()

    markets = arb_engine.Markets(deribit.markets_simple, aevo.markets_simple)
    orderbooks = arb_engine.Orderbooks(deribit.orderbooks_simple, aevo.orderbooks_simple)
   
    draw_streamlit_gui_orderbooks(orderbooks.arb_dict_sorted)




if __name__ == "__main__":
    main()