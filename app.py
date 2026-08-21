import streamlit as st
import pandas as pd

st.title("Wholesale Pricing Workspace")

uploaded_file = st.file_uploader(
    "Upload QuickBooks Excel file",
    type=["xlsx", "xls"]
)

if uploaded_file is not None:
   data = pd.read_excel(
    uploaded_file,
    sheet_name="Sheet1",
    header=0
)

    st.write("Excel file uploaded successfully.")

    st.write("First rows detected:")

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )
