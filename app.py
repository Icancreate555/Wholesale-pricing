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
        # Read Excel file
        raw_data = pd.read_excel(uploaded_file)

        # Clean column names
        raw_data.columns = (
            raw_data.columns
            .astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )

        # Remove completely empty rows
        data = raw_data.dropna(how="all").copy()

        # Show the columns temporarily so we can verify them
        st.write("Columns detected:")
        st.write(list(data.columns))

        # Check that Item exists
        if "Item" not in data.columns:
            st.error(
                "The system could not find the 'Item' column."
            )
            st.stop()

        # Remove rows without Item
        data = data[data["Item"].notna()].copy()

        # Convert Item to text
        data["Item"] = data["Item"].astype(str).str.strip()

        # Remove empty Item rows
        data = data[data["Item"] != ""].copy()

        # Check Cost Price
        if "Cost Price" not in data.columns:
            st.error(
                "The system could not find the 'Cost Price' column."
            )
            st.stop()

        # Convert Cost Price to numbers
        data["Cost Price"] = pd.to_numeric(
            data["Cost Price"],
            errors="coerce"
        )

        # Remove rows without a buying price
        data = data[data["Cost Price"].notna()].copy()

        # Create pricing table
        pricing_data = pd.DataFrame()

        pricing_data["Product"] = (
            data["Memo"]
            .fillna(data["Item"])
            .astype(str)
            .str.strip()
        )

        pricing_data["Buying Price"] = data["Cost Price"]

        pricing_data["Market Range"] = ""

        pricing_data["Recommended Price"] = ""

        pricing_data["Current Selling Price"] = ""

        pricing_data["Current Margin"] = ""

        pricing_data["Recommended Margin"] = ""

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
