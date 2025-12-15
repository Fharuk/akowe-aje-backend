import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import os
from dotenv import load_dotenv

# secrets 
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets["SUPABASE_URL"]
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets["SUPABASE_KEY"]

# Initialize Supabase
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# Page Config
st.set_page_config(page_title="AkoweAje Live Ledger", page_icon="🦅", layout="wide")

# Custom CSS 
st.markdown("""
    <style>
    .big-font { font-size: 24px !important; font-weight: bold; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("🦅 AkoweAje: The Informal Economy Ledger")
st.markdown("Real-time financial tracking for traders (Powered by Awarri & Llama-3)")

# Fetch Data
def get_data():
    response = supabase.table("transactions").select("*").execute()
    return pd.DataFrame(response.data)

df = get_data()

if not df.empty:
    # Convert types
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    df['profit'] = pd.to_numeric(df['profit'], errors='coerce').fillna(0)

    #  KPI ROW 
    col1, col2, col3, col4 = st.columns(4)
    
    total_sales = df[df['intent'] == 'SALE']['amount'].sum()
    total_profit = df[df['intent'] == 'SALE']['profit'].sum()
    tx_count = len(df)
    unique_traders = df['user_phone'].nunique()

    with col1:
        st.metric("💰 Total Volume", f"₦{total_sales:,.0f}")
    with col2:
        st.metric("📈 Total Profit", f"₦{total_profit:,.0f}")
    with col3:
        st.metric("🧾 Transactions", tx_count)
    with col4:
        st.metric("👥 Active Traders", unique_traders)

    st.divider()

    #  CHARTS ROW 
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📊 Sales Velocity")
        # Group by Date
        sales_over_time = df[df['intent'] == 'SALE'].groupby(df['created_at'].dt.date)['amount'].sum().reset_index()
        fig_line = px.line(sales_over_time, x='created_at', y='amount', title="Daily Revenue Trend", markers=True)
        fig_line.update_layout(xaxis_title="Date", yaxis_title="Amount (₦)")
        st.plotly_chart(fig_line, use_container_width=True)

    with c2:
        st.subheader("📦 Product Mix")
        # Extract product names roughly or just count intents if items aren't clean
        # Let's clean up 'item' for a pie chart
        top_items = df[df['intent'] == 'SALE']['item'].value_counts().head(5).reset_index()
        top_items.columns = ['item', 'count']
        fig_pie = px.pie(top_items, values='count', names='item', title="Top Selling Items", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    #  LIVE TABLE 
    st.subheader("📝 Recent Transactions (Live Feed)")
    st.dataframe(
        df[['created_at', 'user_phone', 'intent', 'item', 'amount', 'profit']].sort_values(by='created_at', ascending=False),
        use_container_width=True,
        hide_index=True
    )
    
    # Auto-refresh button
    if st.button('🔄 Refresh Data'):
        st.rerun()

else:
    st.info("Waiting for first transaction... Send a message to the bot!")
