import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Wholesale Pricing Workspace", layout="wide")

st.title("Wholesale Pricing Workspace")
st.caption("Upload a QuickBooks purchase export, review the invoice, and prepare the pricing worksheet.")

# ============================================================
# CONSTANT PRICING FORMULAS
# These formulas are taken from dabu / PRICING.xlsx.
# Do not change these formulas when building the pricing logic.
# ============================================================

VAT_RATE = 1.16

def formula_amount(qty, cost_price):
    """Dabu: =ROUND(IF(ISNUMBER(Jrow), Hrow*Jrow, Hrow),5)"""
    if pd.isna(cost_price):
        return qty if not pd.isna(qty) else np.nan
    if pd.isna(qty):
        return cost_price
    return round(qty * cost_price, 5)

def formula_vat(amount):
    """Dabu: =Krow*1.16"""
    return amount * VAT_RATE if not pd.isna(amount) else np.nan

def formula_bpc(vat_amount, qty):
    """Dabu: =Lrow/Hrow"""
    if pd.isna(vat_amount) or pd.isna(qty) or qty == 0:
        return np.nan
    return vat_amount / qty

def formula_min_sp(bp_c, min_margin):
    """Pricing.xlsx: =(100%+Orow)*Mrow"""
    if pd.isna(bp_c) or pd.isna(min_margin):
        return np.nan
    return (1 + min_margin) * bp_c

def formula_recc_margin(recc_sp, bp_c):
    """Pricing.xlsx column S: =(Rrow-Mrow)/Mrow"""
    if pd.isna(recc_sp) or pd.isna(bp_c) or bp_c == 0:
        return np.nan
    return (recc_sp - bp_c) / bp_c

def formula_current_margin(current_sp, bp_c):
    """Pricing.xlsx column U: =(Trow-Mrow)/Mrow"""
    if pd.isna(current_sp) or pd.isna(bp_c) or bp_c == 0:
        return np.nan
    return (current_sp - bp_c) / bp_c

def formula_base_price(new_sp, pc):
    """Pricing.xlsx: =Vrow/Erow"""
    if pd.isna(new_sp) or pd.isna(pc) or pc == 0:
        return np.nan
    return new_sp / pc


# ============================================================
# COLUMN NORMALISATION
# QuickBooks exports can change. The formulas do not.
# ============================================================

ALIASES = {
    "Type": ["type"],
    "Date": ["date", "transaction date", "bill date"],
    "Num": ["num", "number", "invoice", "invoice no", "invoice number"],
    "Memo": ["memo", "description", "product", "product name"],
    "P/C": ["p/c", "pc", "pack", "pack count", "pieces per carton", "pieces"],
    "Name": ["name", "vendor", "supplier", "vendor name", "supplier name"],
    "Item": ["item", "item name", "product/item"],
    "Qty": ["qty", "quantity", "units", "unit quantity"],
    "U/M": ["u/m", "um", "unit", "unit of measure", "uom"],
    "Cost Price": ["cost price", "cost", "buying price", "purchase price", "unit cost"],
    "Amount": ["amount", "total amount", "line amount"],
    "Balance": ["balance", "running balance"],
}

def clean_header(value):
    text = str(value).replace("\xa0", " ").strip().lower()
    text = " ".join(text.split())
    return text

def find_header_row(raw):
    best_row = None
    best_score = 0

    alias_lookup = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            alias_lookup[clean_header(alias)] = canonical

    for row_idx in range(min(30, len(raw))):
        values = [clean_header(v) for v in raw.iloc[row_idx].tolist()]
        score = len({alias_lookup[v] for v in values if v in alias_lookup})

        if score > best_score:
            best_score = score
            best_row = row_idx

    # A QuickBooks pricing export needs only these core fields.
    if best_row is None or best_score < 3:
        raise ValueError(
            "Could not identify the QuickBooks header row. "
            "The file must contain at least Item/Product, Qty/Quantity, "
            "and Cost Price/Cost."
        )

    return best_row

def standardise_quickbooks(raw):
    header_row = find_header_row(raw)

    data = raw.iloc[header_row + 1:].copy()
    raw_headers = raw.iloc[header_row].tolist()

    data.columns = [clean_header(x) for x in raw_headers]

    alias_lookup = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            alias_lookup[clean_header(alias)] = canonical

    rename_map = {}
    for col in data.columns:
        if col in alias_lookup:
            rename_map[col] = alias_lookup[col]

    data = data.rename(columns=rename_map)

    # If duplicate canonical columns occur, keep the first non-empty one.
    if data.columns.duplicated().any():
        result = pd.DataFrame(index=data.index)
        for col in dict.fromkeys(data.columns):
            matching = data.loc[:, data.columns == col]
            if matching.shape[1] == 1:
                result[col] = matching.iloc[:, 0]
            else:
                result[col] = matching.bfill(axis=1).iloc[:, 0]
        data = result

    # Required for pricing calculations.
    required = ["Item", "Qty", "Cost Price"]
    missing = [c for c in required if c not in data.columns]

    if missing:
        raise ValueError(
            "Missing required QuickBooks fields: "
            + ", ".join(missing)
        )

    optional_columns = [
        "Type", "Date", "Num", "Memo", "P/C", "Name",
        "U/M", "Amount", "Balance"
    ]

    for col in optional_columns:
        if col not in data.columns:
            data[col] = np.nan

    # Product name: prefer Memo where it is useful; otherwise Item.
    memo = data["Memo"].astype("string").str.strip()
    item = data["Item"].astype("string").str.strip()

    data["Memo"] = memo
    data["Item"] = item

    data["Product"] = memo.where(
        memo.notna() & (memo != ""),
        item
    )

    # Convert numeric columns.
    for col in ["Qty", "P/C", "Cost Price", "Amount", "Balance"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    # Remove blank rows.
    data = data[
        data["Product"].notna()
        & (data["Product"].astype(str).str.strip() != "")
    ].copy()

    # Remove common QuickBooks total/subtotal rows.
    total_pattern = r"^(total|subtotal|grand total|balance)$"
    data = data[
        ~data["Product"].astype(str).str.strip().str.lower().str.match(
            total_pattern, na=False
        )
    ].copy()

    data.reset_index(drop=True, inplace=True)

    # Recalculate Amount from the Dabu formula rather than trusting
    # whatever value the uploaded export happens to contain.
    data["Amount"] = [
        formula_amount(q, c)
        for q, c in zip(data["Qty"], data["Cost Price"])
    ]

    return data


# ============================================================
# BUILD THE PRICING WORKSHEET
# ============================================================

def build_pricing_table(data):
    pricing = pd.DataFrame(index=data.index)

    source_columns = [
        "Type", "Date", "Num", "Memo", "P/C", "Name",
        "Item", "Qty", "U/M", "Cost Price"
    ]

    for col in source_columns:
        pricing[col] = data[col]

    # Constant formula columns from Dabu / PRICING.xlsx.
    pricing["Amount"] = [
        formula_amount(q, c)
        for q, c in zip(data["Qty"], data["Cost Price"])
    ]

    pricing["AMT (VAT)"] = pricing["Amount"].apply(formula_vat)

    pricing["BP/C"] = [
        formula_bpc(vat, qty)
        for vat, qty in zip(pricing["AMT (VAT)"], pricing["Qty"])
    ]

    # These values are deliberately editable because they are not
    # constant formulas in Dabu.
    pricing["MARGIN %"] = ""
    pricing["MIN M%"] = np.nan
    pricing["MIN S.P"] = [
        formula_min_sp(bp, margin)
        for bp, margin in zip(pricing["BP/C"], pricing["MIN M%"])
    ]

    pricing["MARKET RANGE"] = ""
    pricing["RECC S.P"] = np.nan
    pricing["RECC MARGIN %"] = [
        formula_recc_margin(sp, bp)
        for sp, bp in zip(pricing["RECC S.P"], pricing["BP/C"])
    ]

    pricing["STS. S.P"] = np.nan
    pricing["CURRENT MARGIN %"] = [
        formula_current_margin(sp, bp)
        for sp, bp in zip(pricing["STS. S.P"], pricing["BP/C"])
    ]

    pricing["NEW S.P"] = np.nan
    pricing["BASE PRICE"] = [
        formula_base_price(sp, pc)
        for sp, pc in zip(pricing["NEW S.P"], pricing["P/C"])
    ]

    pricing["WS S.P"] = np.nan
    pricing["RETAIL S.P"] = np.nan

    pricing["Product"] = data["Product"]

    return pricing


# ============================================================
# EXPORT WITH THE ACTUAL EXCEL FORMULAS
# ============================================================

EXPORT_COLUMNS = [
    "Type", "Date", "Num", "Memo", "P/C", "Name", "Item", "Qty",
    "U/M", "Cost Price", "Amount", "AMT (VAT)", "BP/C", "MARGIN %",
    "MIN M%", "MIN S.P", "MARKET RANGE", "RECC S.P",
    "RECC MARGIN %", "STS. S.P", "CURRENT MARGIN %",
    "NEW S.P", "BASE PRICE", "WS S.P", "RETAIL S.P"
]

def export_excel(pricing):
    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
        datetime_format="yyyy-mm-dd"
    ) as writer:
        export_df = pricing[EXPORT_COLUMNS].copy()
        export_df.to_excel(writer, sheet_name="Sheet1", index=False)

        ws = writer.book["Sheet1"]

        # Put the Dabu / PRICING.xlsx formulas into the spreadsheet.
        for excel_row in range(2, len(export_df) + 2):
            ws[f"K{excel_row}"] = (
                f'=ROUND(IF(ISNUMBER(J{excel_row}),'
                f'H{excel_row}*J{excel_row},H{excel_row}),5)'
            )
            ws[f"L{excel_row}"] = f"=K{excel_row}*1.16"
            ws[f"M{excel_row}"] = f"=L{excel_row}/H{excel_row}"
            ws[f"P{excel_row}"] = f"=(100%+O{excel_row})*M{excel_row}"
            ws[f"S{excel_row}"] = f"=(R{excel_row}-M{excel_row})/M{excel_row}"
            ws[f"U{excel_row}"] = f"=(T{excel_row}-M{excel_row})/M{excel_row}"
            ws[f"W{excel_row}"] = f"=V{excel_row}/E{excel_row}"

        # Total VAT amount, matching the Dabu pattern.
        total_row = len(export_df) + 2
        ws[f"L{total_row}"] = f"=SUM(L2:L{total_row-1})"

        # Formatting.
        money_cols = ["J", "K", "L", "M", "P", "R", "S", "T", "U", "V", "W", "X", "Y"]
        percent_cols = ["O", "S", "U"]

        for col in money_cols:
            for cell in ws[col][1:]:
                cell.number_format = '#,##0.00'

        for col in percent_cols:
            for cell in ws[col][1:]:
                cell.number_format = '0.00%'

        for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "N", "Q"]:
            ws.column_dimensions[col].width = 18

        for col in ["D", "F", "G", "Q"]:
            ws.column_dimensions[col].width = 30

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

    output.seek(0)
    return output.getvalue()


# ============================================================
# SESSION STATE
# ============================================================

if "source_data" not in st.session_state:
    st.session_state.source_data = None

if "pricing_data" not in st.session_state:
    st.session_state.pricing_data = None

if "invoice_name" not in st.session_state:
    st.session_state.invoice_name = None


# ============================================================
# UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "Upload QuickBooks Excel file",
    type=["xlsx", "xls"],
    help="The importer accepts different QuickBooks column layouts. "
         "The Dabu pricing formulas remain constant."
)

if uploaded_file is not None:
    if st.session_state.invoice_name != uploaded_file.name:
        try:
            raw = pd.read_excel(
                uploaded_file,
                sheet_name="Sheet1",
                header=None
            )

            source_data = standardise_quickbooks(raw)
            pricing_data = build_pricing_table(source_data)

            st.session_state.source_data = source_data
            st.session_state.pricing_data = pricing_data
            st.session_state.invoice_name = uploaded_file.name

        except Exception as exc:
            st.session_state.source_data = None
            st.session_state.pricing_data = None
            st.error(f"Could not process the invoice: {exc}")


# ============================================================
# MAIN WORKSPACE
# ============================================================

if st.session_state.source_data is not None:
    source_data = st.session_state.source_data
    pricing_data = st.session_state.pricing_data

    st.success(
        f"{len(source_data)} product(s) imported from "
        f"{st.session_state.invoice_name}."
    )

    # --------------------------------------------------------
    # Invoice summary
    # --------------------------------------------------------
    c1, c2, c3 = st.columns(3)

    c1.metric("Products", len(source_data))
    c2.metric(
        "Quantity",
        f"{source_data['Qty'].sum():,.0f}"
    )
    c3.metric(
        "Purchase Amount",
        f"KES {source_data['Amount'].sum():,.2f}"
    )

    # --------------------------------------------------------
    # Original purchase data
    # --------------------------------------------------------
    with st.expander("1. Review imported purchase data", expanded=True):
        display_source = source_data[
            ["Product", "Qty", "U/M", "Cost Price", "Amount"]
        ].copy()

        st.dataframe(
            display_source,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Cost Price": st.column_config.NumberColumn(
                    "Cost Price",
                    format="KES %.2f"
                ),
                "Amount": st.column_config.NumberColumn(
                    "Amount",
                    format="KES %.2f"
                ),
            }
        )

    # --------------------------------------------------------
    # Pricing worksheet
    # --------------------------------------------------------
    st.subheader("2. Pricing Worksheet")

    st.info(
        "The formulas are fixed from Dabu / PRICING.xlsx. "
        "Product details, margins, market range and selling prices "
        "can change."
    )

    editable_columns = [
        "MARGIN %",
        "MIN M%",
        "MARKET RANGE",
        "RECC S.P",
        "STS. S.P",
        "NEW S.P",
        "WS S.P",
        "RETAIL S.P",
    ]

    disabled_columns = [
        col for col in pricing_data.columns
        if col not in editable_columns
    ]

    edited = st.data_editor(
        pricing_data[EXPORT_COLUMNS],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=disabled_columns,
        column_config={
            "Cost Price": st.column_config.NumberColumn(
                "Cost Price", format="KES %.2f"
            ),
            "Amount": st.column_config.NumberColumn(
                "Amount", format="KES %.2f"
            ),
            "AMT (VAT)": st.column_config.NumberColumn(
                "AMT (VAT)", format="KES %.2f"
            ),
            "BP/C": st.column_config.NumberColumn(
                "BP/C", format="KES %.2f"
            ),
            "MIN M%": st.column_config.NumberColumn(
                "MIN M%", min_value=0.0, max_value=1.0,
                step=0.01, format="0.00%"
            ),
            "MIN S.P": st.column_config.NumberColumn(
                "MIN S.P", format="KES %.2f"
            ),
            "RECC S.P": st.column_config.NumberColumn(
                "RECC S.P", min_value=0.0, step=1.0,
                format="KES %.2f"
            ),
            "RECC MARGIN %": st.column_config.NumberColumn(
                "RECC MARGIN %", format="0.00%"
            ),
            "STS. S.P": st.column_config.NumberColumn(
                "STS. S.P", min_value=0.0, step=1.0,
                format="KES %.2f"
            ),
            "CURRENT MARGIN %": st.column_config.NumberColumn(
                "CURRENT MARGIN %", format="0.00%"
            ),
            "NEW S.P": st.column_config.NumberColumn(
                "NEW S.P", min_value=0.0, step=1.0,
                format="KES %.2f"
            ),
            "BASE PRICE": st.column_config.NumberColumn(
                "BASE PRICE", format="KES %.2f"
            ),
            "WS S.P": st.column_config.NumberColumn(
                "WS S.P", min_value=0.0, step=1.0,
                format="KES %.2f"
            ),
            "RETAIL S.P": st.column_config.NumberColumn(
                "RETAIL S.P", min_value=0.0, step=1.0,
                format="KES %.2f"
            ),
        }
    )

    # --------------------------------------------------------
    # Recalculate fixed formulas after user edits
    # --------------------------------------------------------
    edited = edited.copy()

    for col in ["Qty", "P/C", "Cost Price", "MIN M%",
                "RECC S.P", "STS. S.P", "NEW S.P",
                "WS S.P", "RETAIL S.P"]:
        edited[col] = pd.to_numeric(edited[col], errors="coerce")

    edited["Amount"] = [
        formula_amount(q, c)
        for q, c in zip(edited["Qty"], edited["Cost Price"])
    ]

    edited["AMT (VAT)"] = edited["Amount"].apply(formula_vat)

    edited["BP/C"] = [
        formula_bpc(vat, qty)
        for vat, qty in zip(edited["AMT (VAT)"], edited["Qty"])
    ]

    edited["MIN S.P"] = [
        formula_min_sp(bp, margin)
        for bp, margin in zip(edited["BP/C"], edited["MIN M%"])
    ]

    edited["RECC MARGIN %"] = [
        formula_recc_margin(sp, bp)
        for sp, bp in zip(edited["RECC S.P"], edited["BP/C"])
    ]

    edited["CURRENT MARGIN %"] = [
        formula_current_margin(sp, bp)
        for sp, bp in zip(edited["STS. S.P"], edited["BP/C"])
    ]

    edited["BASE PRICE"] = [
        formula_base_price(sp, pc)
        for sp, pc in zip(edited["NEW S.P"], edited["P/C"])
    ]

    st.session_state.pricing_data = edited

    # --------------------------------------------------------
    # Simple decision view
    # --------------------------------------------------------
    st.subheader("3. Pricing Check")

    check = edited[
        [
            "Product", "BP/C", "MIN S.P", "MARKET RANGE",
            "RECC S.P", "RECC MARGIN %",
            "STS. S.P", "CURRENT MARGIN %",
            "NEW S.P", "BASE PRICE"
        ]
    ].copy()

    st.dataframe(
        check,
        use_container_width=True,
        hide_index=True,
        column_config={
            "BP/C": st.column_config.NumberColumn(format="KES %.2f"),
            "MIN S.P": st.column_config.NumberColumn(format="KES %.2f"),
            "RECC S.P": st.column_config.NumberColumn(format="KES %.2f"),
            "RECC MARGIN %": st.column_config.NumberColumn(format="0.00%"),
            "STS. S.P": st.column_config.NumberColumn(format="KES %.2f"),
            "CURRENT MARGIN %": st.column_config.NumberColumn(format="0.00%"),
            "NEW S.P": st.column_config.NumberColumn(format="KES %.2f"),
            "BASE PRICE": st.column_config.NumberColumn(format="KES %.2f"),
        }
    )

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------
    st.subheader("4. Export")

    excel_bytes = export_excel(edited)

    st.download_button(
        label="Download Pricing Worksheet",
        data=excel_bytes,
        file_name="Wholesale_Pricing_Worksheet.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

    st.caption(
        "Human authority remains with the wholesaler. "
        "The system calculates; the owner decides."
    )
else:
    st.warning("Upload a QuickBooks Excel file to begin.")
