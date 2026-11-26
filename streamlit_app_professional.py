"""
Retail Sales Intelligence — Professional Streamlit Dashboard
============================================================
Run from the project root:
    ..\.venv\Scripts\python.exe -m streamlit run app\streamlit_app_professional.py

Expected dataset:
    data\raw\Sample - Superstore.csv

If the CSV is not found, use the file uploader in the dashboard.
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------- PAGE SETUP -----------------------------
st.set_page_config(
    page_title="Retail Sales Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional navy / blue / teal palette
NAVY = "#14213D"
BLUE = "#2563EB"
TEAL = "#0F766E"
GOLD = "#F59E0B"
RED = "#DC2626"
BG = "#F4F7FB"
TEXT = "#172033"
MUTED = "#64748B"

st.markdown(
    f"""
    <style>
    .stApp {{ background: {BG}; color: {TEXT}; }}
    [data-testid="stSidebar"] {{ background: {NAVY}; }}
    [data-testid="stSidebar"] * {{ color: #F8FAFC !important; }}
    .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; }}
    .hero {{
        background: linear-gradient(115deg, {NAVY} 0%, #1D4ED8 100%);
        padding: 28px 32px; border-radius: 18px; color: white;
        margin-bottom: 22px; box-shadow: 0 8px 24px rgba(20,33,61,.14);
    }}
    .hero h1 {{ color: white !important; font-size: 30px; margin: 0 0 7px 0; }}
    .hero p {{ color: #DBEAFE !important; margin: 0; font-size: 14px; }}
    div[data-testid="stMetric"] {{
        background: white; border: 1px solid #E2E8F0; padding: 16px 18px;
        border-radius: 14px; box-shadow: 0 3px 12px rgba(15,23,42,.04);
    }}
    div[data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-weight: 600; }}
    div[data-testid="stMetricValue"] {{ color: {NAVY} !important; font-weight: 750; }}
    h2, h3 {{ color: {NAVY} !important; }}
    .small-note {{ color: {MUTED}; font-size: 12px; }}
    /* High-contrast tab names and section labels */
    div[data-testid="stTabs"] button,
    button[data-baseweb="tab"] {{
        color: #14213D !important;
        font-weight: 750 !important;
        opacity: 1 !important;
    }}
    div[data-testid="stTabs"] button[aria-selected="true"],
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #1D4ED8 !important;
        border-bottom-color: #2563EB !important;
    }}
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    label {{
        color: #172033 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- DATA LOADING -----------------------------
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "raw" / "Sample - Superstore.csv"

REQUIRED = ["Order Date", "Sales", "Profit", "Quantity", "Category"]
ALIASES = {
    "Order Date": ["Order Date", "order_date"],
    "Sales": ["Sales", "sales"],
    "Profit": ["Profit", "profit"],
    "Quantity": ["Quantity", "quantity"],
    "Category": ["Category", "category"],
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename = {}
    for standard, candidates in ALIASES.items():
        for candidate in candidates:
            if candidate in df.columns:
                rename[candidate] = standard
                break
    return df.rename(columns=rename)

@st.cache_data(show_spinner=False)
def read_csv_file(file_or_path):
    return pd.read_csv(file_or_path, encoding_errors="replace")

def load_data():
    if DEFAULT_DATA.exists():
        try:
            return read_csv_file(DEFAULT_DATA), str(DEFAULT_DATA)
        except Exception as exc:
            st.sidebar.error(f"Could not read default CSV: {exc}")
    uploaded = st.sidebar.file_uploader("Upload your Superstore CSV", type=["csv"])
    if uploaded is not None:
        try:
            return read_csv_file(uploaded), uploaded.name
        except Exception as exc:
            st.error(f"Could not read uploaded file: {exc}")
    return None, None

raw, source_name = load_data()

st.markdown(
    """
    <div class="hero">
      <h1>Retail Sales Intelligence</h1>
      <p>Executive overview • Sales performance • Product insights • Customer analytics</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if raw is None:
    st.info(
        "Dataset not found automatically. Upload **Sample - Superstore.csv** "
        "using the sidebar, or place it in `data/raw/`."
    )
    st.stop()

df = normalize_columns(raw)

missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error(f"Required columns are missing: {', '.join(missing)}")
    st.write("Columns found in your file:", list(df.columns))
    st.stop()

# Parse / clean types
df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
for col in ["Sales", "Profit", "Quantity", "Discount"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["Order Date", "Sales", "Profit", "Quantity", "Category"]).copy()
df["Order Year"] = df["Order Date"].dt.year
df["Order Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
df["Order Month Label"] = df["Order Month"].dt.strftime("%b %Y")

# ----------------------------- SIDEBAR FILTERS -----------------------------
st.sidebar.markdown("## Dashboard Controls")
st.sidebar.caption(f"Data source: {source_name}")
currency_mode = st.sidebar.selectbox(
    "Display currency",
    ["INR (converted from USD)", "Original dataset currency (USD)"],
    index=0,
)
rate = 92.93
if currency_mode.startswith("INR"):
    rate = st.sidebar.number_input(
        "USD → INR conversion rate",
        min_value=1.0,
        max_value=200.0,
        value=92.93,
        step=0.10,
        help="Editable reference rate. Change this to the rate you want to use.",
    )
else:
    rate = 1.0

def amount(value):
    symbol = "₹" if currency_mode.startswith("INR") else "$"
    return f"{symbol}{value * rate:,.0f}"

def amount_axis():
    return "₹" if currency_mode.startswith("INR") else "$"

years = sorted(df["Order Year"].dropna().unique().tolist())
selected_years = st.sidebar.multiselect("Order year", years, default=years)
categories = sorted(df["Category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Category", categories, default=categories)

regions = sorted(df["Region"].dropna().unique().tolist()) if "Region" in df.columns else []
selected_regions = st.sidebar.multiselect("Region", regions, default=regions) if regions else []

filtered = df[df["Order Year"].isin(selected_years) & df["Category"].isin(selected_categories)].copy()
if regions and selected_regions:
    filtered = filtered[filtered["Region"].isin(selected_regions)]
elif regions and not selected_regions:
    filtered = filtered.iloc[0:0]

if filtered.empty:
    st.warning("No rows match the selected filters. Choose at least one year and category.")
    st.stop()

# ----------------------------- KPI METRICS -----------------------------
sales_total = filtered["Sales"].sum()
profit_total = filtered["Profit"].sum()
orders = filtered["Order ID"].nunique() if "Order ID" in filtered.columns else len(filtered)
customers = filtered["Customer ID"].nunique() if "Customer ID" in filtered.columns else None
quantity = filtered["Quantity"].sum()
margin = (profit_total / sales_total * 100) if sales_total else 0

st.markdown("### Executive Overview")
kpis = st.columns(5)
kpis[0].metric("Total Sales", amount(sales_total))
kpis[1].metric("Total Profit", amount(profit_total))
kpis[2].metric("Orders", f"{orders:,.0f}")
kpis[3].metric("Profit Margin", f"{margin:.1f}%")
kpis[4].metric("Units Sold", f"{quantity:,.0f}")
if customers is not None:
    st.caption(f"Unique customers in the current selection: **{customers:,}**")
st.markdown(
    f'<div class="small-note">Currency: {currency_mode}. '
    f'INR mode uses the editable reference rate ₹{rate:,.2f} per USD; '
    'it is a conversion for display, not a live exchange-rate feed.</div>',
    unsafe_allow_html=True,
)

# ----------------------------- TABS -----------------------------
tab_overview, tab_sales, tab_products, tab_customers, tab_quality = st.tabs(
    ["Overview", "Sales Analytics", "Product Analytics", "Customer Analytics", "Data Quality"]
)

plot_template = "plotly_white"
common_layout = dict(
    template=plot_template,
    font=dict(family="Arial", size=13, color="#172033"),
    title_font=dict(family="Arial", size=18, color="#14213D"),
    legend=dict(font=dict(family="Arial", size=12, color="#172033")),
    xaxis=dict(
        title_font=dict(size=13, color="#172033"),
        tickfont=dict(size=12, color="#334155"),
        showline=True, linecolor="#CBD5E1",
        gridcolor="#E2E8F0",
    ),
    yaxis=dict(
        title_font=dict(size=13, color="#172033"),
        tickfont=dict(size=12, color="#334155"),
        showline=False,
        gridcolor="#E2E8F0",
    ),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=35, r=25, t=65, b=35),
)

with tab_overview:
    left, right = st.columns([1.55, 1])
    with left:
        monthly = (
            filtered.groupby("Order Month", as_index=False)
            .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
            .sort_values("Order Month")
        )
        monthly["Sales Display"] = monthly["Sales"] * rate
        monthly["Profit Display"] = monthly["Profit"] * rate
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly["Order Month"], y=monthly["Sales Display"],
            name="Sales", mode="lines+markers",
            line=dict(color=BLUE, width=3), fill="tozeroy",
            fillcolor="rgba(37,99,235,0.08)",
        ))
        fig.add_trace(go.Scatter(
            x=monthly["Order Month"], y=monthly["Profit Display"],
            name="Profit", mode="lines+markers",
            line=dict(color=TEAL, width=3),
        ))
        fig.update_layout(title="Monthly Sales & Profit Trend", **common_layout)
        fig.update_yaxes(title=f"Amount ({amount_axis()})")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        cat = filtered.groupby("Category", as_index=False)["Sales"].sum()
        fig = px.pie(
            cat, names="Category", values="Sales", hole=0.58,
            color_discrete_sequence=[BLUE, TEAL, GOLD],
            title="Sales Mix by Category",
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(**common_layout)
        st.plotly_chart(fig, use_container_width=True)

    if "Region" in filtered.columns:
        reg = filtered.groupby("Region", as_index=False).agg(
            Sales=("Sales", "sum"), Profit=("Profit", "sum")
        ).sort_values("Sales", ascending=True)
        reg["Sales Display"] = reg["Sales"] * rate
        fig = px.bar(
            reg, x="Sales Display", y="Region", orientation="h",
            title="Sales by Region", text_auto=".2s",
            color="Sales Display", color_continuous_scale=["#BFDBFE", BLUE],
        )
        fig.update_layout(**common_layout, coloraxis_showscale=False)
        fig.update_xaxes(title=f"Sales ({amount_axis()})")
        st.plotly_chart(fig, use_container_width=True)

with tab_sales:
    st.subheader("Sales Performance")
    c1, c2 = st.columns(2)
    with c1:
        if "Segment" in filtered.columns:
            seg = filtered.groupby("Segment", as_index=False).agg(
                Sales=("Sales", "sum"), Profit=("Profit", "sum")
            )
            seg["Sales Display"] = seg["Sales"] * rate
            fig = px.bar(
                seg, x="Segment", y="Sales Display", color="Segment",
                title="Sales by Customer Segment",
                color_discrete_sequence=[BLUE, TEAL, GOLD],
                text_auto=".2s",
            )
            fig.update_layout(**common_layout, showlegend=False)
            fig.update_yaxes(title=f"Sales ({amount_axis()})")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Segment column is not available in this dataset.")
    with c2:
        if "Region" in filtered.columns:
            reg = filtered.groupby("Region", as_index=False).agg(
                Sales=("Sales", "sum"), Profit=("Profit", "sum")
            )
            reg["Profit Display"] = reg["Profit"] * rate
            fig = px.bar(
                reg, x="Region", y="Profit Display", color="Region",
                title="Profit by Region",
                color_discrete_sequence=[BLUE, TEAL, GOLD, "#7C3AED"],
                text_auto=".2s",
            )
            fig.update_layout(**common_layout, showlegend=False)
            fig.update_yaxes(title=f"Profit ({amount_axis()})")
            st.plotly_chart(fig, use_container_width=True)

    if "Order Date" in filtered.columns:
        yearly = filtered.groupby("Order Year", as_index=False).agg(
            Sales=("Sales", "sum"), Profit=("Profit", "sum")
        )
        yearly["Sales Display"] = yearly["Sales"] * rate
        fig = px.bar(
            yearly, x="Order Year", y="Sales Display",
            title="Yearly Sales Comparison", text_auto=".2s",
            color_discrete_sequence=[BLUE],
        )
        fig.update_layout(**common_layout)
        fig.update_yaxes(title=f"Sales ({amount_axis()})")
        st.plotly_chart(fig, use_container_width=True)

with tab_products:
    st.subheader("Product Performance")
    if "Sub-Category" in filtered.columns:
        product = filtered.groupby("Sub-Category", as_index=False).agg(
            Sales=("Sales", "sum"), Profit=("Profit", "sum"),
            Quantity=("Quantity", "sum")
        ).sort_values("Sales", ascending=False)
        product["Sales Display"] = product["Sales"] * rate
        product["Profit Display"] = product["Profit"] * rate
        fig = px.bar(
            product.sort_values("Profit Display"),
            x="Profit Display", y="Sub-Category", orientation="h",
            title="Profit by Sub-Category", color="Profit Display",
            color_continuous_scale=["#FCA5A5", "#F8FAFC", TEAL],
            text_auto=".2s",
        )
        fig.update_layout(**common_layout, coloraxis_showscale=False)
        fig.update_xaxes(title=f"Profit ({amount_axis()})")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("#### Top 10 Sub-Categories by Sales")
        st.dataframe(
            product.head(10)[["Sub-Category", "Sales Display", "Profit Display", "Quantity"]]
            .rename(columns={"Sales Display": f"Sales ({amount_axis()})",
                             "Profit Display": f"Profit ({amount_axis()})"}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Sub-Category column is not available.")

with tab_customers:
    st.subheader("Customer Analytics")
    if "Customer ID" in filtered.columns:
        cust = filtered.groupby("Customer ID", as_index=False).agg(
            Sales=("Sales", "sum"), Profit=("Profit", "sum"),
            Orders=("Order ID", "nunique") if "Order ID" in filtered.columns
            else ("Sales", "count")
        )
        cust["Sales Display"] = cust["Sales"] * rate
        fig = px.scatter(
            cust, x="Sales Display", y="Profit", size="Orders",
            hover_name="Customer ID", title="Customer Sales vs Profit",
            color="Profit", color_continuous_scale=["#FCA5A5", BLUE, TEAL],
        )
        fig.update_layout(**common_layout)
        fig.update_xaxes(title=f"Customer Sales ({amount_axis()})")
        fig.update_yaxes(title="Profit (original dataset units)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Customer-level profit remains in the dataset's original units in this scatter plot.")
        st.markdown("#### Top 10 Customers by Sales")
        top = cust.nlargest(10, "Sales")[["Customer ID", "Sales Display", "Profit", "Orders"]]
        top = top.rename(columns={"Sales Display": f"Sales ({amount_axis()})"})
        st.dataframe(top, use_container_width=True, hide_index=True)
    else:
        st.info("Customer ID column is not available.")

with tab_quality:
    st.subheader("Data Quality Summary")
    q1, q2, q3 = st.columns(3)
    q1.metric("Rows loaded", f"{len(raw):,}")
    q2.metric("Rows after required-field cleaning", f"{len(df):,}")
    q3.metric("Rows in current filters", f"{len(filtered):,}")
    quality = pd.DataFrame({
        "Column": raw.columns,
        "Missing Values": [int(raw[c].isna().sum()) for c in raw.columns],
        "Missing %": [round(raw[c].isna().mean() * 100, 2) for c in raw.columns],
    }).sort_values("Missing Values", ascending=False)
    st.markdown("#### Missing Values by Column")
    st.dataframe(quality, use_container_width=True, hide_index=True)
    st.markdown("#### Data Preview")
    st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Retail Sales Intelligence | Built with Python, Pandas, Plotly and Streamlit")
