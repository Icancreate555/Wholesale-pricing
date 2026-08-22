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
    "A simple pricing workspace that combines purchase information, "
    "market evidence and owner judgement."
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).replace("\xa0", " ").strip()


def normalize_product(value):
    return (
        clean_text(value)
        .upper()
        .replace("  ", " ")
    )


def calculate_margin(buying_price, selling_price):
    if selling_price is None or selling_price <= 0:
        return None

    return (
        (selling_price - buying_price)
        / selling_price
    ) * 100


def classify_geography(location):
    location = clean_text(location).lower()

    if not location:
        return "Unknown"

    karatina_terms = [
        "karatina"
    ]

    nyeri_terms = [
        "nyeri",
        "nyeri town"
    ]

    corridor_terms = [
        "mukurwe-ini",
        "mukurweini",
        "mathira",
        "chaka",
        "kiganjo"
    ]

    if any(term in location for term in karatina_terms):
        return "Core Local"

    if any(term in location for term in nyeri_terms):
        return "Core Local"

    if any(term in location for term in corridor_terms):
        return "Karatina-Nyeri Corridor"

    return "Wider / Other"


def evidence_score(row):
    score = 0

    source_type = clean_text(
        row.get("source_type", "")
    ).lower()

    strength = clean_text(
        row.get("evidence_strength", "")
    ).lower()

    geography = clean_text(
        row.get("geographic_relevance", "")
    ).lower()

    if strength == "high":
        score += 3
    elif strength == "medium":
        score += 2
    elif strength == "low":
        score += 1

    if "official" in source_type:
        score += 3
    elif "wholesaler" in source_type:
        score += 3
    elif "supplier" in source_type:
        score += 2
    elif "commercial" in source_type:
        score += 1
    elif "retail" in source_type:
        score -= 2

    if "core local" in geography:
        score += 3
    elif "corridor" in geography:
        score += 2
    elif "wider" in geography:
        score += 1

    return score


# ============================================================
# MARKET EVIDENCE ENGINE
# ============================================================

def load_market_evidence():

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

        if evidence.empty:
            return evidence

        evidence["geography_class"] = (
            evidence["location"]
            .apply(classify_geography)
        )

        evidence["evidence_score"] = (
            evidence.apply(
                evidence_score,
                axis=1
            )
        )

        return evidence

    except Exception as error:
        st.warning(
            f"Market evidence could not be loaded: {error}"
        )
        return pd.DataFrame()


def get_market_evidence(
    product_name,
    evidence
):

    if evidence.empty:
        return {
            "range": "No verified evidence yet",
            "status": "No evidence",
            "count": 0,
            "sources": []
        }

    product_normalized = normalize_product(
        product_name
    )

    matches = evidence[
        evidence["product"]
        .apply(normalize_product)
        == product_normalized
    ].copy()

    if matches.empty:
        return {
            "range": "No verified evidence yet",
            "status": "No evidence",
            "count": 0,
            "sources": []
        }

    # Only evidence with reasonable confidence
    valid = matches[
        matches["evidence_score"] >= 5
    ].copy()

    # Prefer local evidence
    local = valid[
        valid["geography_class"].isin(
            [
                "Core Local",
                "Karatina-Nyeri Corridor"
            ]
        )
    ].copy()

    if len(local) >= 2:

        lowest = local["price"].min()
        highest = local["price"].max()

        return {
            "range": (
                f"KES {lowest:,.2f} – "
                f"KES {highest:,.2f}"
            ),
            "status": "Local evidence",
            "count": len(local),
            "sources": local["source"].tolist()
        }

    # If local evidence is insufficient,
    # do not pretend wider evidence is local.
    if len(valid) >= 2:

        lowest = valid["price"].min()
        highest = valid["price"].max()

        return {
            "range": (
                f"KES {lowest:,.2f} – "
                f"KES {highest:,.2f}"
            ),
            "status": "Broader reference only",
            "count": len(valid),
            "sources": valid["source"].tolist()
        }

    return {
        "range": "Insufficient evidence",
        "status": "Insufficient evidence",
        "count": len(valid),
        "sources": valid["source"].tolist()
    }


# ============================================================
# LOAD EVIDENCE
# ============================================================

market_evidence = load_market_evidence()


# ============================================================
# QUICKBOOKS UPLOAD
# ============================================================

st.subheader("1. Upload Purchase File")

uploaded_file = st.file_uploader(
    "Upload your QuickBooks Excel file",
    type=["xlsx", "xls"]
)


if uploaded_file is not None:

    try:

        # ----------------------------------------------------
        # READ EXCEL
        # ----------------------------------------------------

        data = pd.read_excel(
            uploaded_file,
            sheet_name="Sheet1",
            header=0
        )

        data.columns = (
            data.columns
            .astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )

        data = data.dropna(
            how="all"
        ).copy()


        # ----------------------------------------------------
        # REQUIRED COLUMNS
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

        missing = [
            column
            for column in required_columns
            if column not in data.columns
        ]

        if missing:

            st.error(
                "Missing columns: "
                + ", ".join(missing)
            )

            st.stop()


        # ----------------------------------------------------
        # CLEAN DATA
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # PRICING TABLE
        # ----------------------------------------------------

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
            "No verified evidence yet"
        )

        pricing_data["Evidence Status"] = (
            "No evidence"
        )


        # ----------------------------------------------------
        # MARKET EVIDENCE
        # ----------------------------------------------------

        for index, row in pricing_data.iterrows():

            evidence_result = get_market_evidence(
                row["Product"],
                market_evidence
            )

            pricing_data.at[
                index,
                "Market Range"
            ] = evidence_result["range"]

            pricing_data.at[
                index,
                "Evidence Status"
            ] = evidence_result["status"]


        # ----------------------------------------------------
        # SAVE IN SESSION
        # ----------------------------------------------------

        st.session_state["pricing_data"] = (
            pricing_data
        )


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

    st.subheader("2. New Purchases")

    st.caption(
        "Your purchase information remains visible. "
        "Market information is shown only when evidence exists."
    )


    # --------------------------------------------------------
    # SIMPLE TABLE
    # --------------------------------------------------------

    display_data = pricing_data[
        [
            "Product",
            "Buying Price",
            "Quantity",
            "Unit",
            "Market Range",
            "Evidence Status",
            "Current Selling Price",
            "Margin"
        ]
    ].copy()

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # OWNER PRICING
    # ========================================================

    st.divider()

    st.subheader("3. Owner Pricing Decision")

    product_list = pricing_data[
        "Product"
    ].tolist()

    selected_product = st.selectbox(
        "Select a product",
        product_list
    )


    selected_index = pricing_data[
        pricing_data["Product"]
        == selected_product
    ].index[0]

    selected_row = pricing_data.loc[
        selected_index
    ]


    # --------------------------------------------------------
    # PRODUCT INFORMATION
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
            "Market Evidence",
            selected_row["Evidence Status"]
        )


    st.write(
        f"**Observed Market Range:** "
        f"{selected_row['Market Range']}"
    )


    # --------------------------------------------------------
    # SELLING PRICE
    # --------------------------------------------------------

    current_price = st.number_input(
        "Your Current Selling Price (KES)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f"
    )


    # --------------------------------------------------------
    # CALCULATE MARGIN
    # --------------------------------------------------------

    if current_price > 0:

        buying_price = float(
            selected_row["Buying Price"]
        )

        profit = (
            current_price
            - buying_price
        )

        margin = calculate_margin(
            buying_price,
            current_price
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


        # ----------------------------------------------------
        # SIMPLE HUMAN-CENTRED REASONING
        # ----------------------------------------------------

        if margin < 1:

            observation = (
                "Your margin is below 1%. "
                "This is a very thin margin and may "
                "leave little room for operating costs."
            )

        elif margin < 3:

            observation = (
                "Your margin is relatively thin. "
                "Consider your costs, competition and "
                "how quickly this product normally moves."
            )

        elif margin < 5:

            observation = (
                "Your margin is moderate. "
                "Consider whether the price remains "
                "competitive in your market."
            )

        else:

            observation = (
                "Your margin provides more room for profit. "
                "Check that the price remains competitive."
            )


        st.info(
            f"**System observation:** {observation}"
        )


        # ----------------------------------------------------
        # EVIDENCE REASONING
        # ----------------------------------------------------

        if selected_row["Evidence Status"] == "Local evidence":

            st.success(
                "Local market evidence is available. "
                "Use it as a reference rather than an instruction."
            )

        elif selected_row[
            "Evidence Status"
        ] == "Broader reference only":

            st.warning(
                "Broader market evidence exists, but it has "
                "not been treated as a Karatina–Nyeri local price."
            )

        elif selected_row[
            "Evidence Status"
        ] == "Insufficient evidence":

            st.warning(
                "There is not enough verified evidence "
                "to establish a reliable market range."
            )

        else:

            st.info(
                "The system is waiting for verified market evidence."
            )


        # ----------------------------------------------------
        # OWNER CONTROL
        # ----------------------------------------------------

        if st.button(
            "Save Selling Price",
            type="primary"
        ):

            pricing_data.at[
                selected_index,
                "Current Selling Price"
            ] = current_price

            pricing_data.at[
                selected_index,
                "Margin"
            ] = margin

            st.session_state[
                "pricing_data"
            ] = pricing_data

            st.success(
                f"Price saved for {selected_product}."
            )


# ============================================================
# MARKET EVIDENCE MANAGEMENT
# ============================================================

st.divider()

st.subheader("Market Evidence")

if market_evidence.empty:

    st.info(
        "No verified market evidence has been added yet. "
        "This is intentional: the system will not invent market prices."
    )

else:

    st.caption(
        "Evidence is separated by geography and source quality."
    )

    evidence_display = market_evidence[
        [
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
    ].copy()

    st.dataframe(
        evidence_display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# SYSTEM PRINCIPLE
# ============================================================

st.divider()

st.caption(
    "The system supports the wholesaler's decision. "
    "It does not replace the owner's judgement."
)
