import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.write("Upload your QuickBooks purchase file.")


# ---------------------------------
# SESSION STATE
# ---------------------------------

if "saved_pricing_data" not in st.session_state:
    st.session_state.saved_pricing_data = None


# ---------------------------------
# FILE UPLOAD
# ---------------------------------

uploaded_file = st.file_uploader(
    "Upload QuickBooks Excel file",
    type=["xlsx", "xls"]
)


if uploaded_file is not None:

    try:

        # ---------------------------------
        # READ QUICKBOOKS SHEET
        # ---------------------------------

        data = pd.read_excel(
            uploaded_file,
            sheet_name="Sheet1",
            header=0
        )


        # ---------------------------------
        # CLEAN COLUMN NAMES
        # ---------------------------------

        data.columns = (
            data.columns
            .astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )


        # ---------------------------------
        # REMOVE EMPTY ROWS
        # ---------------------------------

        data = data.dropna(how="all").copy()


        # ---------------------------------
        # REQUIRED COLUMNS
        # ---------------------------------

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
            column
            for column in required_columns
            if column not in data.columns
        ]


        if missing_columns:

            st.error(
                f"Missing columns: {missing_columns}"
            )


        else:

            # ---------------------------------
            # CONVERT NUMERIC COLUMNS
            # ---------------------------------

            data["Cost Price"] = pd.to_numeric(
                data["Cost Price"],
                errors="coerce"
            )

            data["Qty"] = pd.to_numeric(
                data["Qty"],
                errors="coerce"
            )


            # ---------------------------------
            # REMOVE INVALID PRODUCTS
            # ---------------------------------

            data = data[
                data["Memo"].notna()
                & data["Cost Price"].notna()
            ].copy()


            # ---------------------------------
            # REMOVE SUMMARY ROWS
            # ---------------------------------

            data = data[
                data["Memo"].astype(str).str.strip() != ""
            ].copy()


            # ---------------------------------
            # CREATE PRICING WORKSPACE
            # ---------------------------------

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

            pricing_data["Current Selling Price"] = None

            pricing_data["Current Margin"] = None

            pricing_data["Current Margin %"] = None

            pricing_data["Recommended Margin"] = ""


            # ---------------------------------
            # SUCCESS MESSAGE
            # ---------------------------------

            st.success(
                f"{len(pricing_data)} products imported."
            )


            # ---------------------------------
            # PRICING WORKSPACE
            # ---------------------------------

            st.subheader("Pricing Workspace")

            st.write(
                "Enter the current selling price for each product."
            )


            # ---------------------------------
            # EDITABLE TABLE
            # ---------------------------------

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
                    "Current Margin %",
                    "Recommended Margin"
                ],

                column_config={

                    "Buying Price":
                        st.column_config.NumberColumn(
                            "Buying Price",
                            format="KES %.2f"
                        ),

                    "Current Selling Price":
                        st.column_config.NumberColumn(
                            "Current Selling Price",
                            help=(
                                "Enter the price at which "
                                "the wholesaler currently "
                                "sells this product."
                            ),
                            min_value=0,
                            step=1,
                            format="KES %.2f"
                        ),

                    "Current Margin":
                        st.column_config.NumberColumn(
                            "Current Margin",
                            format="KES %.2f"
                        ),

                    "Current Margin %":
                        st.column_config.NumberColumn(
                            "Current Margin %",
                            format="%.2f%%"
                        )
                }
            )


            # ---------------------------------
            # CONVERT SELLING PRICE TO NUMBER
            # ---------------------------------

            edited_data["Current Selling Price"] = pd.to_numeric(
                edited_data["Current Selling Price"],
                errors="coerce"
            )


            # ---------------------------------
            # CALCULATE CURRENT MARGIN
            # ---------------------------------

            edited_data["Current Margin"] = (
                edited_data["Current Selling Price"]
                - edited_data["Buying Price"]
            )


            # ---------------------------------
            # CALCULATE CURRENT MARGIN %
            # ---------------------------------

            edited_data["Current Margin %"] = (
                edited_data["Current Margin"]
                / edited_data["Current Selling Price"]
            ) * 100


            # ---------------------------------
            # HANDLE ZERO / EMPTY SELLING PRICE
            # ---------------------------------

            edited_data.loc[
                edited_data["Current Selling Price"].isna()
                | (edited_data["Current Selling Price"] == 0),
                "Current Margin %"
            ] = None


            # ---------------------------------
            # SAVE CHANGES BUTTON
            # ---------------------------------

            if st.button(
                "Save Changes",
                type="primary"
            ):

                st.session_state.saved_pricing_data = (
                    edited_data.copy()
                )

                st.success(
                    "Changes saved successfully."
                )


            # ---------------------------------
            # SHOW SAVED DATA
            # ---------------------------------

            if st.session_state.saved_pricing_data is not None:

                st.subheader("Saved Pricing")

                st.dataframe(
                    st.session_state.saved_pricing_data,
                    use_container_width=True,
                    hide_index=True,

                    column_config={

                        "Buying Price":
                            st.column_config.NumberColumn(
                                "Buying Price",
                                format="KES %.2f"
                            ),

                        "Current Selling Price":
                            st.column_config.NumberColumn(
                                "Current Selling Price",
                                format="KES %.2f"
                            ),

                        "Current Margin":
                            st.column_config.NumberColumn(
                                "Current Margin",
                                format="KES %.2f"
                            ),

                        "Current Margin %":
                            st.column_config.NumberColumn(
                                "Current Margin %",
                                format="%.2f%%"
                            )
                    }
                )


    except Exception as e:

        st.error(
            f"We could not process the QuickBooks file: {e}"
        )
