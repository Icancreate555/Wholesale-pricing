import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.write("Enter a product to begin pricing.")

st.subheader("Add Product")

product = st.text_input("Product")
buying_price = st.number_input("Buying Price (KES)", min_value=0.0, step=1.0)
quantity = st.number_input("Quantity", min_value=1, step=1)
current_price = st.number_input("Current Selling Price (KES)", min_value=0.0, step=1.0)
purchase_date = st.date_input("Purchase Date", value=date.today())

if st.button("Add Product"):
    if product and buying_price > 0 and current_price > 0:
        margin = ((current_price - buying_price) / current_price) * 100

        st.success(f"{product} added successfully.")

        st.subheader("Pricing Information")

        st.write(f"**Product:** {product}")
        st.write(f"**Buying Price:** KES {buying_price:,.2f}")
        st.write(f"**Quantity:** {quantity}")
        st.write(f"**Current Selling Price:** KES {current_price:,.2f}")
        st.write(f"**Current Margin:** {margin:.2f}%")
        st.write(f"**Purchase Date:** {purchase_date}")

    else:
        st.warning("Please enter the product, buying price and current selling price.")
