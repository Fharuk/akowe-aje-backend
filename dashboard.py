import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Config & Setup
st.set_page_config(
    page_title="AkoweAje Mission Control",
    page_icon="📊",
    layout="wide"
)

load_dotenv()

# Initialize Database Connection
try:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
except:
    st.error("❌ Supabase Keys missing! Check .env file.")
    st.stop()

# 2. Custom CSS for "Dark Mode" Finance Look
st.markdown("""
<style>
    .metric-card {
        background-color: #0e1117;
        border: 1px solid #303030;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .stDataFrame { border: 1px solid #303030; }
</style>
""", unsafe_allow_html=True)

# 3. The Header
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.header("🦅")
with col_title:
    st.title("AkoweAje Mission Control")
    st.caption("Real-Time Financial Intelligence for the Informal Economy | Powered by **Awarri**")

st.divider()

# 4. The Live Data Loop
placeholder = st.empty()

while True:
    with placeholder.container():
        # A. Fetch Data
        try:
            # We fetch slightly more data to ensure charts look good
            response = supabase.table("transactions").select("*").order("created_at", desc=True).limit(100).execute()
            data = response.data
        except Exception as e:
            st.error(f"Database Error: {e}")
            time.sleep(5)
            continue

        if not data:
            st.info("Waiting for transactions... Send a voice note!")
            time.sleep(2)
            continue

        # B. Process Data
        df = pd.DataFrame(data)
        
        # Calculate Metrics
        total_sales = df[df['intent'] == 'SALE']['amount'].sum()
        total_debt = df[df['intent'] == 'DEBT']['amount'].sum()
        transaction_count = len(df)
        
        # C. KPI Row
        kpi1, kpi2, kpi3 = st.columns(3)
        
        with kpi1:
            st.metric(label="💰 Total Sales Recorded", value=f"₦{total_sales:,.0f}")
        with kpi2:
            st.metric(label="📕 Outstanding Debt", value=f"₦{total_debt:,.0f}")
        with kpi3:
            st.metric(label="📊 Transactions Logged", value=transaction_count)

        # D. Visuals Row
        chart_col, table_col = st.columns([2, 3])
        
        with chart_col:
            st.subheader("Sales Velocity")
            if not df.empty:
                # Group by Item for a clean chart
                sales_df = df[df['intent'] == 'SALE']
                if not sales_df.empty:
                    chart_data = sales_df.groupby('item')['amount'].sum().reset_index()
                    fig = px.bar(chart_data, x='item', y='amount', color='amount', 
                                 color_continuous_scale='Greens', template='plotly_dark')
                    
                    # --- CRITICAL FIX: Unique Key for every loop iteration ---
                    # We also switched to width="stretch" to stop the warnings
                    st.plotly_chart(fig, key=f"sales_chart_{time.time()}", selection_mode="points")
                else:
                    st.info("No sales data yet.")

        with table_col:
            st.subheader("🔴 Live Ledger Feed")
            # Clean up the table for display
            if not df.empty:
                display_df = df[['created_at', 'intent', 'item', 'amount', 'customer']]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Refresh Rate (Slower to prevent UI glitches)
        time.sleep(3)