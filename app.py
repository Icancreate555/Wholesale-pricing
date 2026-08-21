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
        data = pd.read_excel(
            uploaded_file,
            sheet_name="Sheet1",
            header=0
        )

        st.success("Excel file uploaded successfully.")

        st.subheader("QuickBooks Purchase Data")

        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:

        st.error(
            f"We could not read the QuickBooks file: {e}"
        )
