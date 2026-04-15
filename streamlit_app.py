import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(
    page_title="HEAD OFFICE MIS 2025-26",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GOOGLE SHEET URL ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/18Ixbmk-vMsCMZtY88LlgER-PiL7Dd2tGI6djyJwcI3M/edit"

# --- DATA FUNCTION ---
@st.cache_data(ttl=600)
def get_and_clean_data(url):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)

        # ✅ FIXED: Use correct worksheet name
        df = conn.read(spreadsheet=url, worksheet="Weekly Dashboard")

        # ✅ CLEAN EMPTY
        df = df.dropna(how='all').dropna(axis=1, how='all')

        # ✅ STRIP COLUMN SPACES
        df.columns = df.columns.str.strip()

        # ✅ REQUIRED COLUMNS CHECK
        required_cols = [
            'Employee Name', 'FMS Planned', 'FMS Actual',
            'Checklist Planned', 'Checklist Actual',
            'PMS Planned', 'PMS Actual'
        ]

        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            st.error(f"Missing columns in sheet: {missing_cols}")
            st.stop()

        # ✅ SELECT + RENAME
        cleaned_df = df[required_cols].copy()
        cleaned_df.columns = ['Employee', 'FMS_P', 'FMS_A', 'REC_P', 'REC_A', 'PMS_P', 'PMS_A']

        # ✅ NUMERIC CONVERSION
        numeric_cols = ['FMS_P', 'FMS_A', 'REC_P', 'REC_A', 'PMS_P', 'PMS_A']
        for col in numeric_cols:
            cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce').fillna(0)

        # ✅ CALCULATIONS
        cleaned_df['Total_P'] = cleaned_df[['FMS_P', 'REC_P', 'PMS_P']].sum(axis=1)
        cleaned_df['Total_A'] = cleaned_df[['FMS_A', 'REC_A', 'PMS_A']].sum(axis=1)

        cleaned_df['MIS_Score'] = (
            cleaned_df['Total_A'] / cleaned_df['Total_P'].replace(0, 1) * 100
        ).round(1)

        cleaned_df['Overdue'] = (cleaned_df['Total_P'] - cleaned_df['Total_A']).clip(lower=0)

        cleaned_df['Overdue_Pct'] = (
            cleaned_df['Overdue'] / cleaned_df['Total_P'].replace(0, 1) * 100
        ).round(1)

        # ✅ REMOVE EMPTY EMPLOYEES
        cleaned_df = cleaned_df[cleaned_df['Employee'].notna() & (cleaned_df['Employee'] != '')]

        return cleaned_df

    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()


# --- LOAD DATA ---
df = get_and_clean_data(SHEET_URL)

# ✅ STOP IF NO DATA
if df.empty:
    st.warning("No data available. Check Google Sheet connection or structure.")
    st.stop()

# --- AGGREGATES ---
total_planned = df['Total_P'].sum()
total_actual = df['Total_A'].sum()
total_overdue = df['Overdue'].sum()

team_mis_score = round((total_actual / total_planned) * 100, 1) if total_planned else 0
team_overdue_pct = round((total_overdue / total_planned) * 100, 1) if total_planned else 0

status_color = "🟢" if team_mis_score > 80 else "🟡" if team_mis_score > 60 else "🔴"

# --- HEADER ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("HEAD OFFICE MIS 2025-26")
    st.caption("Data Source: Weekly Dashboard")
with col2:
    st.info(f"Meeting Mode: {status_color}")

# --- METRICS ---
st.subheader("Team Health")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("MIS SCORE", f"{team_mis_score}%")
with col2:
    st.metric("TOTAL PLANNED", int(total_planned))
with col3:
    st.metric("TOTAL ACTUAL", int(total_actual))
with col4:
    st.metric("OVERDUE %", f"{team_overdue_pct}%")

# --- SCATTER PLOT ---
st.subheader("Performance Quadrant")

fig = px.scatter(
    df,
    x="MIS_Score",
    y="Overdue_Pct",
    size="Total_P",
    color="Employee",
    hover_name="Employee",
    size_max=40
)

fig.add_hline(y=15, line_dash="dash")
fig.add_vline(x=70, line_dash="dash")

st.plotly_chart(fig, use_container_width=True)

# --- TABLE ---
st.subheader("Individual Performance")

df_sorted = df.sort_values(by="MIS_Score", ascending=False)

df_display = df_sorted[['Employee', 'MIS_Score', 'FMS_A', 'REC_A', 'PMS_A', 'Overdue_Pct']]
df_display.columns = ['Member', 'Score %', 'FMS Done', 'REC Done', 'PMS Done', 'Overdue %']

st.dataframe(df_display, use_container_width=True, hide_index=True)
