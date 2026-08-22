import streamlit as st
import pandas as pd


# ==========================================
# PAGE SETUP
# ==========================================

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.write(
    "Upload your QuickBooks purchase file and review your pricing."
)


# ==========================================
# EXCEL UPLOAD
# ==========================================

uploaded_file = st.file_uploader(
    "Upload QuickBooks Excel file",
    type=["xlsx", "xls"]
)


if uploaded_file is not None:

    try:

        # ==========================================
        # READ QUICKBOOKS SHEET
        # ==========================================

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


        # ==========================================
        # CHECK REQUIRED COLUMNS
        # ==========================================

        required_columns = [
            "Date",
            "Num",
            "Memo",
            "Item",
            "Qty",
            "U/M",
            "Cost Price"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in data.columns
        ]

        if missing_columns:

            st.error(
                "The QuickBooks file is missing these columns: "
                + ", ".join(missing_columns)
            )

            st.stop()


        # ==========================================
        # CLEAN NUMERIC DATA
        # ==========================================

        data["Cost Price"] = pd.to_numeric(
            data["Cost Price"],
            errors="coerce"
        )

        data["Qty"] = pd.to_numeric(
            data["Qty"],
            errors="coerce"
        )


        # ==========================================
        # REMOVE INVALID / SUMMARY ROWS
        # ==========================================

        data = data[
            data["Memo"].notna()
            & data["Cost Price"].notna()
        ].copy()

        data["Memo"] = (
            data["Memo"]
            .astype(str)
            .str.strip()
        )

        data = data[
            data["Memo"] != ""
        ].copy()


        # ==========================================
        # CREATE PRICING WORKSPACE
        # ==========================================

        pricing_data = pd.DataFrame()

        pricing_data["Product"] = data["Memo"]

        pricing_data["Buying Price"] = data["Cost Price"]

        pricing_data["Quantity"] = data["Qty"]

        pricing_data["Unit"] = data["U/M"]

        pricing_data["Purchase Date"] = data["Date"]

        pricing_data["Market Range"] = "No evidence yet"

        pricing_data["Current Selling Price"] = None

        pricing_data["Current Margin"] = None


        # ==========================================
        # LOAD MARKET EVIDENCE
        # ==========================================

        try:

            evidence = pd.read_csv(
                "market_evidence.csv"
            )

            # Make sure the evidence file has the
            # expected columns
            evidence_columns = [
                "product",
                "pack_size",
                "location",
                "price",
                "unit",
                "date",
                "source",
                "source_type",
                "evidence_strength"
            ]

            if all(
                column in evidence.columns
                for column in evidence_columns
            ):

                evidence["price"] = pd.to_numeric(
                    evidence["price"],
                    errors="coerce"
                )

                evidence = evidence.dropna(
                    subset=["price"]
                ).copy()


                # ==========================================
                # CREATE MARKET RANGES
                # ==========================================

                for index, row in pricing_data.iterrows():

                    product_name = str(
                        row["Product"]
                    ).strip().upper()

                    product_evidence = evidence[
                        evidence["product"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        == product_name
                    ]

                    if not product_evidence.empty:

                        lowest_price = (
                            product_evidence["price"]
                            .min()
                        )

                        highest_price = (
                            product_evidence["price"]
                            .max()
                        )

                        pricing_data.at[
                            index,
                            "Market Range"
                        ] = (
                            f"KES {lowest_price:,.2f}"
                            f" – "
                            f"KES {highest_price:,.2f}"
                        )


        except FileNotFoundError:

            # Evidence file does not exist yet.
            # This is acceptable for V1.
            pass


        # ==========================================
        # DISPLAY IMPORT RESULT
        # ==========================================

        st.success(
            f"{len(pricing_data)} products imported successfully."
        )


        # ==========================================
        # PRICING TABLE
        # ==========================================

        st.subheader("Pricing Workspace")

        st.dataframe(
            pricing_data,
            use_container_width=True,
            hide_index=True
        )


        # ==========================================
        # OWNER PRICE ENTRY
        # ==========================================

        st.divider()

        st.subheader("Enter Your Selling Price")

        product_options = pricing_data[
            "Product"
        ].tolist()

        selected_product = st.selectbox(
            "Select a product",
            product_options
        )


        # Get selected product
        selected_index = pricing_data[
            pricing_data["Product"]
            == selected_product
        ].index[0]

        selected_row = pricing_data.loc[
            selected_index
        ]


        # ==========================================
        # SHOW PRODUCT INFORMATION
        # ==========================================

        st.write(
            f"**Product:** {selected_product}"
        )

        st.write(
            f"**Buying Price:** "
            f"KES {selected_row['Buying Price']:,.2f}"
        )

        st.write(
            f"**Market Evidence:** "
            f"{selected_row['Market Range']}"
        )


        # ==========================================
        # OWNER ENTERS SELLING PRICE
        # ==========================================

        selling_price = st.number_input(
            "Your Current Selling Price (KES)",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        )


        # ==========================================
        # CALCULATE MARGIN
        # ==========================================

        if selling_price > 0:

            buying_price = float(
                selected_row["Buying Price"]
            )

            profit = (
                selling_price
                - buying_price
            )

            margin = (
                profit
                / selling_price
                * 100
            )


            st.write(
                f"**Profit per selling unit:** "
                f"KES {profit:,.2f}"
            )

            st.write(
                f"**Current Margin:** "
                f"{margin:.2f}%"
            )


            # ==========================================
            # OWNER DECISION
            # ==========================================

            st.info(
                "The selling price is your decision. "
                "The system provides information and "
                "calculations to support your judgement."
            )


            if st.button(
                "Save Selling Price"
            ):

                st.success(
                    f"Selling price of "
                    f"KES {selling_price:,.2f} "
                    f"recorded for {selected_product}."
                )


    except Exception as e:

        st.error(
            f"We could not process the QuickBooks file: {e}"
        )
