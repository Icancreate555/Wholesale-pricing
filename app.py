import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.write("Upload your QuickBooks purchase file.")

uploaded_file = st.file_uploader(
    "Upload QuickBooks Excel file",
    type=["xlsx", "xls"]
)

if uploaded_file is not None:

    try:
        # Read the correct QuickBooks sheet
        data = pd.read_excel(
            uploaded_file,
            sheet_name="Sheet1",
            header=0
        )

        # Clean column names
        data.columns = (
            data.columns
            .astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )

        # Remove completely empty rows
        data = data.dropna(how="all").copy()

        # Make sure required columns exist
        required_columns = [
            "Memo",
            "Item",
            "Qty",
            "U/M",
            "Cost Price",
            "Date",
            "Num"
        ]

        missing_columns = [
            column for column in required_columns
            if column not in data.columns
        ]

        if missing_columns:

            st.error(
                f"Missing columns: {missing_columns}"
            )

        else:

            # Convert Cost Price to numbers
            data["Cost Price"] = pd.to_numeric(
                data["Cost Price"],
                errors="coerce"
            )

            # Convert Quantity to numbers
            data["Qty"] = pd.to_numeric(
                data["Qty"],
                errors="coerce"
            )

            # Remove rows without a product or buying price
            data = data[
                data["Memo"].notna()
                & data["Cost Price"].notna()
            ].copy()

            # Remove possible summary rows
            data = data[
                data["Memo"].astype(str).str.strip() != ""
            ].copy()

            # -----------------------------
            # CREATE PRICING WORKSPACE
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
                f"{len(pricing_data)} products imported."
            )

            st.subheader("Pricing Workspace")

            st.dataframe(
                pricing_data,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:

        st.error(
            f"We could not process the QuickBooks file: {e}"
        )
