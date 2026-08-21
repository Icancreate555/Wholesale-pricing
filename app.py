import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.write("Upload your QuickBooks purchase file.")

# -----------------------------
# UPLOAD EXCEL
# -----------------------------

uploaded_file = st.file_uploader(
    "Upload QuickBooks Excel file",
    type=["xlsx", "xls"]
)

if uploaded_file is not None:

    try:
        # Read Excel
        raw_data = pd.read_excel(uploaded_file)

        # Remove completely empty rows
        data = raw_data.dropna(how="all").copy()

        # Clean column names
        data.columns = (
            data.columns
            .astype(str)
            .str.strip()
        )

        # Remove rows without a product
        data = data[
            data["Item"].notna()
        ].copy()

        # Remove summary rows
        data = data[
            data["Item"].astype(str).str.strip() != ""
        ]

        # Convert buying price to number
        data["Cost Price"] = pd.to_numeric(
            data["Cost Price"],
            errors="coerce"
        )

        # Remove rows where buying price is missing
        data = data[
            data["Cost Price"].notna()
        ].copy()

        # -----------------------------
        # CREATE PRICING TABLE
        # -----------------------------

        pricing_data = pd.DataFrame()

        pricing_data["Product"] = (
            data["Memo"]
            .astype(str)
            .str.strip()
        )

        pricing_data["Buying Price"] = (
            data["Cost Price"]
        )

        pricing_data["Market Range"] = ""

        pricing_data["Recommended Price"] = ""

        pricing_data["Current Selling Price"] = ""

        pricing_data["Current Margin"] = ""

        pricing_data["Recommended Margin"] = ""

        # -----------------------------
        # DISPLAY
        # -----------------------------

        st.success(
            f"{len(pricing_data)} products imported successfully."
        )

        st.subheader("Pricing Workspace")

        st.dataframe(
            pricing_data,
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:

        st.error(
            f"We could not process this QuickBooks file: {e}"
        )
