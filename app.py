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
    """Clean Excel text safely."""
    if pd.isna(value):
        return ""
    return str(value).replace("\xa0", " ").strip()


def normalize_column(value):
    """Normalize Excel column names."""
    return (
        clean_text(value)
        .replace("\n", " ")
        .replace("  ", " ")
        .strip()
    )


def find_header_row(raw_data):
    """
    Find the actual QuickBooks header row.
    This protects us from blank rows above the Excel table.
    """

    expected = {
        "Date",
        "Num",
        "Memo",
        "Item",
        "Qty",
        "U/M",
        "Cost Price"
    }

    for row_number in range(
        min(20, len(raw_data))
    ):

        row_values = {
            normalize_column(value)
            for value in raw_data.iloc[row_number].tolist()
        }

        matches = len(
            expected.intersection(row_values)
        )

        if matches >= 4:
            return row_number

    return 0


def calculate_markup(
    buying_price,
    selling_price
):
    """Markup = profit / buying price."""

    if buying_price <= 0 or selling_price <= 0:
        return np.nan

    profit = selling_price - buying_price

    return (
        profit / buying_price
    ) * 100


def calculate_margin(
    buying_price,
    selling_price
):
    """Margin = profit / selling price."""

    if selling_price <= 0:
        return np.nan

    profit = selling_price - buying_price

    return (
        profit / selling_price
    ) * 100


def pricing_observation(
    margin,
    markup
):
    """Simple V1 human-readable observation."""

    if pd.isna(margin):

        return (
            "Enter your current selling price "
            "to see your pricing position."
        )

    if margin < 1:

        return (
            "Very thin margin. Consider your operating "
            "costs, customer expectations and how quickly "
            "this product moves."
        )

    if margin < 3:

        return (
            "Thin margin. Check whether this price gives "
            "the business enough room after other costs."
        )

    if margin < 5:

        return (
            "Moderate margin. Your price provides some room, "
            "but competition and product movement still matter."
        )

    return (
        "Healthy room in the current selling price. "
        "Still consider competition and how quickly the "
        "product moves."
    )


# ============================================================
# SESSION STATE
# ============================================================

if "purchase_data" not in st.session_state:
    st.session_state.purchase_data = None

if "pricing_data" not in st.session_state:
    st.session_state.pricing_data = None

if "pricing_strategy" not in st.session_state:
    st.session_state.pricing_strategy = {}

if "invoice_name" not in st.session_state:
    st.session_state.invoice_name = ""


# ============================================================
# 1. INVOICE UPLOAD
# ============================================================

st.header("1. Upload Purchase Invoice")

uploaded_file = st.file_uploader(
    "Upload the Excel file exported from QuickBooks",
    type=["xlsx", "xls"],
    help="Use the same QuickBooks Excel format you normally export."
)


if uploaded_file is not None:

    try:

        # ----------------------------------------------------
        # READ RAW EXCEL
        # ----------------------------------------------------

        raw_data = pd.read_excel(
            uploaded_file,
            sheet_name=0,
            header=None
        )

        # ----------------------------------------------------
        # FIND ACTUAL HEADER
        # ----------------------------------------------------

        header_row = find_header_row(
            raw_data
        )

        data = pd.read_excel(
            uploaded_file,
            sheet_name=0,
            header=header_row
        )

        data.columns = [
            normalize_column(column)
            for column in data.columns
        ]

        # Remove completely empty rows
        data = data.dropna(
            how="all"
        ).copy()

        # ----------------------------------------------------
        # REQUIRED QUICKBOOKS COLUMNS
        # ----------------------------------------------------

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
                "The QuickBooks structure could not be "
                "fully recognized."
            )

            st.write(
                "Columns detected:"
            )

            st.write(
                list(data.columns)
            )

            st.stop()

        # ----------------------------------------------------
        # CLEAN DATA
        # ----------------------------------------------------

        for column in [
            "Date",
            "Num",
            "Memo",
            "Item",
            "U/M"
        ]:

            data[column] = (
                data[column]
                .apply(clean_text)
            )

        data["Qty"] = pd.to_numeric(
            data["Qty"],
            errors="coerce"
        )

        data["Cost Price"] = pd.to_numeric(
            data["Cost Price"],
            errors="coerce"
        )

        if "Amount" in data.columns:

            data["Amount"] = pd.to_numeric(
                data["Amount"],
                errors="coerce"
            )

        if "Balance" in data.columns:

            data["Balance"] = pd.to_numeric(
                data["Balance"],
                errors="coerce"
            )

        # ----------------------------------------------------
        # REMOVE QUICKBOOKS TOTAL / EMPTY ROWS
        # ----------------------------------------------------

        data = data[
            data["Memo"].astype(str).str.strip() != ""
        ].copy()

        data = data[
            data["Cost Price"].notna()
        ].copy()

        # ----------------------------------------------------
        # CREATE CLEAN PURCHASE TABLE
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CREATE PRICING TABLE
        # ----------------------------------------------------

        pricing_data = pd.DataFrame()

        pricing_data["Product"] = (
            purchase_data["Memo"]
        )

        pricing_data["Buying Price"] = (
            purchase_data["Cost Price"]
        )

        pricing_data["Qty"] = (
            purchase_data["Qty"]
        )

        pricing_data["U/M"] = (
            purchase_data["U/M"]
        )

        pricing_data["Current Selling Price"] = 0.0

        pricing_data["Markup"] = np.nan

        pricing_data["Margin"] = np.nan

        pricing_data["Pricing Approach"] = ""

        pricing_data["Observation"] = (
            "Enter selling price"
        )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        st.session_state.purchase_data = (
            purchase_data
        )

        st.session_state.pricing_data = (
            pricing_data
        )

        st.session_state.invoice_name = (
            uploaded_file.name
        )

        st.success(
            f"{len(pricing_data)} products detected successfully."
        )

    except Exception as error:

        st.error(
            f"We could not process this QuickBooks file: {error}"
        )


# ============================================================
# 2. INVOICE SUMMARY
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
    # SUMMARY
    # --------------------------------------------------------

    invoice_number = "—"

    if "Num" in purchase_data.columns:

        numbers = [
            value
            for value in purchase_data["Num"].tolist()
            if clean_text(value)
        ]

        if numbers:
            invoice_number = numbers[0]

    invoice_date = "—"

    if "Date" in purchase_data.columns:

        dates = purchase_data["Date"].dropna()

        if not dates.empty:
            invoice_date = clean_text(
                dates.iloc[0]
            )

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
    # ORIGINAL QUICKBOOKS INFORMATION
    # --------------------------------------------------------

    st.subheader(
        "Purchase Information"
    )

    st.caption(
        "This keeps the information from your QuickBooks "
        "export visible and familiar."
    )

    purchase_display = purchase_data.copy()

    st.dataframe(
        purchase_display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 3. PRICING WORKSPACE
# ============================================================

if st.session_state.pricing_data is not None:

    pricing_data = (
        st.session_state.pricing_data
        .copy()
    )

    st.divider()

    st.header("3. Pricing Workspace")

    st.caption(
        "Enter the current selling price. "
        "Markup and margin are calculated automatically."
    )

    # --------------------------------------------------------
    # PRODUCT PRICING INPUT
    # --------------------------------------------------------

    for index in pricing_data.index:

        product = pricing_data.at[
            index,
            "Product"
        ]

        buying_price = float(
            pricing_data.at[
                index,
                "Buying Price"
            ]
        )

        quantity = pricing_data.at[
            index,
            "Qty"
        ]

        unit = pricing_data.at[
            index,
            "U/M"
        ]

        with st.container():

            st.markdown(
                f"### {product}"
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                st.write(
                    "**Buying Price**"
                )

                st.write(
                    f"KES {buying_price:,.2f}"
                )

            with col2:

                st.write(
                    "**Quantity**"
                )

                st.write(
                    f"{quantity:g} {unit}"
                )

            with col3:

                current_price = st.number_input(
                    "Current Selling Price",
                    min_value=0.0,
                    value=float(
                        pricing_data.at[
                            index,
                            "Current Selling Price"
                        ]
                    ),
                    step=1.0,
                    key=f"selling_{index}"
                )

            # ------------------------------------------------
            # CALCULATIONS
            # ------------------------------------------------

            if current_price > 0:

                markup = calculate_markup(
                    buying_price,
                    current_price
                )

                margin = calculate_margin(
                    buying_price,
                    current_price
                )

                pricing_data.at[
                    index,
                    "Current Selling Price"
                ] = current_price

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
                ] = pricing_observation(
                    margin,
                    markup
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Profit",
                        f"KES {current_price - buying_price:,.2f}"
                    )

                with col2:

                    st.metric(
                        "Markup",
                        f"{markup:.2f}%"
                    )

                with col3:

                    st.metric(
                        "Margin",
                        f"{margin:.2f}%"
                    )

                st.info(
                    f"**Pricing observation:** "
                    f"{pricing_data.at[index, 'Observation']}"
                )

            else:

                st.caption(
                    "Enter the current selling price "
                    "to calculate markup and margin."
                )

            st.divider()


    # ========================================================
    # SAVE CURRENT PRICES
    # ========================================================

    st.session_state.pricing_data = (
        pricing_data
    )


# ============================================================
# 4. PRICING STRATEGY
# ============================================================

if st.session_state.pricing_data is not None:

    pricing_data = (
        st.session_state.pricing_data
    )

    st.header("4. How Do You Normally Price?")

    st.caption(
        "We want to understand how you already make pricing decisions. "
        "The system should learn from your experience rather than "
        "replace it."
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
        strategy_options,
        key="pricing_strategy_main"
    )

    notes = st.text_area(
        "Anything else you consider when setting prices?",
        placeholder=(
            "For example: fast-moving products, "
            "regular customers, supplier price changes, "
            "competition, transport costs..."
        )
    )

    if st.button(
        "Save Pricing Approach",
        type="primary"
    ):

        st.session_state.pricing_strategy[
            "general"
        ] = selected_strategy

        st.session_state.pricing_strategy[
            "notes"
        ] = notes

        st.success(
            "Your pricing approach has been saved."
        )


# ============================================================
# 5. FINAL PRICING VIEW
# ============================================================

if st.session_state.pricing_data is not None:

    st.divider()

    st.header("5. Pricing Summary")

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

    st.dataframe(
        summary_display,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "The current version does not recommend a selling price yet. "
        "It first learns how the wholesaler actually prices products."
    )


# ============================================================
# PRODUCT PRINCIPLE
# ============================================================

st.divider()

st.caption(
    "The wholesaler remains in control. "
    "The system calculates, organizes and explains — "
    "the owner makes the final pricing decision."
)
