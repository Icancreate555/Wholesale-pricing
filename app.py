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

            # This is now editable
            pricing_data["Current Selling Price"] = None

            pricing_data["Current Margin"] = None

            pricing_data["Recommended Margin"] = ""

            # -----------------------------
            # DISPLAY
            # -----------------------------

            st.success(
                f"{len(pricing_data)} products imported."
            )

            st.subheader("Pricing Workspace")

            st.write(
                "Enter the current selling price for each product."
            )

            # Editable pricing table
            edited_data = st.data_editor(
                pricing_data,
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "Product",
                    "Buying Price",
                    "Market Range",
                    "Recommended Price",
                    "Current Margin",
                    "Recommended Margin"
                ],
                column_config={
                    "Current Selling Price": st.column_config.NumberColumn(
                        "Current Selling Price",
                        help="Enter the price at which the wholesaler currently sells this product.",
                        min_value=0,
                        step=1,
                        format="KES %.2f"
                    ),
                    "Buying Price": st.column_config.NumberColumn(
                        "Buying Price",
                        format="KES %.2f"
                    )
                }
            )

            # -----------------------------
            # CALCULATE CURRENT MARGIN
            # -----------------------------

            edited_data["Current Selling Price"] = pd.to_numeric(
                edited_data["Current Selling Price"],
                errors="coerce"
            )

            edited_data["Current Margin"] = (
                edited_data["Current Selling Price"]
                - edited_data["Buying Price"]
            )

            # -----------------------------
            # SHOW UPDATED TABLE
            # -----------------------------

            st.subheader("Updated Pricing")

            st.dataframe(
                edited_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Buying Price": st.column_config.NumberColumn(
                        "Buying Price",
                        format="KES %.2f"
                    ),
                    "Current Selling Price": st.column_config.NumberColumn(
                        "Current Selling Price",
                        format="KES %.2f"
                    ),
                    "Current Margin": st.column_config.NumberColumn(
                        "Current Margin",
                        format="KES %.2f"
                    )
                }
            )

    except Exception as e:

        st.error(
            f"We could not process the QuickBooks file: {e}"
        )
