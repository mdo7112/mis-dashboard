import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="HEAD OFFICE MIS 2025-26",
    page_icon="📊",
    layout="wide", # Desktop layout (will respond to mobile)
    initial_sidebar_state="collapsed"
)

# A simplified mobile detection heuristic (can be expanded)
is_mobile = st.session_state.get("is_mobile", False)

# Simple custom CSS for styling and responsiveness
st.markdown("""
<style>
    .metric-card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #ededed;
        text-align: center;
    }
    .metric-title { font-size: 14px; color: #5f6368; margin-bottom: 5px; }
    .metric-value-green { font-size: 32px; font-weight: bold; color: #10B981; }
    .metric-value-red { font-size: 32px; font-weight: bold; color: #EF4444; }
    [data-testid="stMetricValue"] { font-size: 2.5rem !important; } /* Make metrics bold */
    
    /* Responsive Adjustments */
    @media (max-width: 640px) {
        .metric-value-green, .metric-value-red { font-size: 24px; }
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATA FETCHING & CLEANING ---
# Paste your public Google Sheet URL here (replacing the one below)
SHEET_URL = "https://docs.google.com/spreadsheets/d/18Ixbmk-vMsCMZtY88LlgER-PiL7Dd2tGI8djyJwcI3M/edit#gid=1525910319"

@st.cache_data(ttl=600) # Cache data for 10 minutes to improve performance
def get_and_clean_data(url):
    try:
        # Connect to Google Sheets
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Read the 'Week 15' tab specifically (using the gid from your link)
        df = conn.read(spreadsheet=url, worksheet="1525910319")
        
        # 1. CLEANING: Remove completely empty rows/columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # 2. CLEANING: Define meaningful columns and rename
        # We need: Employee Name, FMS Planned/Actual, Recurring Planned/Actual, PMS Planned/Actual
        # Adjust these headers if your sheet columns change
        cleaned_df = df[['Employee Name', 'FMS Planned', 'FMS Actual', 'Checklist Planned', 'Checklist Actual', 'PMS Planned', 'PMS Actual']].copy()
        cleaned_df.columns = ['Employee', 'FMS_P', 'FMS_A', 'REC_P', 'REC_A', 'PMS_P', 'PMS_A']
        
        # 3. DATA TYPING: Ensure numeric columns are actually numbers (handle errors)
        numeric_cols = ['FMS_P', 'FMS_A', 'REC_P', 'REC_A', 'PMS_P', 'PMS_A']
        for col in numeric_cols:
            cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce').fillna(0).astype(int)

        # 4. CALCULATIONS: Generate aggregate metrics
        # (Using a simple 1:1:1 weighted aggregate for this test)
        cleaned_df['Total_P'] = cleaned_df['FMS_P'] + cleaned_df['REC_P'] + cleaned_df['PMS_P']
        cleaned_df['Total_A'] = cleaned_df['FMS_A'] + cleaned_df['REC_A'] + cleaned_df['PMS_A']
        
        # Avoid division by zero
        cleaned_df['MIS_Score'] = (cleaned_df['Total_A'] / cleaned_df['Total_P'].replace(0, 1) * 100).round(1)
        cleaned_df['Overdue'] = (cleaned_df['Total_P'] - cleaned_df['Total_A']).clip(lower=0)
        cleaned_df['Overdue_Pct'] = (cleaned_df['Overdue'] / cleaned_df['Total_P'].replace(0, 1) * 100).round(1)

        # Remove HOD/MD names if they are 'None' or empty (cleaning based on actual sheet)
        cleaned_df = cleaned_df[cleaned_df['Employee'].notna() & (cleaned_df['Employee'] != '')]

        return cleaned_df

    except Exception as e:
        st.error(f"Error connecting to Google Sheets. Verify the link is public and headers are correct. Error: {e}")
        return pd.DataFrame() # Return empty DataFrame on failure

# Load the live data
df = get_and_clean_data(SHEET_URL)

# --- GLOBAL VARIABLES & AGGREGATES ---
if not df.empty:
    total_planned = df['Total_P'].sum()
    total_actual = df['Total_A'].sum()
    total_overdue = df['Overdue'].sum()
    
    # Team Aggregate MIS Score
    if total_planned > 0:
        team_mis_score = round((total_actual / total_planned) * 100, 1)
        team_overdue_pct = round((total_overdue / total_planned) * 100, 1)
    else:
        team_mis_score = 0
        team_overdue_pct = 0
else:
    team_mis_score = 0
    total_planned = 0
    total_actual = 0
    team_overdue_pct = 0

# Determine global color status (🟢/🟡/🔴)
status_color = "🟢" if team_mis_score > 80 else "🟡" if team_mis_score > 60 else "🔴"

# --- MAIN PAGE LAYOUT ---

# Top Header: Context & Controls
header_col1, header_col2, header_col3 = st.columns([2, 2, 1])
with header_col1:
    st.title("HEAD OFFICE MIS 2025-26")
    st.caption("Data Source: Week 15 Live Google Sheet")
with header_col2:
    # Simulating a meeting mode timer/status
    st.info(f"**Meeting Mode:** Active {status_color}")
with header_col3:
    # A manual filter (for testing delegation)
    selected_team = st.selectbox("Team/Dept", ["All Operations", "HR", "Sales"], label_visibility="collapsed")


# Section 1: Dynamic Top Stats (Desktop Grid vs. Mobile Vertical)
st.write("---")
st.subheader("Team Health (Week 15)")

# Metric definition logic (Gauge)
metric_agg_score = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = team_mis_score,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': "TEAM MIS SCORE", 'font': {'size': 18}},
    gauge = {
        'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
        'bar': {'color': "#10B981"},
        'bgcolor': "white",
        'borderwidth': 2,
        'bordercolor': "gray",
        'steps': [
            {'range': [0, 60], 'color': '#EF4444'},
            {'range': [60, 80], 'color': '#FBBF24'}],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 90}}))
metric_agg_score.update_layout(paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)", margin=dict(l=20,r=20,t=40,b=20), height=200)

# Render logic (Responsiveness Simulation)
col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1])
with col1:
    st.plotly_chart(metric_agg_score, use_container_width=True)
with col2:
    st.metric("TOTAL PLANNED", total_planned, help="Combined FMS + REC + PMS")
with col3:
    st.metric("TOTAL ACTUAL", total_actual, help="Tasks closed on time")
with col4:
    # Conditional color badge simulation
    overdue_class = "metric-value-red" if team_overdue_pct > 15 else "metric-value-green"
    st.markdown(f'<div class="metric-card"><div class="metric-title">OVERDUE %</div><div class="{overdue_class}">{team_overdue_pct}%</div></div>', unsafe_allow_html=True)


# Section 2: Accountability Charts (Performance Quadrant)
st.write("---")
st.subheader("Performance Quadrant (Accountability)")

# Build the interactive Scatter Plot (from the visual design)
# Bubble Size = Total Tasks (Weight)
fig_quadrant = px.scatter(df, x="MIS_Score", y="Overdue_Pct",
                 size="Total_P", color="Employee",
                 hover_name="Employee", size_max=40,
                 title="Team MIS Score vs. Overdue Rate",
                 labels={"MIS_Score": "MIS Score %", "Overdue_Pct": "Overdue Rate %"},
                 color_discrete_sequence=px.colors.qualitative.Safe)

# Add reference lines for standard/at-risk performance (as shown in visual)
fig_quadrant.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="Target Overdue Max")
fig_quadrant.add_vline(x=70, line_dash="dash", line_color="red", annotation_text="At-Risk Threshold")

# Shading for the "At-Risk" area (High Overdue, Low Score)
fig_quadrant.add_vrect(x0=0, x1=70, y0=15, y1=100, 
              fillcolor="#EF4444", opacity=0.1, layer="below", line_width=0)

# Render the interactive chart
st.plotly_chart(fig_quadrant, use_container_width=True)
st.caption("Bubbles in the RED SHADED area indicate individuals requiring HOD intervention.")


# Section 3: The Delegation Table (HOD Individual Review)
st.write("---")
st.subheader("Individual Performance List (Drill-Down)")
st.write("Sorting: Best Performing (MIS Score) to Least Performing.")

# Sort data by score (Descending)
df_sorted = df.sort_values(by="MIS_Score", ascending=False)

# Simplify columns for easy readability in meeting
df_display = df_sorted[['Employee', 'MIS_Score', 'FMS_A', 'REC_A', 'PMS_A', 'Overdue_Pct']]
df_display.columns = ['Member', 'Score %', 'FMS Done', 'REC Done', 'PMS Done', 'Overdue %']

# Basic Dataframe display with formatting (st.dataframe is interactive)
st.dataframe(df_display.style.format(subset=['Score %', 'Overdue %'], formatter="{:.1f}"), use_container_width=True, hide_index=True)

# Mobile simulations can be added here with conditional layout logic
