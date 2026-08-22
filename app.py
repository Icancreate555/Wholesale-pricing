import streamlit as st
import pandas as pd
import os
from datetime import datetime, date


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Wholesale Pricing Intelligence",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")

st.caption(
    "Market intelligence + movement + pricing strategy "
    "for a small wholesale business."
)


# ============================================================
# CONSTANTS
# ============================================================

EVIDENCE_FILE = "market_evidence.csv"

LOCAL_GEOGRAPHIES = [
    "CORE LOCAL",
    "KARATINA-NYERI CORRIDOR"
]


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


def calculate_profit(
    buying_price,
    selling_price
):

    return selling_price - buying_price


# ============================================================
# PHASE 1
# EVIDENCE DATABASE
# ============================================================

def empty_evidence_dataframe():

    return pd.DataFrame(columns=[

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

    ])


def load_evidence():

    if not os.path.exists(EVIDENCE_FILE):

        return empty_evidence_dataframe()

    try:

        evidence = pd.read_csv(
            EVIDENCE_FILE
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
            f"Market evidence could not be loaded: {error}"
        )

        return empty_evidence_dataframe()


def save_evidence(evidence):

    evidence.to_csv(
        EVIDENCE_FILE,
        index=False
    )


# ============================================================
# EVIDENCE SCORING
# ============================================================

def source_score(source_type):

    source_type = normalize_text(
        source_type
    )

    scores = {

        "WHOLESALER": 3,

        "OFFICIAL": 3,

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
        or "NYERI" in location
    ):

        return 3

    if relevance == "WIDER / OTHER":

        return 1

    return 0


def strength_score(
    evidence_strength
):

    strength = normalize_text(
        evidence_strength
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


def evidence_quality(row):

    return (
        strength_score(
            row.get(
                "evidence_strength",
                ""
            )
        )
        +
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
    )


# ============================================================
# PHASE 2
# MARKET INTELLIGENCE ENGINE
# ============================================================

def get_product_evidence(
    product,
    evidence
):

    empty_result = {

        "local": pd.DataFrame(),

        "broader": pd.DataFrame(),

        "low": None,

        "high": None,

        "median": None,

        "spread": None,

        "count": 0,

        "confidence": "None",

        "trend": "Unknown",

        "status": "Awaiting evidence",

        "fresh": False

    }

    if evidence.empty:

        return empty_result


    product_key = normalize_text(
        product
    )


    matches = evidence[
        evidence["product"]
        .apply(normalize_text)
        == product_key
    ].copy()


    if matches.empty:

        return empty_result


    matches["quality_score"] = (
        matches.apply(
            evidence_quality,
            axis=1
        )
    )


    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    matches["parsed_date"] = pd.to_datetime(
        matches["date"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    local = matches[
        matches[
            "geographic_relevance"
        ]
        .apply(normalize_text)
        .isin(
            LOCAL_GEOGRAPHIES
        )
    ].copy()


    local = local[
        local["quality_score"] >= 5
    ].copy()


    # --------------------------------------------------------
    # BROADER
    # --------------------------------------------------------

    broader = matches[
        matches["quality_score"] >= 4
    ].copy()


    working = local.copy()

    status = "Local evidence available"


    if len(working) < 2:

        working = broader.copy()

        status = "Broader reference only"


    if len(working) < 2:

        empty_result[
            "local"
        ] = local

        empty_result[
            "broader"
        ] = broader

        empty_result[
            "status"
        ] = "Insufficient evidence"

        return empty_result


    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    low = working["price"].min()

    high = working["price"].max()

    median = working["price"].median()

    spread = high - low

    count = len(working)


    # --------------------------------------------------------
    # FRESHNESS
    # --------------------------------------------------------

    valid_dates = working[
        "parsed_date"
    ].dropna()


    fresh = False

    if not valid_dates.empty:

        latest_date = valid_dates.max()

        days_old = (
            pd.Timestamp.today()
            - latest_date
        ).days

        fresh = days_old <= 7


    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    if (
        count >= 5
        and fresh
        and status == "Local evidence available"
    ):

        confidence = "High"

    elif (
        count >= 3
        and status == "Local evidence available"
    ):

        confidence = "Medium"

    elif count >= 2:

        confidence = "Low"

    else:

        confidence = "None"


    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    trend = "Stable / Unknown"


    dated = working.dropna(
        subset=["parsed_date"]
    ).sort_values(
        "parsed_date"
    )


    if len(dated) >= 3:

        recent = dated.tail(
            max(1, len(dated) // 2)
        )["price"].mean()

        older = dated.head(
            max(1, len(dated) // 2)
        )["price"].mean()


        if recent > older * 1.02:

            trend = "Rising"

        elif recent < older * 0.98:

            trend = "Falling"

        else:

            trend = "Stable"


    return {

        "local": local,

        "broader": broader,

        "low": low,

        "high": high,

        "median": median,

        "spread": spread,

        "count": count,

        "confidence": confidence,

        "trend": trend,

        "status": status,

        "fresh": fresh

    }


# ============================================================
# PHASE 3
# MARKET AGENT WATCHLIST
# ============================================================

def build_watchlist(
    pricing_data,
    evidence
):

    watchlist = []

    for product in pricing_data[
        "Product"
    ].dropna().unique():

        intelligence = get_product_evidence(
            product,
            evidence
        )

        needs_refresh = (

            intelligence["count"] < 3
            or not intelligence["fresh"]
            or intelligence["confidence"]
            in ["Low", "None"]

        )

        if needs_refresh:

            watchlist.append({

                "Product": product,

                "Reason":
                    "Fresh local evidence needed"

            })


    return pd.DataFrame(
        watchlist
    )


# ============================================================
# PHASE 4
# MOVEMENT INTELLIGENCE
# ============================================================

def determine_movement(
    quantity,
    historical_quantities=None
):

    if (
        historical_quantities is None
        or len(historical_quantities) < 3
    ):

        if quantity >= 50:

            return "Fast"

        elif quantity >= 10:

            return "Medium"

        return "Slow"


    average = pd.Series(
        historical_quantities
    ).mean()


    if quantity >= average * 1.5:

        return "Fast"

    if quantity <= average * 0.5:

        return "Slow"

    return "Medium"


# ============================================================
# PHASE 4
# COMPETITIVE PRESSURE
# ============================================================

def competitive_pressure(
    intelligence
):

    if intelligence["count"] < 2:

        return "Unknown"


    spread = intelligence["spread"]

    median = intelligence["median"]


    if median <= 0:

        return "Unknown"


    spread_percent = (
        spread / median
    ) * 100


    if spread_percent <= 4:

        return "High"


    if spread_percent <= 8:

        return "Medium"


    return "Low"


# ============================================================
# PRICE POSITION
# ============================================================

def price_position(
    price,
    low,
    high
):

    if (
        low is None
        or high is None
        or high <= low
    ):

        return None


    return (
        (price - low)
        /
        (high - low)
    ) * 100


# ============================================================
# PHASE 5
# PRICING STRATEGY
# ============================================================

def pricing_strategy(
    buying_price,
    intelligence,
    movement
):

    low = intelligence["low"]

    high = intelligence["high"]

    median = intelligence["median"]


    # --------------------------------------------------------
    # NO MARKET EVIDENCE
    # --------------------------------------------------------

    if (
        low is None
        or high is None
    ):

        base_margin = 5

        balanced = (
            buying_price
            /
            (1 - base_margin / 100)
        )

        return {

            "value": round(
                balanced * 0.98,
                2
            ),

            "balanced": round(
                balanced,
                2
            ),

            "margin": round(
                balanced * 1.02,
                2
            ),

            "recommended":
                round(
                    balanced,
                    2
                ),

            "target_margin":
                base_margin,

            "reason":
                "No reliable market evidence. "
                "Recommendation is cost-based only."

        }


    # --------------------------------------------------------
    # MOVEMENT ADJUSTMENT
    # --------------------------------------------------------

    if movement == "Fast":

        target = 3.5

    elif movement == "Medium":

        target = 5.0

    else:

        target = 7.0


    # --------------------------------------------------------
    # MARKET-BASED OPTIONS
    # --------------------------------------------------------

    value_price = low

    balanced_price = median

    margin_price = high


    # --------------------------------------------------------
    # COST FLOOR
    # --------------------------------------------------------

    cost_floor = buying_price * (
        1 + target / 100
    )


    value_price = max(
        value_price,
        cost_floor
    )


    balanced_price = max(
        balanced_price,
        cost_floor
    )


    margin_price = max(
        margin_price,
        balanced_price
    )


    # --------------------------------------------------------
    # RECOMMENDATION
    # --------------------------------------------------------

    if movement == "Fast":

        recommended = balanced_price

        reason = (
            "Fast-moving product: "
            "the strategy prioritizes "
            "competitive turnover while "
            "protecting a reasonable margin."
        )

    elif movement == "Slow":

        recommended = margin_price

        reason = (
            "Slow-moving product: "
            "the strategy gives more weight "
            "to margin because capital may "
            "remain tied up longer."
        )

    else:

        recommended = balanced_price

        reason = (
            "Medium-moving product: "
            "the strategy balances "
            "market competitiveness and margin."
        )


    return {

        "value":
            round(value_price, 2),

        "balanced":
            round(balanced_price, 2),

        "margin":
            round(margin_price, 2),

        "recommended":
            round(recommended, 2),

        "target_margin":
            target,

        "reason":
            reason

    }


# ============================================================
# LOAD EVIDENCE
# ============================================================

market_evidence = load_evidence()


# ============================================================
# PHASE 1
# QUICKBOOKS
# ============================================================

st.subheader(
    "1. Purchase Data"
)


uploaded_file = st.file_uploader(
    "Upload today's QuickBooks Excel file",
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
            c for c in required_columns
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
            (data["Memo"] != "")
            &
            data["Cost Price"].notna()
        ].copy()


        pricing_data = pd.DataFrame({

            "Product":
                data["Memo"],

            "Item":
                data["Item"],

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
            f"{len(pricing_data)} products imported."
        )


    except Exception as error:

        st.error(
            f"Could not process file: {error}"
        )


# ============================================================
# EVERYTHING BELOW REQUIRES PURCHASE DATA
# ============================================================

if "pricing_data" in st.session_state:

    pricing_data = st.session_state[
        "pricing_data"
    ]


    # ========================================================
    # PHASE 2
    # MARKET INTELLIGENCE
    # ========================================================

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


    intelligence = get_product_evidence(
        selected_product,
        market_evidence
    )


    # ========================================================
    # PRODUCT HEADER
    # ========================================================

    st.markdown(
        f"## {selected_product}"
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "Buying Price",
            f"KES "
            f"{selected_row['Buying Price']:,.2f}"
        )


    with col2:

        st.metric(
            "Quantity",
            f"{selected_row['Quantity']:g}"
        )


    with col3:

        st.metric(
            "Movement",
            determine_movement(
                selected_row["Quantity"]
            )
        )


    # ========================================================
    # MARKET METRICS
    # ========================================================

    if intelligence["low"] is not None:

        col1, col2, col3, col4 = st.columns(4)


        with col1:

            st.metric(
                "Local Low",
                f"KES "
                f"{intelligence['low']:,.2f}"
            )


        with col2:

            st.metric(
                "Local High",
                f"KES "
                f"{intelligence['high']:,.2f}"
            )


        with col3:

            st.metric(
                "Median",
                f"KES "
                f"{intelligence['median']:,.2f}"
            )


        with col4:

            st.metric(
                "Observations",
                intelligence["count"]
            )


        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "Spread",
                f"KES "
                f"{intelligence['spread']:,.2f}"
            )


        with col2:

            st.metric(
                "Confidence",
                intelligence["confidence"]
            )


        with col3:

            st.metric(
                "Market Trend",
                intelligence["trend"]
            )


        pressure = competitive_pressure(
            intelligence
        )


        st.write(
            f"**Competitive pressure:** "
            f"{pressure}"
        )


    else:

        st.warning(
            "No reliable market evidence is available "
            "for this product yet."
        )


    # ========================================================
    # PHASE 3
    # MARKET AGENT WATCHLIST
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
            "Current products have sufficiently fresh evidence."
        )

    else:

        st.info(
            f"{len(watchlist)} product(s) need "
            "fresh market evidence."
        )

        st.dataframe(
            watchlist,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # TEMPORARY AGENT TEST INPUT
    # ========================================================

    with st.expander(
        "Developer: Add a market observation"
    ):

        st.caption(
            "This is a temporary testing interface. "
            "Later the market agent will populate this automatically."
        )


        observation_product = st.text_input(
            "Product",
            value=selected_product
        )


        col1, col2 = st.columns(2)


        with col1:

            observation_price = st.number_input(
                "Observed Price",
                min_value=0.0,
                step=1.0
            )


        with col2:

            observation_date = st.date_input(
                "Observation Date",
                value=date.today()
            )


        col1, col2 = st.columns(2)


        with col1:

            observation_location = st.selectbox(
                "Location",
                [
                    "Karatina",
                    "Nyeri Town",
                    "Other"
                ]
            )


        with col2:

            observation_source_type = st.selectbox(
                "Source Type",
                [
                    "WHOLESALER",
                    "SUPPLIER",
                    "OFFICIAL",
                    "COMMERCIAL",
                    "RETAIL"
                ]
            )


        observation_source = st.text_input(
            "Source / Competitor"
        )


        pack_size = st.text_input(
            "Pack Size"
        )


        unit = st.text_input(
            "Unit",
            value="carton"
        )


        strength = st.selectbox(
            "Evidence Strength",
            [
                "HIGH",
                "MEDIUM",
                "LOW"
            ]
        )


        if st.button(
            "Add Market Observation"
        ):

            if (
                observation_product.strip()
                and observation_price > 0
            ):

                if observation_location in [
                    "Karatina",
                    "Nyeri Town"
                ]:

                    geography = (
                        "KARATINA-NYERI CORRIDOR"
                    )

                else:

                    geography = "WIDER / OTHER"


                new_row = {

                    "product":
                        observation_product,

                    "pack_size":
                        pack_size,

                    "location":
                        observation_location,

                    "price":
                        observation_price,

                    "unit":
                        unit,

                    "date":
                        observation_date.isoformat(),

                    "source":
                        observation_source,

                    "source_type":
                        observation_source_type,

                    "evidence_strength":
                        strength,

                    "geographic_relevance":
                        geography

                }


                market_evidence = pd.concat(
                    [
                        market_evidence,
                        pd.DataFrame([new_row])
                    ],
                    ignore_index=True
                )


                save_evidence(
                    market_evidence
                )


                st.success(
                    "Market observation added."
                )

                st.rerun()


            else:

                st.error(
                    "Product and price are required."
                )


    # ========================================================
    # PHASE 4
    # MOVEMENT
    # ========================================================

    st.divider()

    st.subheader(
        "4. Product Movement"
    )


    movement = determine_movement(
        selected_row["Quantity"]
    )


    if movement == "Fast":

        movement_message = (
            "Fast-moving signal: prioritize "
            "competitive turnover and cash flow."
        )

    elif movement == "Medium":

        movement_message = (
            "Medium-moving signal: balance "
            "margin and competitiveness."
        )

    else:

        movement_message = (
            "Slow-moving signal: protect margin "
            "because capital may remain tied up."
        )


    st.info(
        f"**Movement: {movement}** — "
        f"{movement_message}"
    )


    # ========================================================
    # PHASE 5
    # PRICING STRATEGY
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


    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "VALUE PRICE",
            f"KES "
            f"{strategy['value']:,.2f}"
        )


    with col2:

        st.metric(
            "BALANCED PRICE",
            f"KES "
            f"{strategy['balanced']:,.2f}"
        )


    with col3:

        st.metric(
            "MARGIN PRICE",
            f"KES "
            f"{strategy['margin']:,.2f}"
        )


    st.success(
        f"### Recommended Price: "
        f"KES {strategy['recommended']:,.2f}"
    )


    st.write(
        f"**Target margin strategy:** "
        f"{strategy['target_margin']:.1f}%"
    )


    st.info(
        f"**Why:** {strategy['reason']}"
    )


    # ========================================================
    # CURRENT SELLING PRICE
    # ========================================================

    st.divider()

    st.subheader(
        "Owner's Current Price"
    )


    current_price = st.number_input(

        "Current Selling Price (KES)",

        min_value=0.0,

        step=1.0,

        format="%.2f",

        key=f"current_price_{selected_index}"

    )


    if current_price > 0:

        buying = float(
            selected_row[
                "Buying Price"
            ]
        )


        current_margin = calculate_margin(
            buying,
            current_price
        )


        current_profit = calculate_profit(
            buying,
            current_price
        )


        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "Current Profit",
                f"KES "
                f"{current_profit:,.2f}"
            )


        with col2:

            st.metric(
                "Current Margin",
                f"{current_margin:.2f}%"
            )


        with col3:

            difference = (
                current_price
                -
                strategy["recommended"]
            )


            st.metric(
                "vs Recommendation",
                f"KES {difference:,.2f}"
            )


        if st.button(
            "Save Owner Price",
            type="primary"
        ):

            pricing_data.at[
                selected_index,
                "Current Selling Price"
            ] = current_price


            pricing_data.at[
                selected_index,
                "Margin"
            ] = current_margin


            st.session_state[
                "pricing_data"
            ] = pricing_data


            st.success(
                f"Saved KES "
                f"{current_price:,.2f}."
            )


# ============================================================
# EVIDENCE DATABASE
# ============================================================

st.divider()

st.subheader(
    "Market Evidence Database"
)


if market_evidence.empty:

    st.info(
        "No market observations have been collected yet. "
        "The database is ready for the market intelligence agent."
    )

else:

    st.caption(
        f"{len(market_evidence)} market observation(s)."
    )


    display = market_evidence.copy()


    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PRINCIPLE
# ============================================================

st.divider()

st.caption(
    "The system researches and reasons. "
    "The wholesaler retains the final pricing decision."
)
