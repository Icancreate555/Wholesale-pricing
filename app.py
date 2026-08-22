import streamlit as st
import pandas as pd
import os
from datetime import datetime


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.caption(
    "Your purchase data, market evidence and pricing decision in one place."
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).replace("\xa0", " ").strip()


def normalize_text(value):
    return (
        clean_text(value)
        .upper()
        .replace("  ", " ")
    )


def calculate_margin(buying_price, selling_price):
    if selling_price <= 0:
        return None

    return (
        (selling_price - buying_price)
        / selling_price
    ) * 100


# ============================================================
# EVIDENCE ENGINE
# ============================================================

def load_evidence():

    file_name = "market_evidence.csv"

    if not os.path.exists(file_name):
        return pd.DataFrame()

    try:

        evidence = pd.read_csv(file_name)

        evidence.columns = (
            evidence.columns
            .astype(str)
            .str.strip()
        )

        required_columns = [
            "product",
            "pack_size",
            "location",
            "price",
            "unit",
            "date",
            "source",
            "source_type",
            "evidence_strength",
            "geographic_relevance"
        ]

        for column in required_columns:

            if column not in evidence.columns:
                evidence[column] = ""

        evidence["price"] = pd.to_numeric(
            evidence["price"],
            errors="coerce"
        )

        evidence = evidence.dropna(
            subset=["price"]
        ).copy()

        return evidence

    except Exception as error:

        st.warning(
            f"Evidence database could not be loaded: {error}"
        )

        return pd.DataFrame()


def source_score(source_type):

    source_type = normalize_text(
        source_type
    )

    if source_type in [
        "OFFICIAL",
        "WHOLESALER"
    ]:
        return 3

    if source_type == "SUPPLIER":
        return 2

    if source_type == "COMMERCIAL":
        return 1

    if source_type == "RETAIL":
        return 0

    return 0


def geography_score(location, relevance):

    location = normalize_text(location)
    relevance = normalize_text(relevance)

    if relevance == "CORE LOCAL":
        return 3

    if relevance == "KARATINA-NYERI CORRIDOR":
        return 2

    if relevance == "WIDER / OTHER":
        return 1

    if (
        "KARATINA" in location
        or "NYERI" in location
    ):
        return 3

    return 0


def evidence_quality(row):

    score = 0

    strength = normalize_text(
        row.get("evidence_strength", "")
    )

    if strength == "HIGH":
        score += 3

    elif strength == "MEDIUM":
        score += 2

    elif strength == "LOW":
        score += 1

    score += source_score(
        row.get("source_type", "")
    )

    score += geography_score(
        row.get("location", ""),
        row.get("geographic_relevance", "")
    )

    return score


def get_product_evidence(
    product,
    evidence
):

    if evidence.empty:

        return {
            "local": pd.DataFrame(),
            "broader": pd.DataFrame(),
            "range": "Awaiting verified local evidence",
            "status": "Awaiting evidence"
        }

    product_key = normalize_text(
        product
    )

    matches = evidence[
        evidence["product"]
        .apply(normalize_text)
        == product_key
    ].copy()

    if matches.empty:

        return {
            "local": pd.DataFrame(),
            "broader": pd.DataFrame(),
            "range": "Awaiting verified local evidence",
            "status": "Awaiting evidence"
        }

    matches["quality_score"] = (
        matches.apply(
            evidence_quality,
            axis=1
        )
    )

    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    local = matches[
        (
            matches["geographic_relevance"]
            .apply(normalize_text)
            .isin(
                [
                    "CORE LOCAL",
                    "KARATINA-NYERI CORRIDOR"
                ]
            )
        )
        &
        (
            matches["quality_score"] >= 5
        )
    ].copy()

    # --------------------------------------------------------
    # BROADER
    # --------------------------------------------------------

    broader = matches[
        matches["quality_score"] >= 4
    ].copy()

    # --------------------------------------------------------
    # LOCAL RANGE
    # --------------------------------------------------------

    if len(local) >= 2:

        lowest = local["price"].min()
        highest = local["price"].max()

        return {
            "local": local,
            "broader": broader,
            "range": (
                f"KES {lowest:,.2f} – "
                f"KES {highest:,.2f}"
            ),
            "status": "Local evidence available"
        }

    # --------------------------------------------------------
    # BROADER REFERENCE
    # --------------------------------------------------------

    if len(broader) >= 2:

        lowest = broader["price"].min()
        highest = broader["price"].max()

        return {
            "local": local,
            "broader": broader,
            "range": (
                f"KES {lowest:,.2f} – "
                f"KES {highest:,.2f}"
            ),
            "status": "Broader reference only"
        }

    return {
        "local": local,
        "broader": broader,
        "range": "Insufficient verified evidence",
        "status": "Insufficient evidence"
    }


# ============================================================
# LOAD EVIDENCE DATABASE
# ============================================================

market_evidence = load_evidence()


# ============================================================
# QUICKBOOKS IMPORT
# ============================================================

st.subheader("1. Upload Purchase File")

uploaded_file = st.file_uploader(
    "Upload your QuickBooks Excel file",
    type=["xlsx", "xls"]
)


if uploaded_file is not None:

    try:

        data = pd.read_excel(
            uploaded_file,
            sheet_name="Sheet1",
            header=0
        )

        data.columns = (
            data.columns
            .astype(str)
            .str.replace(
                "\xa0",
                " ",
                regex=False
            )
            .str.strip()
        )

        data = data.dropna(
            how="all"
        ).copy()

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
                "Missing columns: "
                + ", ".join(missing_columns)
            )

            st.stop()

        data["Memo"] = (
            data["Memo"]
            .apply(clean_text)
        )

        data["Item"] = (
            data["Item"]
            .apply(clean_text)
        )

        data["Cost Price"] = pd.to_numeric(
            data["Cost Price"],
            errors="coerce"
        )

        data["Qty"] = pd.to_numeric(
            data["Qty"],
            errors="coerce"
        )

        data = data[
            data["Memo"] != ""
        ].copy()

        data = data[
            data["Cost Price"].notna()
        ].copy()


        # ====================================================
        # CREATE PRICING WORKSPACE
        # ====================================================

        pricing_data = pd.DataFrame()

        pricing_data["Product"] = data["Memo"]

        pricing_data["Item"] = data["Item"]

        pricing_data["Buying Price"] = (
            data["Cost Price"]
        )

        pricing_data["Quantity"] = data["Qty"]

        pricing_data["Unit"] = data["U/M"]

        pricing_data["Purchase Date"] = data["Date"]

        pricing_data["Current Selling Price"] = None

        pricing_data["Margin"] = None

        pricing_data["Market Range"] = (
            "Awaiting verified local evidence"
        )

        pricing_data["Evidence Status"] = (
            "Awaiting evidence"
        )


        # ====================================================
        # MATCH MARKET EVIDENCE
        # ====================================================

        for index, row in pricing_data.iterrows():

            result = get_product_evidence(
                row["Product"],
                market_evidence
            )

            pricing_data.at[
                index,
                "Market Range"
            ] = result["range"]

            pricing_data.at[
                index,
                "Evidence Status"
            ] = result["status"]


        st.session_state[
            "pricing_data"
        ] = pricing_data


        st.success(
            f"{len(pricing_data)} products imported successfully."
        )


    except Exception as error:

        st.error(
            f"We could not process the QuickBooks file: {error}"
        )


# ============================================================
# PRICING WORKSPACE
# ============================================================

if "pricing_data" in st.session_state:

    pricing_data = st.session_state[
        "pricing_data"
    ]

    st.divider()

    st.subheader("2. Pricing Workspace")

    display_columns = [
        "Product",
        "Buying Price",
        "Quantity",
        "Unit",
        "Market Range",
        "Evidence Status",
        "Current Selling Price",
        "Margin"
    ]

    st.dataframe(
        pricing_data[display_columns],
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # OWNER DECISION
    # ========================================================

    st.divider()

    st.subheader("3. Owner Pricing Decision")

    selected_product = st.selectbox(
        "Select a product",
        pricing_data["Product"].tolist()
    )

    selected_index = pricing_data[
        pricing_data["Product"]
        == selected_product
    ].index[0]

    selected_row = pricing_data.loc[
        selected_index
    ]


    # --------------------------------------------------------
    # PRODUCT SUMMARY
    # --------------------------------------------------------

    st.markdown(
        f"### {selected_product}"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Buying Price",
            f"KES {selected_row['Buying Price']:,.2f}"
        )

    with col2:

        st.metric(
            "Quantity",
            f"{selected_row['Quantity']:g}"
        )

    with col3:

        st.metric(
            "Evidence",
            selected_row["Evidence Status"]
        )


    st.write(
        f"**Observed Market Range:** "
        f"{selected_row['Market Range']}"
    )


    # ========================================================
    # SELLING PRICE
    # ========================================================

    selling_price = st.number_input(
        "Your Current Selling Price (KES)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f"
    )


    if selling_price > 0:

        buying_price = float(
            selected_row["Buying Price"]
        )

        profit = (
            selling_price
            - buying_price
        )

        margin = calculate_margin(
            buying_price,
            selling_price
        )


        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Profit per Unit",
                f"KES {profit:,.2f}"
            )

        with col2:

            st.metric(
                "Current Margin",
                f"{margin:.2f}%"
            )


        # ====================================================
        # HUMAN-CENTRED PRICING REASONING
        # ====================================================

        if margin < 1:

            advice = (
                "This is a very thin margin. "
                "Before changing the price, consider "
                "your operating costs and how important "
                "this product is for customer retention."
            )

        elif margin < 3:

            advice = (
                "Your margin is thin. "
                "Consider competition, operating costs "
                "and how quickly this product moves."
            )

        elif margin < 5:

            advice = (
                "Your margin is moderate. "
                "Check whether your price remains competitive "
                "while still giving the business room to operate."
            )

        else:

            advice = (
                "Your margin provides more room for profit. "
                "Still check the market before making a price change."
            )


        st.info(
            f"**System observation:** {advice}"
        )


        # ====================================================
        # EVIDENCE MESSAGE
        # ====================================================

        status = selected_row[
            "Evidence Status"
        ]

        if status == "Local evidence available":

            st.success(
                "Verified local evidence is available. "
                "Use the range as a reference, not an instruction."
            )

        elif status == "Broader reference only":

            st.warning(
                "Broader market evidence exists, but it has "
                "not been treated as a Karatina–Nyeri local range."
            )

        elif status == "Insufficient evidence":

            st.warning(
                "There is some evidence, but not enough "
                "to establish a reliable market range."
            )

        else:

            st.info(
                "The system is waiting for verified market evidence."
            )


        # ====================================================
        # OWNER SAVE
        # ====================================================

        if st.button(
            "Save Selling Price",
            type="primary"
        ):

            pricing_data.at[
                selected_index,
                "Current Selling Price"
            ] = selling_price

            pricing_data.at[
                selected_index,
                "Margin"
            ] = margin

            st.session_state[
                "pricing_data"
            ] = pricing_data

            st.success(
                f"Saved KES {selling_price:,.2f} "
                f"for {selected_product}."
            )


# ============================================================
# EVIDENCE PANEL
# ============================================================

st.divider()

st.subheader("Market Evidence")

if market_evidence.empty:

    st.info(
        "No verified market evidence has been added yet."
    )

else:

    st.caption(
        "Evidence is kept separate from the owner's pricing decision."
    )

    evidence_columns = [
        "product",
        "pack_size",
        "location",
        "price",
        "unit",
        "date",
        "source",
        "source_type",
        "evidence_strength",
        "geographic_relevance"
    ]

    st.dataframe(
        market_evidence[evidence_columns],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PRINCIPLE
# ============================================================

st.divider()

st.caption(
    "The system is a pricing partner: it brings evidence and reasoning; "
    "the wholesaler retains the final decision."
)
