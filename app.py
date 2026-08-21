import streamlit as st
import pandas as pd
import math

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.write(
    "Upload your QuickBooks purchase file and review pricing decisions."
)


# =========================================
# SESSION STATE
# =========================================

if "saved_pricing_data" not in st.session_state:
    st.session_state.saved_pricing_data = None


# =========================================
# PRICING STRATEGIES
# =========================================

strategy_margins = {
    "Competitive": 0.07,
    "Standard": 0.10,
    "Higher Margin": 0.15,
    "Clearance": 0.00
}


# =========================================
# HELPER FUNCTION
# =========================================

def round_to_5(value):
    """Round a price to the nearest KES 5."""
    if pd.isna(value):
        return None

    return round(value / 5) * 5


# =========================================
# FILE UPLOAD
# =========================================

uploaded_file = st.file_uploader(
    "Upload QuickBooks Excel file",
    type=["xlsx", "xls"]
)


if uploaded_file is not None:

    try:

        # =========================================
        # READ QUICKBOOKS FILE
        # =========================================

        data = pd.read_excel(
            uploaded_file,
            sheet_name="Sheet1",
            header=0
        )


        # =========================================
        # CLEAN COLUMN NAMES
        # =========================================

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


        # =========================================
        # REMOVE EMPTY ROWS
        # =========================================

        data = data.dropna(
            how="all"
        ).copy()


        # =========================================
        # REQUIRED COLUMNS
        # =========================================

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

            # =========================================
            # CONVERT NUMERIC DATA
            # =========================================

            data["Cost Price"] = pd.to_numeric(
                data["Cost Price"],
                errors="coerce"
            )

            data["Qty"] = pd.to_numeric(
                data["Qty"],
                errors="coerce"
            )


            # =========================================
            # REMOVE INVALID PRODUCTS
            # =========================================

            data = data[
                data["Memo"].notna()
                & data["Cost Price"].notna()
            ].copy()


            data = data[
                data["Memo"]
                .astype(str)
                .str.strip()
                != ""
            ].copy()


            # =========================================
            # CREATE PRICING WORKSPACE
            # =========================================

            pricing_data = pd.DataFrame()


            pricing_data["Product"] = (
                data["Memo"]
                .astype(str)
                .str.strip()
            )


            pricing_data["Buying Price"] = (
                data["Cost Price"]
            )


            # Market information

            pricing_data["Market Low"] = None

            pricing_data["Market High"] = None


            # Business strategy

            pricing_data["Pricing Strategy"] = (
                "Standard"
            )


            pricing_data["Target Margin %"] = (
                10.0
            )


            # Pricing calculations

            pricing_data["Minimum Viable Price"] = None

            pricing_data["Recommended Price"] = None


            # Current business price

            pricing_data["Current Selling Price"] = None


            # Approved business decision

            pricing_data["Approved Selling Price"] = None


            # Profitability

            pricing_data["Current Margin"] = None

            pricing_data["Current Margin %"] = None


            # Future intelligence inputs

            pricing_data["Sales Velocity"] = (
                "Unknown"
            )

            pricing_data["AI Competitiveness"] = (
                "Pending"
            )

            pricing_data["AI Confidence"] = (
                "Pending"
            )


            # Decision output

            pricing_data["Pricing Status"] = (
                "Pending market data"
            )

            pricing_data["Pricing Explanation"] = (
                "Enter market prices to generate a recommendation."
            )


            # =========================================
            # SUCCESS MESSAGE
            # =========================================

            st.success(
                f"{len(pricing_data)} products imported."
            )


            # =========================================
            # PRICING ENGINE
            # =========================================

            st.subheader(
                "Pricing Decision Engine"
            )

            st.write(
                "Enter observed market prices and choose the "
                "business pricing strategy."
            )


            # =========================================
            # EDITABLE TABLE
            # =========================================

            edited_data = st.data_editor(

                pricing_data,

                use_container_width=True,

                hide_index=True,

                disabled=[

                    "Product",

                    "Buying Price",

                    "Target Margin %",

                    "Minimum Viable Price",

                    "Recommended Price",

                    "Current Margin",

                    "Current Margin %",

                    "AI Competitiveness",

                    "AI Confidence",

                    "Pricing Status",

                    "Pricing Explanation"
                ],

                column_config={

                    "Buying Price":
                        st.column_config.NumberColumn(
                            "Buying Price",
                            format="KES %.2f"
                        ),

                    "Market Low":
                        st.column_config.NumberColumn(
                            "Market Low",
                            min_value=0,
                            step=1,
                            format="KES %.2f"
                        ),

                    "Market High":
                        st.column_config.NumberColumn(
                            "Market High",
                            min_value=0,
                            step=1,
                            format="KES %.2f"
                        ),

                    "Pricing Strategy":
                        st.column_config.SelectboxColumn(
                            "Pricing Strategy",
                            options=[
                                "Competitive",
                                "Standard",
                                "Higher Margin",
                                "Clearance"
                            ],
                            required=True
                        ),

                    "Target Margin %":
                        st.column_config.NumberColumn(
                            "Target Margin %",
                            format="%.2f%%"
                        ),

                    "Minimum Viable Price":
                        st.column_config.NumberColumn(
                            "Minimum Viable Price",
                            format="KES %.2f"
                        ),

                    "Recommended Price":
                        st.column_config.NumberColumn(
                            "Recommended Price",
                            format="KES %.2f"
                        ),

                    "Current Selling Price":
                        st.column_config.NumberColumn(
                            "Current Selling Price",
                            min_value=0,
                            step=1,
                            format="KES %.2f"
                        ),

                    "Approved Selling Price":
                        st.column_config.NumberColumn(
                            "Approved Selling Price",
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
                        ),

                    "Sales Velocity":
                        st.column_config.SelectboxColumn(
                            "Sales Velocity",
                            options=[
                                "Unknown",
                                "Fast",
                                "Medium",
                                "Slow"
                            ],
                            required=True
                        )
                }
            )


            # =========================================
            # TARGET MARGIN
            # =========================================

            edited_data["Target Margin %"] = (

                edited_data["Pricing Strategy"]
                .map(strategy_margins)
                * 100

            )


            # =========================================
            # TARGET MARGIN DECIMAL
            # =========================================

            target_margin_decimal = (
                edited_data["Target Margin %"]
                / 100
            )


            # =========================================
            # MINIMUM VIABLE PRICE
            # =========================================

            edited_data["Minimum Viable Price"] = (

                edited_data["Buying Price"]
                /
                (
                    1
                    -
                    target_margin_decimal
                )

            )


            # =========================================
            # RECOMMENDATION ENGINE
            # =========================================

            for index, row in edited_data.iterrows():

                buying_price = row["Buying Price"]

                market_low = pd.to_numeric(
                    row["Market Low"],
                    errors="coerce"
                )

                market_high = pd.to_numeric(
                    row["Market High"],
                    errors="coerce"
                )

                minimum_price = row[
                    "Minimum Viable Price"
                ]


                # -------------------------------------
                # NO MARKET DATA
                # -------------------------------------

                if (
                    pd.isna(market_low)
                    or pd.isna(market_high)
                ):

                    edited_data.at[
                        index,
                        "Recommended Price"
                    ] = None

                    edited_data.at[
                        index,
                        "Pricing Status"
                    ] = "Pending market data"

                    edited_data.at[
                        index,
                        "Pricing Explanation"
                    ] = (
                        "Enter both Market Low and "
                        "Market High."
                    )

                    continue


                # -------------------------------------
                # INVALID MARKET RANGE
                # -------------------------------------

                if market_low > market_high:

                    edited_data.at[
                        index,
                        "Recommended Price"
                    ] = None

                    edited_data.at[
                        index,
                        "Pricing Status"
                    ] = "Invalid market range"

                    edited_data.at[
                        index,
                        "Pricing Explanation"
                    ] = (
                        "Market Low cannot be greater "
                        "than Market High."
                    )

                    continue


                # -------------------------------------
                # TARGET ACHIEVABLE
                # -------------------------------------

                if minimum_price <= market_high:

                    if minimum_price < market_low:

                        recommended_price = market_low

                    else:

                        recommended_price = minimum_price


                    recommended_price = round_to_5(
                        recommended_price
                    )


                    edited_data.at[
                        index,
                        "Recommended Price"
                    ] = recommended_price


                    edited_data.at[
                        index,
                        "Pricing Status"
                    ] = "Target achievable"


                    edited_data.at[
                        index,
                        "Pricing Explanation"
                    ] = (

                        "The target margin can be achieved "
                        "within the observed market range. "
                        "The recommendation is constrained "
                        "by the market and rounded to KES 5."

                    )


                # -------------------------------------
                # TARGET NOT ACHIEVABLE
                # -------------------------------------

                else:

                    edited_data.at[
                        index,
                        "Recommended Price"
                    ] = None


                    edited_data.at[
                        index,
                        "Pricing Status"
                    ] = "Target exceeds market"


                    edited_data.at[
                        index,
                        "Pricing Explanation"
                    ] = (

                        "The minimum price required to achieve "
                        "the selected target margin is above "
                        "the observed market ceiling. "
                        "Review the margin, buying cost, "
                        "or competitive position."

                    )


            # =========================================
            # CURRENT SELLING PRICE
            # =========================================

            edited_data[
                "Current Selling Price"
            ] = pd.to_numeric(

                edited_data[
                    "Current Selling Price"
                ],

                errors="coerce"
            )


            # =========================================
            # CURRENT MARGIN
            # =========================================

            edited_data[
                "Current Margin"
            ] = (

                edited_data[
                    "Current Selling Price"
                ]

                -

                edited_data[
                    "Buying Price"
                ]

            )


            # =========================================
            # CURRENT MARGIN %
            # =========================================

            edited_data[
                "Current Margin %"
            ] = (

                edited_data[
                    "Current Margin"
                ]

                /

                edited_data[
                    "Current Selling Price"
                ]

            ) * 100


            # =========================================
            # HANDLE EMPTY SELLING PRICE
            # =========================================

            edited_data.loc[

                edited_data[
                    "Current Selling Price"
                ].isna()

                |

                (
                    edited_data[
                        "Current Selling Price"
                    ]
                    == 0
                ),

                "Current Margin %"

            ] = None


            # =========================================
            # SAVE CHANGES
            # =========================================

            if st.button(
                "Save Pricing Decisions",
                type="primary"
            ):

                st.session_state.saved_pricing_data = (
                    edited_data.copy()
                )

                st.success(
                    "Pricing decisions saved for this session."
                )


            # =========================================
            # SAVED PRICING
            # =========================================

            if (
                st.session_state.saved_pricing_data
                is not None
            ):

                st.subheader(
                    "Pricing Decisions"
                )

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

                        "Market Low":
                            st.column_config.NumberColumn(
                                "Market Low",
                                format="KES %.2f"
                            ),

                        "Market High":
                            st.column_config.NumberColumn(
                                "Market High",
                                format="KES %.2f"
                            ),

                        "Target Margin %":
                            st.column_config.NumberColumn(
                                "Target Margin %",
                                format="%.2f%%"
                            ),

                        "Minimum Viable Price":
                            st.column_config.NumberColumn(
                                "Minimum Viable Price",
                                format="KES %.2f"
                            ),

                        "Recommended Price":
                            st.column_config.NumberColumn(
                                "Recommended Price",
                                format="KES %.2f"
                            ),

                        "Current Selling Price":
                            st.column_config.NumberColumn(
                                "Current Selling Price",
                                format="KES %.2f"
                            ),

                        "Approved Selling Price":
                            st.column_config.NumberColumn(
                                "Approved Selling Price",
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
