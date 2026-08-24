import streamlit as st
import pandas as pd
import numpy as np


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    page_icon="💼",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")

st.caption(
    "Review your purchases, enter your selling prices, "
    "and understand your margins."
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    return str(value).replace("\xa0", " ").strip()


def clean_column_name(value):
    return (
        clean_text(value)
        .replace("\n", " ")
        .replace("  ", " ")
        .strip()
    )


def calculate_markup(buying_price, selling_price):
    if buying_price <= 0 or selling_price <= 0:
        return np.nan

    profit = selling_price - buying_price

    return (profit / buying_price) * 100


def calculate_margin(buying_price, selling_price):
    if selling_price <= 0:
        return np.nan

    profit = selling_price - buying_price

    return (profit / selling_price) * 100


def get_observation(margin):
    if pd.isna(margin):
        return "Enter a selling price."

    if margin < 1:
        return (
            "Very thin margin. Consider your costs, "
            "competition and how quickly this product moves."
        )

    if margin < 3:
        return (
            "Thin margin. Check whether this price gives "
            "the business enough room after other costs."
        )

    if margin < 5:
        return (
            "Moderate margin. Competition and product movement "
            "still matter when deciding whether to change the price."
        )

    return (
        "The current price provides more room for profit. "
        "Still consider competition and product movement."
    )


def find_header_row(raw_data):
    expected_columns = {
        "Date",
        "Num",
        "Memo",
        "Item",
        "Qty",
        "U/M",
        "Cost Price"
    }

    maximum_rows = min(20, len(raw_data))

    for row_number in range(maximum_rows):

        values = {
            clean_column_name(value)
            for value in raw_data.iloc[row_number].tolist()
        }

        matches = len(
            expected_columns.intersection(values)
        )

        if matches >= 4:
            return row_number

    return 0


# ============================================================
# SESSION STATE
# ============================================================

if "purchase_data" not in st.session_state:
    st.session_state.purchase_data = None

if "pricing_data" not in st.session_state:
    st.session_state.pricing_data = None

if "invoice_name" not in st.session_state:
    st.session_state.invoice_name = None

if "pricing_strategy" not in st.session_state:
    st.session_state.pricing_strategy = None

if "pricing_notes" not in st.session_state:
    st.session_state.pricing_notes = ""


# ============================================================
# 1. UPLOAD PURCHASE INVOICE
# ============================================================

st.header("1. Upload Purchase Invoice")

uploaded_file = st.file_uploader(
    "Upload the Excel file exported from QuickBooks",
    type=["xlsx", "xls"]
)


if uploaded_file is not None:

    # Process a new file only when the filename changes.
    if st.session_state.invoice_name != uploaded_file.name:

        try:

            # ------------------------------------------------
            # READ EXCEL WITHOUT ASSUMING HEADER POSITION
            # ------------------------------------------------

            raw_data = pd.read_excel(
                uploaded_file,
                sheet_name=0,
                header=None
            )

            header_row = find_header_row(raw_data)

            # ------------------------------------------------
            # READ AGAIN USING THE CORRECT HEADER
            # ------------------------------------------------

            data = pd.read_excel(
                uploaded_file,
                sheet_name=0,
                header=header_row
            )

            # ------------------------------------------------
            # CLEAN COLUMN NAMES
            # ------------------------------------------------

            data.columns = [
                clean_column_name(column)
                for column in data.columns
            ]

            # ------------------------------------------------
            # CHECK REQUIRED COLUMNS
            # ------------------------------------------------

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

                st.write("Columns detected in the file:")

                st.write(
                    list(data.columns)
                )

                st.stop()

            # ------------------------------------------------
            # CLEAN TEXT COLUMNS
            # ------------------------------------------------

            text_columns = [
                "Date",
                "Num",
                "Memo",
                "Item",
                "U/M"
            ]

            for column in text_columns:

                data[column] = (
                    data[column]
                    .apply(clean_text)
                )

            # ------------------------------------------------
            # CLEAN NUMERIC COLUMNS
            # ------------------------------------------------

            data["Qty"] = pd.to_numeric(
                data["Qty"],
                errors="coerce"
            )

            data["Cost Price"] = pd.to_numeric(
                data["Cost Price"],
                errors="coerce"
            )

            # ------------------------------------------------
            # REMOVE EMPTY/TOTAL ROWS
            # ------------------------------------------------

            data = data[
                data["Memo"] != ""
            ].copy()

            data = data[
                data["Cost Price"].notna()
            ].copy()

            # ------------------------------------------------
            # KEEP ORIGINAL QUICKBOOKS INFORMATION
            # ------------------------------------------------

            purchase_columns = [
                "Date",
                "Num",
                "Memo",
                "Item",
                "Qty",
                "U/M",
                "Cost Price"
            ]

            if "Amount" in data.columns:
                purchase_columns.append("Amount")

            if "Balance" in data.columns:
                purchase_columns.append("Balance")

            purchase_data = data[
                purchase_columns
            ].copy()

            # ------------------------------------------------
            # CREATE PRICING DATA
            # ------------------------------------------------

            pricing_data = pd.DataFrame()

            pricing_data["Product"] = (
                purchase_data["Memo"].values
            )

            pricing_data["Buying Price"] = (
                purchase_data["Cost Price"].values
            )

            pricing_data["Quantity"] = (
                purchase_data["Qty"].values
            )

            pricing_data["Unit"] = (
                purchase_data["U/M"].values
            )

            pricing_data["Current Selling Price"] = 0.0

            pricing_data["Markup"] = np.nan

            pricing_data["Margin"] = np.nan

            pricing_data["Observation"] = (
                "Enter selling price"
            )

            # ------------------------------------------------
            # SAVE FRESH DATA
            # ------------------------------------------------

            st.session_state.purchase_data = (
                purchase_data
            )

            st.session_state.pricing_data = (
                pricing_data
            )

            st.session_state.invoice_name = (
                uploaded_file.name
            )

            st.session_state.pricing_strategy = None

            st.session_state.pricing_notes = ""

            st.success(
                f"{len(pricing_data)} products detected successfully."
            )

        except Exception as error:

            st.error(
                "We could not process this QuickBooks file."
            )

            st.exception(error)


# ============================================================
# 2. PURCHASE REVIEW
# ============================================================

if st.session_state.purchase_data is not None:

    purchase_data = (
        st.session_state.purchase_data
    )

    pricing_data = (
        st.session_state.pricing_data
    )

    st.divider()

    st.header("2. Purchase Review")

    # --------------------------------------------------------
    # INVOICE SUMMARY
    # --------------------------------------------------------

    invoice_number = "—"

    if "Num" in purchase_data.columns:

        numbers = [
            clean_text(value)
            for value in purchase_data["Num"]
            if clean_text(value) != ""
        ]

        if len(numbers) > 0:
            invoice_number = numbers[0]

    invoice_date = "—"

    if "Date" in purchase_data.columns:

        dates = [
            clean_text(value)
            for value in purchase_data["Date"]
            if clean_text(value) != ""
        ]

        if len(dates) > 0:
            invoice_date = dates[0]

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Invoice",
            invoice_number
        )

    with col2:

        st.metric(
            "Invoice Date",
            invoice_date
        )

    with col3:

        st.metric(
            "Products Detected",
            len(pricing_data)
        )

    st.success(
        "Ready for review"
    )

    # --------------------------------------------------------
    # ORIGINAL PURCHASE TABLE
    # --------------------------------------------------------

    st.subheader(
        "Purchase Information"
    )

    st.caption(
        "This is the information imported from your QuickBooks file."
    )

    st.dataframe(
        purchase_data,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 3. PRICING WORKSPACE
# ============================================================

if st.session_state.pricing_data is not None:

    st.divider()

    st.header("3. Pricing Workspace")

    st.caption(
        "Enter the current selling price. "
        "The system calculates profit, markup and margin."
    )

    pricing_data = (
        st.session_state.pricing_data
        .copy()
    )

    # --------------------------------------------------------
    # PRODUCT LOOP
    # --------------------------------------------------------

    for index in pricing_data.index:

        product = clean_text(
            pricing_data.at[
                index,
                "Product"
            ]
        )

        buying_price = float(
            pricing_data.at[
                index,
                "Buying Price"
            ]
        )

        quantity = pricing_data.at[
            index,
            "Quantity"
        ]

        unit = clean_text(
            pricing_data.at[
                index,
                "Unit"
            ]
        )

        st.markdown(
            f"### {product}"
        )

        col1, col2, col3 = st.columns(3)

        # ----------------------------------------------------
        # BUYING PRICE
        # ----------------------------------------------------

        with col1:

            st.write(
                "**Buying Price**"
            )

            st.write(
                f"KES {buying_price:,.2f}"
            )

        # ----------------------------------------------------
        # QUANTITY
        # ----------------------------------------------------

        with col2:

            st.write(
                "**Quantity**"
            )

            if pd.isna(quantity):

                st.write(
                    f"— {unit}"
                )

            else:

                st.write(
                    f"{quantity:g} {unit}"
                )

        # ----------------------------------------------------
        # SELLING PRICE
        # ----------------------------------------------------

        with col3:

            selling_price = st.number_input(
                "Current Selling Price (KES)",
                min_value=0.0,
                step=1.0,
                value=float(
                    pricing_data.at[
                        index,
                        "Current Selling Price"
                    ]
                ),
                key=f"selling_price_{index}"
            )

        # ----------------------------------------------------
        # CALCULATE
        # ----------------------------------------------------

        if selling_price > 0:

            profit = (
                selling_price
                - buying_price
            )

            markup = calculate_markup(
                buying_price,
                selling_price
            )

            margin = calculate_margin(
                buying_price,
                selling_price
            )

            observation = get_observation(
                margin
            )

            pricing_data.at[
                index,
                "Current Selling Price"
            ] = selling_price

            pricing_data.at[
                index,
                "Markup"
            ] = markup

            pricing_data.at[
                index,
                "Margin"
            ] = margin

            pricing_data.at[
                index,
                "Observation"
            ] = observation

            # ------------------------------------------------
            # RESULTS
            # ------------------------------------------------

            result1, result2, result3 = st.columns(3)

            with result1:

                st.metric(
                    "Profit per Unit",
                    f"KES {profit:,.2f}"
                )

            with result2:

                st.metric(
                    "Markup",
                    f"{markup:.2f}%"
                )

            with result3:

                st.metric(
                    "Margin",
                    f"{margin:.2f}%"
                )

            st.info(
                f"**Pricing observation:** {observation}"
            )

        else:

            st.caption(
                "Enter the current selling price "
                "to calculate the pricing information."
            )

        st.divider()

    # --------------------------------------------------------
    # SAVE PRICING DATA
    # --------------------------------------------------------

    st.session_state.pricing_data = (
        pricing_data
    )


# ============================================================
# 4. PRICING APPROACH
# ============================================================

if st.session_state.pricing_data is not None:

    st.header(
        "4. How Do You Normally Price?"
    )

    st.caption(
        "We want to understand how you already make pricing decisions."
    )

    strategy_options = [
        "I follow the market",
        "I add a fixed amount",
        "I use a percentage markup",
        "I check competitors",
        "I price differently for different customers",
        "I mainly use my experience",
        "Other"
    ]

    selected_strategy = st.radio(
        "Choose the approach that best describes you:",
        strategy_options
    )

    pricing_notes = st.text_area(
        "Anything else do you consider?",
        value=st.session_state.pricing_notes,
        placeholder=(
            "For example: customer relationships, "
            "fast-moving products, competition, "
            "supplier prices or transport costs."
        )
    )

    if st.button(
        "Save Pricing Approach",
        type="primary"
    ):

        st.session_state.pricing_strategy = (
            selected_strategy
        )

        st.session_state.pricing_notes = (
            pricing_notes
        )

        st.success(
            "Pricing approach saved."
        )


# ============================================================
# 5. SIMPLE PRICING SUMMARY
# ============================================================

if st.session_state.pricing_data is not None:

    st.divider()

    st.header(
        "5. Pricing Summary"
    )

    summary = (
        st.session_state.pricing_data
        .copy()
    )

    summary_columns = [
        "Product",
        "Buying Price",
        "Current Selling Price",
        "Markup",
        "Margin",
        "Observation"
    ]

    summary_display = summary[
        summary_columns
    ].copy()

    # --------------------------------------------------------
    # FORMAT DISPLAY
    # --------------------------------------------------------

    summary_display["Buying Price"] = (
        summary_display["Buying Price"]
        .apply(
            lambda x: (
                f"KES {x:,.2f}"
                if pd.notna(x)
                else "—"
            )
        )
    )

    summary_display["Current Selling Price"] = (
        summary_display["Current Selling Price"]
        .apply(
            lambda x: (
                f"KES {x:,.2f}"
                if pd.notna(x) and x > 0
                else "—"
            )
        )
    )

    summary_display["Markup"] = (
        summary_display["Markup"]
        .apply(
            lambda x: (
                f"{x:.2f}%"
                if pd.notna(x)
                else "—"
            )
        )
    )

    summary_display["Margin"] = (
        summary_display["Margin"]
        .apply(
            lambda x: (
                f"{x:.2f}%"
                if pd.notna(x)
                else "—"
            )
        )
    )

    st.dataframe(
        summary_display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PRODUCT PRINCIPLE
# ============================================================

st.divider()

st.caption(
    "The system supports the wholesaler's decision. "
    "It does not replace the owner's judgement."
)
