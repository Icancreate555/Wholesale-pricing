import streamlit as st
import pandas as pd
import os
from datetime import date


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Wholesale Pricing Intelligence",
    layout="wide"
)

st.title("Wholesale Pricing Intelligence")

st.caption(
    "Purchase data → market intelligence → competitiveness "
    "→ movement → pricing strategy"
)


# ============================================================
# FILES
# ============================================================

EVIDENCE_FILE = "market_evidence.csv"

SOURCE_FILE = "source_registry.csv"


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if pd.isna(value):
        return ""

    return (
        str(value)
        .replace("\xa0", " ")
        .strip()
    )


def normalize_text(value):

    return (
        clean_text(value)
        .upper()
        .replace("  ", " ")
    )


def calculate_margin(
    buying_price,
    selling_price
):

    if selling_price <= 0:

        return None

    return (
        (selling_price - buying_price)
        / selling_price
    ) * 100


# ============================================================
# SOURCE REGISTRY
# ============================================================

def load_sources():

    if not os.path.exists(
        SOURCE_FILE
    ):

        return pd.DataFrame()

    try:

        sources = pd.read_csv(
            SOURCE_FILE
        )

        sources.columns = (
            sources.columns
            .astype(str)
            .str.strip()
        )

        return sources

    except Exception as error:

        st.warning(
            f"Source registry error: {error}"
        )

        return pd.DataFrame()


source_registry = load_sources()


# ============================================================
# EVIDENCE DATABASE
# ============================================================

def empty_evidence():

    return pd.DataFrame(

        columns=[

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

    )


def load_evidence():

    if not os.path.exists(
        EVIDENCE_FILE
    ):

        return empty_evidence()

    try:

        evidence = pd.read_csv(
            EVIDENCE_FILE
        )

        required = [

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

        for column in required:

            if column not in evidence.columns:

                evidence[column] = ""

        evidence["price"] = pd.to_numeric(
            evidence["price"],
            errors="coerce"
        )

        evidence = evidence.dropna(
            subset=["price"]
        )

        return evidence

    except Exception as error:

        st.warning(
            f"Evidence database error: {error}"
        )

        return empty_evidence()


def save_evidence(
    evidence
):

    evidence.to_csv(
        EVIDENCE_FILE,
        index=False
    )


market_evidence = load_evidence()


# ============================================================
# EVIDENCE SCORING
# ============================================================

def source_score(
    source_type
):

    source_type = normalize_text(
        source_type
    )

    scores = {

        "OFFICIAL": 3,

        "WHOLESALER": 3,

        "SUPPLIER": 2,

        "COMMERCIAL": 1,

        "RETAIL": 0

    }

    return scores.get(
        source_type,
        0
    )


def geography_score(
    location,
    relevance
):

    location = normalize_text(
        location
    )

    relevance = normalize_text(
        relevance
    )

    if relevance in [

        "CORE LOCAL",

        "KARATINA-NYERI CORRIDOR"

    ]:

        return 3

    if (

        "KARATINA" in location

        or

        "NYERI" in location

    ):

        return 3

    if relevance == "WIDER / OTHER":

        return 1

    return 0


def strength_score(
    strength
):

    strength = normalize_text(
        strength
    )

    scores = {

        "HIGH": 3,

        "MEDIUM": 2,

        "LOW": 1

    }

    return scores.get(
        strength,
        0
    )


def evidence_quality(
    row
):

    return (

        source_score(
            row.get(
                "source_type",
                ""
            )
        )

        +

        geography_score(
            row.get(
                "location",
                ""
            ),

            row.get(
                "geographic_relevance",
                ""
            )
        )

        +

        strength_score(
            row.get(
                "evidence_strength",
                ""
            )
        )

    )


# ============================================================
# MARKET INTELLIGENCE
# ============================================================

def market_intelligence(
    product,
    evidence
):

    result = {

        "low": None,

        "high": None,

        "median": None,

        "spread": None,

        "count": 0,

        "confidence": "None",

        "trend": "Unknown",

        "status": "No evidence",

        "sources": []

    }


    if evidence.empty:

        return result


    matches = evidence[

        evidence["product"]
        .apply(normalize_text)

        ==

        normalize_text(product)

    ].copy()


    if matches.empty:

        return result


    matches["quality"] = (
        matches.apply(
            evidence_quality,
            axis=1
        )
    )


    local = matches[

        matches[
            "geographic_relevance"
        ]
        .apply(normalize_text)
        .isin([

            "CORE LOCAL",

            "KARATINA-NYERI CORRIDOR"

        ])

    ].copy()


    local = local[
        local["quality"] >= 5
    ]


    if len(local) >= 2:

        working = local

        status = (
            "Local evidence available"
        )

    else:

        broader = matches[
            matches["quality"] >= 4
        ]

        if len(broader) >= 2:

            working = broader

            status = (
                "Broader reference only"
            )

        else:

            return result


    prices = working[
        "price"
    ]


    result["low"] = prices.min()

    result["high"] = prices.max()

    result["median"] = prices.median()

    result["spread"] = (

        result["high"]

        -

        result["low"]

    )

    result["count"] = len(
        working
    )

    result["status"] = status


    result["sources"] = (
        working["source"]
        .dropna()
        .unique()
        .tolist()
    )


    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    if len(working) >= 5:

        result["confidence"] = "High"

    elif len(working) >= 3:

        result["confidence"] = "Medium"

    else:

        result["confidence"] = "Low"


    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    working["date_parsed"] = pd.to_datetime(

        working["date"],

        errors="coerce"

    )


    dated = working.dropna(
        subset=["date_parsed"]
    ).sort_values(
        "date_parsed"
    )


    if len(dated) >= 3:

        half = max(
            1,
            len(dated) // 2
        )

        older = dated.head(
            half
        )["price"].mean()

        recent = dated.tail(
            half
        )["price"].mean()


        if recent > older * 1.02:

            result["trend"] = "Rising"

        elif recent < older * 0.98:

            result["trend"] = "Falling"

        else:

            result["trend"] = "Stable"


    return result


# ============================================================
# MOVEMENT
# ============================================================

def movement_class(
    quantity
):

    if quantity >= 50:

        return "Fast"

    if quantity >= 10:

        return "Medium"

    return "Slow"


# ============================================================
# COMPETITIVENESS
# ============================================================

def competitive_pressure(
    intelligence
):

    if (

        intelligence["median"] is None

        or

        intelligence["median"] <= 0

    ):

        return "Unknown"


    spread_percent = (

        intelligence["spread"]

        /

        intelligence["median"]

    ) * 100


    if spread_percent <= 4:

        return "High"

    if spread_percent <= 8:

        return "Medium"

    return "Low"


# ============================================================
# PRICING STRATEGY
# ============================================================

def pricing_strategy(
    buying_price,
    intelligence,
    movement
):

    # --------------------------------------------------------
    # NO MARKET DATA
    # --------------------------------------------------------

    if intelligence["median"] is None:

        target_margin = 5

        price = (

            buying_price

            /

            (1 - target_margin / 100)

        )

        return {

            "recommended": round(
                price,
                2
            ),

            "target_margin":
                target_margin,

            "reason":
                "No verified market evidence. "
                "Using a temporary cost-based fallback."

        }


    # --------------------------------------------------------
    # MOVEMENT STRATEGY
    # --------------------------------------------------------

    if movement == "Fast":

        target_margin = 3.5

    elif movement == "Medium":

        target_margin = 5

    else:

        target_margin = 7


    cost_floor = (

        buying_price

        /

        (1 - target_margin / 100)

    )


    market_price = (
        intelligence["median"]
    )


    # --------------------------------------------------------
    # RECOMMENDATION
    # --------------------------------------------------------

    recommended = max(

        market_price,

        cost_floor

    )


    if movement == "Fast":

        reason = (

            "Fast-moving product. "
            "The strategy prioritizes "
            "competitive turnover."

        )

    elif movement == "Medium":

        reason = (

            "Medium-moving product. "
            "The strategy balances "
            "margin and competitiveness."

        )

    else:

        reason = (

            "Slow-moving product. "
            "The strategy protects margin "
            "because capital may remain tied up."

        )


    return {

        "recommended":
            round(
                recommended,
                2
            ),

        "target_margin":
            target_margin,

        "reason":
            reason

    }


# ============================================================
# WATCHLIST
# ============================================================

def build_watchlist(
    pricing_data,
    evidence
):

    rows = []


    for product in pricing_data[
        "Product"
    ].unique():

        intel = market_intelligence(
            product,
            evidence
        )


        if (

            intel["count"] < 3

            or

            intel["confidence"]
            == "Low"

        ):

            rows.append({

                "Product":
                    product,

                "Status":
                    "Needs market research"

            })


    return pd.DataFrame(
        rows
    )


# ============================================================
# PURCHASE IMPORT
# ============================================================

st.subheader(
    "1. Today's Purchases"
)


uploaded_file = st.file_uploader(

    "Upload QuickBooks purchase file",

    type=[
        "xlsx",
        "xls"
    ]

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


        required = [

            "Date",
            "Num",
            "Memo",
            "Item",
            "Qty",
            "U/M",
            "Cost Price"

        ]


        missing = [

            c for c in required

            if c not in data.columns

        ]


        if missing:

            st.error(
                "Missing columns: "
                + ", ".join(missing)
            )

            st.stop()


        data["Memo"] = (
            data["Memo"]
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

            (data["Memo"] != "")

            &

            data["Cost Price"].notna()

        ].copy()


        pricing_data = pd.DataFrame({

            "Product":
                data["Memo"],

            "Buying Price":
                data["Cost Price"],

            "Quantity":
                data["Qty"],

            "Unit":
                data["U/M"],

            "Purchase Date":
                data["Date"],

            "Current Selling Price":
                None,

            "Margin":
                None

        })


        st.session_state[
            "pricing_data"
        ] = pricing_data


        st.success(

            f"{len(pricing_data)} "
            "products imported."

        )


    except Exception as error:

        st.error(
            f"Could not process file: {error}"
        )


# ============================================================
# PRICING WORKSPACE
# ============================================================

if "pricing_data" in st.session_state:

    pricing_data = st.session_state[
        "pricing_data"
    ]


    st.divider()

    st.subheader(
        "2. Market Intelligence"
    )


    selected_product = st.selectbox(

        "Select product",

        pricing_data[
            "Product"
        ].tolist()

    )


    selected_index = pricing_data[

        pricing_data["Product"]
        == selected_product

    ].index[0]


    selected_row = pricing_data.loc[
        selected_index
    ]


    intelligence = market_intelligence(

        selected_product,

        market_evidence

    )


    movement = movement_class(

        float(
            selected_row["Quantity"]
        )

    )


    # ========================================================
    # MARKET DISPLAY
    # ========================================================

    if intelligence["median"] is None:

        st.warning(
            "No verified local market evidence "
            "is currently available."
        )

    else:

        c1, c2, c3, c4 = st.columns(4)


        with c1:

            st.metric(

                "Market Low",

                f"KES "
                f"{intelligence['low']:,.2f}"

            )


        with c2:

            st.metric(

                "Market High",

                f"KES "
                f"{intelligence['high']:,.2f}"

            )


        with c3:

            st.metric(

                "Market Median",

                f"KES "
                f"{intelligence['median']:,.2f}"

            )


        with c4:

            st.metric(

                "Evidence",

                intelligence["confidence"]

            )


        st.write(

            f"**Trend:** "
            f"{intelligence['trend']}"

        )


        st.write(

            f"**Competitive pressure:** "
            f"{competitive_pressure(intelligence)}"

        )


        st.write(

            "**Sources:** "

            +

            ", ".join(
                intelligence["sources"]
            )

        )


    # ========================================================
    # MARKET AGENT
    # ========================================================

    st.divider()

    st.subheader(
        "3. Market Intelligence Agent"
    )


    watchlist = build_watchlist(

        pricing_data,

        market_evidence

    )


    if watchlist.empty:

        st.success(
            "All current products have adequate evidence."
        )

    else:

        st.info(

            f"{len(watchlist)} products "
            "require fresh market research."

        )

        st.dataframe(

            watchlist,

            use_container_width=True,

            hide_index=True

        )


    st.button(
        "Run Market Research Agent",
        type="primary"
    )


    st.caption(

        "Live web research will be connected here. "
        "The agent will prioritize KAMIS, then verified "
        "Karatina/Nyeri wholesale sources, then broader "
        "Kenyan sources."

    )


    # ========================================================
    # MOVEMENT
    # ========================================================

    st.divider()

    st.subheader(
        "4. Product Movement"
    )


    st.metric(
        "Movement",
        movement
    )


    # ========================================================
    # PRICING
    # ========================================================

    st.divider()

    st.subheader(
        "5. Pricing Strategy"
    )


    strategy = pricing_strategy(

        float(
            selected_row[
                "Buying Price"
            ]
        ),

        intelligence,

        movement

    )


    st.success(

        f"Recommended Price: "
        f"KES "
        f"{strategy['recommended']:,.2f}"

    )


    st.write(

        f"**Target margin:** "
        f"{strategy['target_margin']:.1f}%"

    )


    st.info(
        strategy["reason"]
    )


    # ========================================================
    # OWNER PRICE
    # ========================================================

    st.divider()

    current_price = st.number_input(

        "Your Current Selling Price (KES)",

        min_value=0.0,

        step=1.0,

        format="%.2f"

    )


    if current_price > 0:

        buying_price = float(

            selected_row[
                "Buying Price"
            ]

        )


        margin = calculate_margin(

            buying_price,

            current_price

        )


        profit = (

            current_price

            -

            buying_price

        )


        c1, c2 = st.columns(2)


        with c1:

            st.metric(

                "Profit",

                f"KES "
                f"{profit:,.2f}"

            )


        with c2:

            st.metric(

                "Margin",

                f"{margin:.2f}%"

            )


        if st.button(
            "Save Owner Price",
            type="secondary"
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
                "Owner price saved."
            )


# ============================================================
# EVIDENCE DATABASE
# ============================================================

st.divider()

st.subheader(
    "6. Market Evidence Database"
)


if market_evidence.empty:

    st.info(
        "No verified market evidence has been collected yet."
    )

else:

    st.dataframe(

        market_evidence,

        use_container_width=True,

        hide_index=True

    )


# ============================================================
# SOURCE REGISTRY
# ============================================================

st.divider()

st.subheader(
    "7. Market Source Registry"
)


if source_registry.empty:

    st.warning(
        "source_registry.csv was not found."
    )

else:

    st.dataframe(

        source_registry,

        use_container_width=True,

        hide_index=True

    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(

    "Market evidence informs the decision. "
    "The wholesaler retains final pricing authority."

)
