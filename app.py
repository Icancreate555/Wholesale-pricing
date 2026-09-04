import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Wholesale Pricing Workspace",
    page_icon="📦",
    layout="wide"
)

st.title("Wholesale Pricing Workspace")
st.caption("Upload a QuickBooks purchase invoice and prepare it for pricing review.")

# ============================================================
# SESSION STATE
# ============================================================

if "pricing_data" not in st.session_state:
    st.session_state.pricing_data = None

if "invoice_name" not in st.session_state:
    st.session_state.invoice_name = ""

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_number(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("KES", "", regex=False)
        .str.replace("KSh", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


def find_header_row(raw_df):
    """
    Find the QuickBooks header row automatically.
    """
    expected = {
        "Type",
        "Date",
        "Num",
        "Memo",
        "Item",
        "Qty",
        "U/M",
        "Cost Price"
    }

    for i in range(min(len(raw_df), 30)):
        row_values = {
            clean_text(x)
            for x in raw_df.iloc[i].tolist()
        }

        matches = len(expected.intersection(row_values))

        if matches >= 5:
            return i

    return None


def calculate_pricing(df):
    """
    Recreates the core formulas from PRICING.xlsx.

    Excel logic:

    Amount:
        =ROUND(IF(ISNUMBER(J), H*J, H), 5)

    AMT (VAT):
        =K*1.16

    BP/C:
        =L/H

    MIN S.P:
        =(100%+MIN M%)*BP/C

    Recommended Margin:
        =(RECC S.P-BP/C)/BP/C

    Current Margin:
        =(STS. S.P-BP/C)/BP/C

    New Margin:
        =(NEW S.P-BP/C)/BP/C

    WS S.P:
        =BASE PRICE / P/C
    """

    # --------------------------------------------------------
    # Amount
    # --------------------------------------------------------

    df["Amount"] = np.where(
        pd.notna(df["Cost Price"]),
        np.round(
            np.where(
                pd.notna(df["Qty"]),
                df["Qty"] * df["Cost Price"],
                df["Cost Price"]
            ),
            5
        ),
        np.nan
    )

    # --------------------------------------------------------
    # VAT-inclusive amount
    # --------------------------------------------------------

    df["AMT (VAT)"] = df["Amount"] * 1.16

    # --------------------------------------------------------
    # BP/C
    # Cost per selling unit/carton/etc.
    # --------------------------------------------------------

    df["BP/C"] = np.where(
        df["Qty"] > 0,
        df["AMT (VAT)"] / df["Qty"],
        np.nan
    )

    # --------------------------------------------------------
    # Minimum margin
    # --------------------------------------------------------

    def minimum_margin(row):
        product = str(row["Product"]).upper()

        # These are the margin bands from the PRICING workbook.
        # We use the lower bound for the minimum selling price.
        if any(x in product for x in [
            "ALPA",
            "RAHA NGANO",
            "RINA",
            "SUGAR",
            "RICE"
        ]):
            return 0.05

        if any(x in product for x in [
            "MENENGAI",
            "KEN SALT",
            "BISCUIT",
            "BISCUITS",
            "INDOMIE",
            "SUNNY GIRL",
            "SOFT CARE",
            "DOWNY",
            "TROPICAL"
        ]):
            return 0.07

        return 0.05

    df["MIN M%"] = df.apply(minimum_margin, axis=1)

    # --------------------------------------------------------
    # Minimum selling price
    #
    # = (1 + MIN M%) * BP/C
    # --------------------------------------------------------

    df["MIN S.P"] = (
        (1 + df["MIN M%"]) * df["BP/C"]
    )

    # --------------------------------------------------------
    # Fields requiring market intelligence / owner input
    # --------------------------------------------------------

    df["MARKET RANGE"] = ""

    df["RECC S.P"] = np.nan

    df["RECC MARGIN %"] = np.nan

    # --------------------------------------------------------
    # Current selling price
    # Owner enters this later
    # --------------------------------------------------------

    df["STS. S.P"] = np.nan

    df["CURRENT MARGIN %"] = np.nan

    # --------------------------------------------------------
    # New selling price
    # Owner may enter this later
    # --------------------------------------------------------

    df["NEW S.P"] = np.nan

    df["NEW MARGIN %"] = np.nan

    # --------------------------------------------------------
    # Base price
    #
    # PRICING.xlsx:
    # =V/E
    #
    # V = NEW S.P
    # E = P/C
    # --------------------------------------------------------

    df["BASE PRICE"] = np.nan

    # --------------------------------------------------------
    # Wholesale selling price
    #
    # PRICING.xlsx:
    # =V/E
    #
    # Only calculate where BASE PRICE and P/C exist.
    # --------------------------------------------------------

    df["WS S.P"] = np.nan

    # --------------------------------------------------------
    # Retail selling price
    # Kept for later.
    # --------------------------------------------------------

    df["RETAIL S.P"] = np.nan

    return df


def build_pricing_table(uploaded_file):
    """
    Reads a QuickBooks Excel export and converts it
    into the PRICING.xlsx structure.
    """

    raw = pd.read_excel(
        uploaded_file,
        sheet_name="Sheet1",
        header=None
    )

    header_row = find_header_row(raw)

    if header_row is None:
        raise ValueError(
            "Could not find the QuickBooks header row."
        )

    df = pd.read_excel(
        uploaded_file,
        sheet_name="Sheet1",
        header=header_row
    )

    # --------------------------------------------------------
    # Clean column names
    # --------------------------------------------------------

    df.columns = [
        clean_text(col)
        for col in df.columns
    ]

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

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
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}"
        )

    # --------------------------------------------------------
    # Remove empty rows
    # --------------------------------------------------------

    df = df.dropna(
        how="all"
    ).copy()

    # --------------------------------------------------------
    # Remove QuickBooks total rows
    # --------------------------------------------------------

    text_columns = [
        "Memo",
        "Item",
        "Num"
    ]

    for col in text_columns:
        df[col] = df[col].apply(clean_text)

    combined_text = (
        df["Memo"].str.upper()
        + " "
        + df["Item"].str.upper()
    )

    total_mask = combined_text.str.contains(
        "TOTAL|BALANCE|SUBTOTAL",
        na=False
    )

    df = df.loc[~total_mask].copy()

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    df["Qty"] = clean_number(df["Qty"])
    df["Cost Price"] = clean_number(df["Cost Price"])

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Product name
    #
    # Prefer Memo because this is the clean product name
    # in the pricing workbook.
    # --------------------------------------------------------

    df["Product"] = df["Memo"]

    empty_product = (
        df["Product"].str.strip() == ""
    )

    df.loc[
        empty_product,
        "Product"
    ] = df.loc[
        empty_product,
        "Item"
    ]

    # --------------------------------------------------------
    # P/C
    #
    # QuickBooks/PRICING workbook uses the pack quantity
    # from the invoice.
    # --------------------------------------------------------

    if "P/C" in df.columns:
        df["P/C"] = clean_number(df["P/C"])
    else:
        df["P/C"] = np.nan

    # --------------------------------------------------------
    # Name / Supplier
    # --------------------------------------------------------

    if "Name" in df.columns:
        df["Name"] = df["Name"].apply(clean_text)
    else:
        df["Name"] = ""

    # --------------------------------------------------------
    # Type
    # --------------------------------------------------------

    if "Type" in df.columns:
        df["Type"] = df["Type"].apply(clean_text)
    else:
        df["Type"] = "Bill"

    # --------------------------------------------------------
    # Build pricing dataframe
    # --------------------------------------------------------

    pricing = pd.DataFrame()

    pricing["Type"] = df["Type"]
    pricing["Date"] = df["Date"]
    pricing["Num"] = df["Num"]
    pricing["Memo"] = df["Memo"]
    pricing["P/C"] = df["P/C"]
    pricing["Name"] = df["Name"]
    pricing["Product"] = df["Product"]
    pricing["Qty"] = df["Qty"]
    pricing["U/M"] = df["U/M"]
    pricing["Cost Price"] = df["Cost Price"]

    # --------------------------------------------------------
    # Apply pricing formulas
    # --------------------------------------------------------

    pricing = calculate_pricing(pricing)

    return pricing


def format_money(value):
    if pd.isna(value):
        return ""

    return f"KES {value:,.2f}"


def export_excel(df):
    """
    Export the prepared pricing table to Excel.
    """

    output = BytesIO()

    export_df = df.copy()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        export_df.to_excel(
            writer,
            sheet_name="Pricing",
            index=False
        )

        workbook = writer.book
        worksheet = writer.sheets["Pricing"]

        # Freeze top row
        worksheet.freeze_panes = "A2"

        # Auto-size columns
        for column_cells in worksheet.columns:

            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:

                try:
                    cell_length = len(
                        str(cell.value)
                    )
                    max_length = max(
                        max_length,
                        cell_length
                    )
                except Exception:
                    pass

            worksheet.column_dimensions[
                column_letter
            ].width = min(
                max_length + 2,
                35
            )

    output.seek(0)

    return output


# ============================================================
# UPLOAD
# ============================================================

st.subheader("1. Upload Purchase Invoice")

uploaded_file = st.file_uploader(
    "Upload your QuickBooks Excel invoice",
    type=["xlsx", "xls"]
)

if uploaded_file:

    try:

        pricing_df = build_pricing_table(
            uploaded_file
        )

        st.session_state.pricing_data = pricing_df
        st.session_state.invoice_name = uploaded_file.name

        st.success(
            f"Invoice loaded successfully: {uploaded_file.name}"
        )

    except Exception as e:

        st.error(
            f"Could not process the invoice: {e}"
        )


# ============================================================
# DISPLAY
# ============================================================

if st.session_state.pricing_data is not None:

    df = st.session_state.pricing_data.copy()

    st.divider()

    # --------------------------------------------------------
    # Invoice summary
    # --------------------------------------------------------

    st.subheader("2. Purchase Review")

    invoice_number = (
        df["Num"]
        .dropna()
        .astype(str)
        .iloc[0]
        if not df["Num"].dropna().empty
        else "—"
    )

    invoice_date = (
        df["Date"]
        .dropna()
        .iloc[0]
        if not df["Date"].dropna().empty
        else None
    )

    supplier = (
        df["Name"]
        .dropna()
        .astype(str)
        .iloc[0]
        if not df["Name"].dropna().empty
        else "—"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Invoice",
            invoice_number
        )

    with col2:
        if invoice_date is not None:
            st.metric(
                "Invoice Date",
                invoice_date.strftime("%d/%m/%Y")
            )
        else:
            st.metric(
                "Invoice Date",
                "—"
            )

    with col3:
        st.metric(
            "Products",
            len(df)
        )

    st.write(
        f"**Supplier:** {supplier}"
    )

    # --------------------------------------------------------
    # Pricing table
    # --------------------------------------------------------

    st.divider()

    st.subheader("3. Pricing Worksheet")

    st.caption(
        "Calculated fields follow the logic in your PRICING.xlsx workbook. "
        "Market Range and Recommended Price are left blank until verified evidence is available."
    )

    # --------------------------------------------------------
    # Show the core table first
    # --------------------------------------------------------

    display_columns = [
        "Product",
        "Qty",
        "U/M",
        "Cost Price",
        "Amount",
        "AMT (VAT)",
        "BP/C",
        "MIN M%",
        "MIN S.P",
        "MARKET RANGE",
        "RECC S.P",
        "RECC MARGIN %",
        "STS. S.P",
        "CURRENT MARGIN %",
        "NEW S.P",
        "NEW MARGIN %",
        "BASE PRICE",
        "WS S.P",
        "RETAIL S.P"
    ]

    display_df = df[display_columns].copy()

    # --------------------------------------------------------
    # Owner editable selling prices
    # --------------------------------------------------------

    st.markdown(
        "**Owner-controlled prices**"
    )

    edited = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={

            "Product": st.column_config.TextColumn(
                "Product",
                disabled=True
            ),

            "Qty": st.column_config.NumberColumn(
                "Qty",
                disabled=True
            ),

            "U/M": st.column_config.TextColumn(
                "U/M",
                disabled=True
            ),

            "Cost Price": st.column_config.NumberColumn(
                "Cost Price",
                format="KES %.2f",
                disabled=True
            ),

            "Amount": st.column_config.NumberColumn(
                "Amount",
                format="KES %.2f",
                disabled=True
            ),

            "AMT (VAT)": st.column_config.NumberColumn(
                "AMT (VAT)",
                format="KES %.2f",
                disabled=True
            ),

            "BP/C": st.column_config.NumberColumn(
                "BP/C",
                format="KES %.2f",
                disabled=True
            ),

            "MIN M%": st.column_config.NumberColumn(
                "MIN M%",
                format="%.1f%%",
                disabled=True
            ),

            "MIN S.P": st.column_config.NumberColumn(
                "MIN S.P",
                format="KES %.2f",
                disabled=True
            ),

            "MARKET RANGE": st.column_config.TextColumn(
                "MARKET RANGE",
                disabled=True
            ),

            "RECC S.P": st.column_config.NumberColumn(
                "RECC S.P",
                format="KES %.2f",
                disabled=True
            ),

            "RECC MARGIN %": st.column_config.NumberColumn(
                "RECC MARGIN %",
                format="%.2f%%",
                disabled=True
            ),

            "STS. S.P": st.column_config.NumberColumn(
                "STS. S.P",
                format="KES %.2f"
            ),

            "CURRENT MARGIN %": st.column_config.NumberColumn(
                "CURRENT MARGIN %",
                format="%.2f%%",
                disabled=True
            ),

            "NEW S.P": st.column_config.NumberColumn(
                "NEW S.P",
                format="KES %.2f"
            ),

            "NEW MARGIN %": st.column_config.NumberColumn(
                "NEW MARGIN %",
                format="%.2f%%",
                disabled=True
            ),

            "BASE PRICE": st.column_config.NumberColumn(
                "BASE PRICE",
                format="KES %.2f",
                disabled=True
            ),

            "WS S.P": st.column_config.NumberColumn(
                "WS S.P",
                format="KES %.2f",
                disabled=True
            ),

            "RETAIL S.P": st.column_config.NumberColumn(
                "RETAIL S.P",
                format="KES %.2f"
            ),
        }
    )

    # ========================================================
    # RECALCULATE AFTER OWNER INPUT
    # ========================================================

    for index in edited.index:

        # ----------------------------------------------------
        # Current selling price margin
        # ----------------------------------------------------

        current_sp = edited.loc[
            index,
            "STS. S.P"
        ]

        bp = edited.loc[
            index,
            "BP/C"
        ]

        if (
            pd.notna(current_sp)
            and current_sp > 0
            and pd.notna(bp)
            and bp > 0
        ):

            edited.loc[
                index,
                "CURRENT MARGIN %"
            ] = (
                (current_sp - bp)
                / bp
            )

        else:

            edited.loc[
                index,
                "CURRENT MARGIN %"
            ] = np.nan

        # ----------------------------------------------------
        # New selling price margin
        # ----------------------------------------------------

        new_sp = edited.loc[
            index,
            "NEW S.P"
        ]

        if (
            pd.notna(new_sp)
            and new_sp > 0
            and pd.notna(bp)
            and bp > 0
        ):

            edited.loc[
                index,
                "NEW MARGIN %"
            ] = (
                (new_sp - bp)
                / bp
            )

            # BASE PRICE
            #
            # PRICING.xlsx:
            # =V/E
            #
            # NEW S.P / P/C
            # ------------------------------------------------

            pc = edited.loc[
                index,
                "P/C"
            ]

            if (
                pd.notna(pc)
                and pc > 0
            ):

                edited.loc[
                    index,
                    "BASE PRICE"
                ] = new_sp / pc

        else:

            edited.loc[
                index,
                "NEW MARGIN %"
            ] = np.nan

            edited.loc[
                index,
                "BASE PRICE"
            ] = np.nan

    # ========================================================
    # SAVE CHANGES
    # ========================================================

    st.session_state.pricing_data[
        display_columns
    ] = edited

    # ========================================================
    # DOWNLOAD
    # ========================================================

    st.divider()

    st.subheader("4. Export")

    excel_file = export_excel(
        st.session_state.pricing_data
    )

    st.download_button(
        label="📥 Download Pricing Worksheet",
        data=excel_file,
        file_name="Wholesale_Pricing_Worksheet.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    # ========================================================
    # FOOTER
    # ========================================================

    st.divider()

    st.caption(
        "The system prepares the pricing information and performs calculations. "
        "The wholesaler remains responsible for the final selling price."
    )
