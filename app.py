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

       st.write("Columns detected:")
st.write(list(data.columns))

st.write("First rows:")
st.dataframe(data, use_container_width=True)
