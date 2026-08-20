
import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.write("Enter and review your wholesale pricing information.")

# Store products during the current session
if "products" not in st.session_state:
    st.session_state.products = []

# -----------------------------
# ADD PRODUCT
# -----------------------------
st.subheader("Add Product")

product = st.text_input("Product")
buying_price = st.number_input(
    "Buying Price (KES)",
    min_value=0.0,
    step=1.0
)

quantity = st.number_input(
    "Quantity",
    min_value=1,
    step=1
)

current_price = st.number_input(
    "Current Selling Price (KES)",
    min_value=0.0,
    step=1.0
)

purchase_date = st.date_input(
    "Purchase Date",
    value=date.today()
)

if st.button("Add Product"):

    if product and buying_price > 0 and current_price > 0:

        margin = (
            (current_price - buying_price)
            / current_price
        ) * 100

        new_product = {
            "Product": product,
            "Buying Price": buying_price,
            "Market Range": "",
            "Recommended Price": "",
            "Current Selling Price": current_price,
            "Current Margin": margin,
            "Recommended Margin": "",
            "Quantity": quantity,
            "Purchase Date": purchase_date
        }

        st.session_state.products.append(new_product)

        st.success(f"{product} added successfully.")

    else:
        st.warning(
            "Please enter the product, buying price "
            "and current selling price."
        )

# -----------------------------
# PRICING TABLE
# -----------------------------
if st.session_state.products:

    st.subheader("Pricing Workspace")

    st.dataframe(
        st.session_state.products,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "No products have been added yet. "
        "Enter a product above to begin."
    )
