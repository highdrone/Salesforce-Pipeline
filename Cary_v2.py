import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time
import warnings
import urllib3
import os
import numpy as np
from simple_salesforce import Salesforce

# Suppress warnings
warnings.filterwarnings("ignore")
urllib3.disable_warnings()

# Page config optimized for 1080p
st.set_page_config(
    page_title="Cary Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS for 1080p display
st.markdown("""
<style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* CSS Variables */
    :root {
        --primary: #2563eb;
        --primary-dark: #1e40af;
        --primary-light: #60a5fa;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --info: #06b6d4;
        --purple: #8b5cf6;
        --pink: #ec4899;
        --bg-primary: #0f172a;
        --bg-secondary: #1e293b;
        --bg-card: #ffffff;
        --text-primary: #0f172a;
        --text-secondary: #64748b;
        --text-muted: #94a3b8;
        --border: #e2e8f0;
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
    }
    
    /* Reset and base styles */
    .main { 
        padding: 0; 
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        min-height: 100vh;
    }
    
    .block-container { 
        padding: 0; 
        max-width: 100%; 
        margin: 0;
    }
    
    /* Typography */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-primary);
        font-size: 14px;
    }
    
    /* Enhanced Header */
    .dashboard-header {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 50%, var(--primary-light) 100%);
        color: white;
        padding: 20px 30px;
        margin: 0;
        box-shadow: var(--shadow-lg);
        position: relative;
        overflow: hidden;
    }
    
    .dashboard-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    }
    
    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        z-index: 1;
    }
    
    .header-left {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    
    .dashboard-title {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .dashboard-subtitle {
        font-size: 14px;
        opacity: 0.95;
        font-weight: 400;
    }
    
    .header-stats {
        display: flex;
        gap: 30px;
        align-items: center;
    }
    
    .header-stat {
        text-align: center;
    }
    
    .header-stat-value {
        font-size: 24px;
        font-weight: 700;
        display: block;
    }
    
    .header-stat-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 0.9;
        margin-top: 2px;
    }
    
    .live-indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(255,255,255,0.2);
        padding: 6px 14px;
        border-radius: 20px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .live-dot {
        width: 8px;
        height: 8px;
        background: #10b981;
        border-radius: 50%;
        animation: pulse 2s infinite;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 1);
    }
    
    @keyframes pulse {
        0% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        }
        70% {
            box-shadow: 0 0 0 10px rgba(16, 185, 129, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
        }
    }
    
    /* Section headers */
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary);
        margin: 24px 20px 16px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .section-header::before {
        content: '';
        width: 4px;
        height: 24px;
        background: var(--primary);
        border-radius: 2px;
    }
    
    /* Enhanced Cards */
    .metric-card {
        background: var(--bg-card);
        border-radius: 16px;
        padding: 20px;
        height: 100%;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-xl);
        border-color: var(--primary-light);
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--primary), var(--primary-light));
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover::before {
        transform: scaleX(1);
    }
    
    .metric-icon {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, var(--primary-light), var(--primary));
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 12px;
        font-size: 20px;
    }
    
    .metric-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1;
        margin-bottom: 4px;
    }
    
    .metric-change {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        font-weight: 500;
        padding: 4px 8px;
        border-radius: 6px;
        margin-top: 8px;
    }
    
    .metric-change.positive {
        color: var(--success);
        background: rgba(16, 185, 129, 0.1);
    }
    
    .metric-change.negative {
        color: var(--danger);
        background: rgba(239, 68, 68, 0.1);
    }
    
    .metric-subtitle {
        font-size: 13px;
        color: var(--text-muted);
        margin-top: 4px;
    }
    
    /* Chart containers */
    .chart-container {
        background: var(--bg-card);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        margin: 0 20px 20px 20px;
    }
    
    .chart-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 16px;
    }
    
    /* Grid layouts */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        padding: 0 20px;
    }
    
    /* Progress bars */
    .progress-container {
        margin-top: 12px;
    }
    
    .progress-label {
        font-size: 11px;
        color: var(--text-secondary);
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
    }
    
    .progress-bar {
        height: 8px;
        background: var(--border);
        border-radius: 4px;
        overflow: hidden;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--primary), var(--primary-light));
        border-radius: 4px;
        transition: width 1s ease;
    }
    
    /* Table styles */
    .dataframe {
        font-size: 12px !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    
    .dataframe thead th {
        background: var(--bg-secondary) !important;
        color: white !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 11px !important;
        letter-spacing: 0.5px !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu, footer, header { 
        visibility: hidden; 
    }
    
    .viewerBadge_container__1QSob {
        display: none !important;
    }
    
    /* Responsive for 1080p */
    @media (min-width: 1920px) {
        .metrics-grid {
            grid-template-columns: repeat(4, 1fr);
        }
        
        .metric-value {
            font-size: 36px;
        }
    }
    
    /* Animation for numbers */
    @keyframes countUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .metric-value {
        animation: countUp 0.5s ease-out;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--border);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-dark);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.datetime.now()
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = []

# Auto-refresh function
def auto_refresh():
    time_since_refresh = (datetime.datetime.now() - st.session_state.last_refresh).total_seconds()
    if time_since_refresh > 600:  # 10 minutes
        st.session_state.refresh_count += 1
        st.session_state.last_refresh = datetime.datetime.now()
        if 'salesforce_data' in st.session_state:
            del st.session_state['salesforce_data']
        st.rerun()

# Enhanced fetch data function with error handling
@st.cache_data(ttl=600)
def fetch_opportunities():
    """Fetch opportunities from Salesforce with enhanced error handling"""
    try:
        sf = Salesforce(
            username="william.evans@avidex.com",
            password="D_w?ygrM6g9rp",
            security_token="V7W9o94PW3TVtBsqaS5zkNKS",
            domain='login'
        )
        
        query = """
        SELECT 
            Id, Name, StageName, Amount, CloseDate, CreatedDate, 
            Probability, Owner.Name, Type, Branch__c,
            Owner_Name__c, ForecastCategory, IsClosed, IsWon,
            ExpectedRevenue, NextStep, LeadSource
        FROM Opportunity
        WHERE IsDeleted = false
        AND Branch__c = '700'
        LIMIT 10000
        """
        
        result = sf.query_all(query)
        records = result['records']
        
        # Process records with enhanced data
        data = []
        for record in records:
            data.append({
                'Id': record.get('Id'),
                'Name': record.get('Name', 'Unknown'),
                'Stage': record.get('StageName'),
                'Amount': float(record.get('Amount', 0) or 0),
                'Close Date': record.get('CloseDate'),
                'Created Date': record.get('CreatedDate'),
                'Probability': float(record.get('Probability', 0) or 0),
                'Type': record.get('Type', 'Unknown'),
                'ForecastCategory': record.get('ForecastCategory', 'Unknown'),
                'Owner': record.get('Owner', {}).get('Name') if record.get('Owner') else record.get('Owner_Name__c', 'Unknown'),
                'IsClosed': record.get('IsClosed', False),
                'IsWon': record.get('IsWon', False),
                'ExpectedRevenue': float(record.get('ExpectedRevenue', 0) or 0),
                'NextStep': record.get('NextStep', ''),
                'LeadSource': record.get('LeadSource', 'Unknown')
            })
        
        df = pd.DataFrame(data)
        # Convert dates and handle timezone issues
        df['Close Date'] = pd.to_datetime(df['Close Date'], utc=True).dt.tz_localize(None)
        df['Created Date'] = pd.to_datetime(df['Created Date'], utc=True).dt.tz_localize(None)
        
        return df
        
    except Exception as e:
        st.error(f"⚠️ Connection Error: Unable to fetch Salesforce data. {str(e)}")
        return pd.DataFrame()

# Enhanced metrics calculation
def calculate_metrics(df):
    """Calculate comprehensive dashboard metrics"""
    if df.empty:
        return {
            'pipeline_current': 0,
            'pipeline_mtd': 0,
            'pipeline_3month': 0,
            'pipeline_fy': 0,
            'total_opps': 0,
            'project_forecast': 0,
            'project_mtd': 0,
            'trans_forecast': 0,
            'trans_mtd': 0,
            'service_forecast': 0,
            'service_mtd': 0,
            'win_rate': 0,
            'avg_deal_size': 0,
            'avg_days_to_close': 0,
            'top_lead_source': 'N/A'
        }
    
    # Date filters - ensure timezone consistency
    now = pd.Timestamp.now().tz_localize(None)
    current_month = now.month
    current_year = now.year
    
    # Filter valid forecast categories
    valid_forecast_categories = ['BestCase', 'Closed', 'Commit', 'Pipeline']
    filtered_df = df[df['ForecastCategory'].isin(valid_forecast_categories)].copy()
    
    # Ensure Close Date is timezone-naive for comparisons
    if not filtered_df.empty and 'Close Date' in filtered_df.columns:
        filtered_df['Close Date'] = pd.to_datetime(filtered_df['Close Date']).dt.tz_localize(None)
    
    # Date filters
    current_month_mask = (filtered_df['Close Date'].dt.month == current_month) & \
                        (filtered_df['Close Date'].dt.year == current_year)
    mtd_mask = (filtered_df['Close Date'] >= pd.Timestamp(current_year, current_month, 1)) & \
               (filtered_df['Close Date'] <= now)
    
    # Pipeline calculations
    pipeline_current = filtered_df[current_month_mask]['Amount'].sum()
    pipeline_mtd = filtered_df[mtd_mask]['Amount'].sum() if mtd_mask.any() else pipeline_current
    
    # 3-month pipeline
    three_month_end = now + pd.DateOffset(months=2)
    pipeline_3month = filtered_df[
        (filtered_df['Close Date'] >= now) & 
        (filtered_df['Close Date'] <= three_month_end)
    ]['Amount'].sum()
    
    # FY pipeline (through March 31, 2025)
    fy_start = pd.Timestamp(2024, 4, 1)
    fy_end = pd.Timestamp(2025, 3, 31)
    pipeline_fy = filtered_df[
        (filtered_df['Close Date'] >= fy_start) & 
        (filtered_df['Close Date'] <= fy_end)
    ]['Amount'].sum()
    
    # Sales by type
    current_month_df = filtered_df[current_month_mask]
    project_sales = current_month_df[current_month_df['Type'] == 'System']['Amount'].sum()
    trans_sales = current_month_df[current_month_df['Type'] == 'Transactional']['Amount'].sum()
    service_sales = current_month_df[current_month_df['Type'] == 'Service Agreement']['Amount'].sum()
    
    # Win rate calculation
    closed_opps = df[df['IsClosed'] == True]
    if len(closed_opps) > 0:
        won_opps = closed_opps[closed_opps['IsWon'] == True]
        win_rate = (len(won_opps) / len(closed_opps)) * 100
    else:
        win_rate = 0
    
    # Average deal size
    avg_deal_size = filtered_df[filtered_df['Amount'] > 0]['Amount'].mean() if len(filtered_df) > 0 else 0
    
    # Average days to close - with safer date handling
    closed_deals = df[(df['IsClosed'] == True) & (df['Created Date'].notna()) & (df['Close Date'].notna())].copy()
    if len(closed_deals) > 0:
        try:
            # Ensure both dates are timezone-naive for calculation
            closed_deals['Close Date'] = pd.to_datetime(closed_deals['Close Date']).dt.tz_localize(None)
            closed_deals['Created Date'] = pd.to_datetime(closed_deals['Created Date']).dt.tz_localize(None)
            closed_deals['Days to Close'] = (closed_deals['Close Date'] - closed_deals['Created Date']).dt.days
            avg_days_to_close = closed_deals['Days to Close'].mean()
        except Exception as e:
            # If date calculation fails, set to 0
            avg_days_to_close = 0
    else:
        avg_days_to_close = 0
    
    # Top lead source
    if 'LeadSource' in df.columns and len(df) > 0:
        lead_source_counts = df['LeadSource'].value_counts()
        top_lead_source = lead_source_counts.index[0] if len(lead_source_counts) > 0 else 'N/A'
    else:
        top_lead_source = 'N/A'
    
    # Total open opportunities
    open_opps = df[~df['Stage'].isin(['Closed Won', 'Closed Lost'])] if 'Stage' in df.columns else df
    total_open_opps = len(open_opps)
    
    return {
        'pipeline_current': pipeline_current,
        'pipeline_mtd': pipeline_mtd,
        'pipeline_3month': pipeline_3month,
        'pipeline_fy': pipeline_fy,
        'total_opps': total_open_opps,
        'project_forecast': project_sales,
        'project_mtd': project_sales,  # Using same as forecast for now
        'trans_forecast': trans_sales,
        'trans_mtd': trans_sales,
        'service_forecast': service_sales,
        'service_mtd': service_sales,
        'win_rate': win_rate,
        'avg_deal_size': avg_deal_size,
        'avg_days_to_close': avg_days_to_close,
        'top_lead_source': top_lead_source
    }

# Create enhanced gauge chart
def create_enhanced_gauge(value, max_value, title, target=None):
    """Create an enhanced gauge chart with target line"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = value,
        title = {'text': title, 'font': {'size': 14, 'color': '#0f172a', 'family': 'Inter'}},
        number = {'font': {'size': 32, 'color': '#0f172a', 'family': 'Inter'}, 'prefix': '$', 'valueformat': ',.0f'},
        delta = {'reference': target, 'relative': False, 'font': {'size': 14}} if target else None,
        gauge = {
            'axis': {'range': [0, max_value], 'tickwidth': 1, 'tickcolor': "#e2e8f0"},
            'bar': {'color': "#2563eb", 'thickness': 0.8},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e2e8f0",
            'steps': [
                {'range': [0, max_value * 0.25], 'color': "#dbeafe"},
                {'range': [max_value * 0.25, max_value * 0.5], 'color': "#bfdbfe"},
                {'range': [max_value * 0.5, max_value * 0.75], 'color': "#93c5fd"},
                {'range': [max_value * 0.75, max_value], 'color': "#60a5fa"}
            ],
            'threshold': {
                'line': {'color': "#dc2626", 'width': 3},
                'thickness': 0.75,
                'value': target if target else value * 0.9
            }
        }
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Inter, sans-serif', 'color': '#0f172a'}
    )
    
    return fig

# Create pipeline trend chart
def create_pipeline_trend(df):
    """Create a pipeline trend chart"""
    if df.empty:
        return None
    
    # Group by month
    df_copy = df.copy()
    df_copy['Month'] = df_copy['Close Date'].dt.to_period('M')
    monthly_pipeline = df_copy.groupby('Month')['Amount'].sum().reset_index()
    monthly_pipeline['Month'] = monthly_pipeline['Month'].dt.to_timestamp()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=monthly_pipeline['Month'],
        y=monthly_pipeline['Amount'],
        mode='lines+markers',
        name='Pipeline',
        line=dict(color='#2563eb', width=3),
        marker=dict(size=8, color='#2563eb'),
        fill='tonexty',
        fillcolor='rgba(37, 99, 235, 0.1)'
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        title="Pipeline Trend",
        title_font=dict(size=16, family='Inter'),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', zeroline=False, tickformat='$,.0f')
    )
    
    return fig

# Create sales funnel chart
def create_sales_funnel(df):
    """Create a sales funnel visualization"""
    if df.empty:
        return None
    
    stages_order = ['Prospecting', 'Qualification', 'Needs Analysis', 'Value Proposition', 
                   'Decision Makers', 'Proposal', 'Negotiation', 'Closed Won']
    
    stage_counts = df['Stage'].value_counts()
    funnel_data = []
    
    for stage in stages_order:
        if stage in stage_counts.index:
            funnel_data.append({
                'Stage': stage,
                'Count': stage_counts[stage],
                'Amount': df[df['Stage'] == stage]['Amount'].sum()
            })
    
    if not funnel_data:
        return None
    
    funnel_df = pd.DataFrame(funnel_data)
    
    fig = go.Figure(go.Funnel(
        y=funnel_df['Stage'],
        x=funnel_df['Count'],
        textposition="inside",
        textinfo="value+percent initial",
        opacity=0.85,
        marker=dict(
            color=['#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#dbeafe', '#10b981'],
            line=dict(width=2, color='white')
        ),
        connector={"line": {"color": "#e2e8f0", "width": 2}}
    ))
    
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=30, b=10),
        title="Sales Funnel",
        title_font=dict(size=16, family='Inter'),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=12)
    )
    
    return fig

# Create owner performance chart
def create_owner_performance(df):
    """Create enhanced owner performance bar chart"""
    if df.empty:
        return None
    
    valid_forecast_categories = ['BestCase', 'Closed', 'Commit', 'Pipeline']
    now = pd.Timestamp.now()
    current_month = now.month
    current_year = now.year
    
    filtered_df = df[
        (df['ForecastCategory'].isin(valid_forecast_categories)) &
        (df['Close Date'].dt.month == current_month) &
        (df['Close Date'].dt.year == current_year)
    ]
    
    if filtered_df.empty:
        return None
    
    owner_sales = filtered_df.groupby('Owner')['Amount'].sum().sort_values(ascending=True).tail(10)
    
    # Create gradient colors
    colors = ['#dbeafe', '#bfdbfe', '#93c5fd', '#60a5fa', '#3b82f6', 
              '#2563eb', '#1e40af', '#1e3a8a', '#172554', '#0c1a3d'][:len(owner_sales)]
    
    fig = go.Figure(go.Bar(
        x=owner_sales.values,
        y=owner_sales.index,
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='white', width=1)
        ),
        text=[f'${x:,.0f}' for x in owner_sales.values],
        textposition='outside',
        textfont=dict(size=11, family='Inter')
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        title="Top Performers",
        title_font=dict(size=16, family='Inter'),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0', tickformat='$,.0f'),
        yaxis=dict(showgrid=False),
        font=dict(family='Inter', size=11)
    )
    
    return fig

# Create opportunity type distribution
def create_type_distribution(df):
    """Create a donut chart for opportunity type distribution"""
    if df.empty:
        return None
    
    type_counts = df['Type'].value_counts()
    
    fig = go.Figure(go.Pie(
        labels=type_counts.index,
        values=type_counts.values,
        hole=0.6,
        marker=dict(
            colors=['#2563eb', '#10b981', '#f59e0b'],
            line=dict(color='white', width=2)
        ),
        textfont=dict(size=12, family='Inter'),
        textposition='outside',
        textinfo='label+percent'
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        title="Opportunity Distribution",
        title_font=dict(size=16, family='Inter'),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=11)
    )
    
    return fig

# Format currency with better formatting
def format_currency(value):
    """Format currency values with proper formatting"""
    if value >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:.0f}"

# Format percentage
def format_percentage(value):
    """Format percentage values"""
    return f"{value:.1f}%"

# Main app function
def main():
    # Check for auto-refresh
    auto_refresh()
    
    # Fetch data
    with st.spinner('🔄 Loading Salesforce data...'):
        df = fetch_opportunities()
        metrics = calculate_metrics(df)
    
    # Enhanced Header with live stats
    total_pipeline = metrics['pipeline_current'] + metrics['pipeline_3month']
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="header-content">
            <div class="header-left">
                <div class="dashboard-title">📊 Cary Sales Dashboard</div>
                <div class="dashboard-subtitle">Branch 700 • Real-time Performance Metrics</div>
            </div>
            <div class="header-stats">
                <div class="header-stat">
                    <span class="header-stat-value">{format_currency(total_pipeline)}</span>
                    <span class="header-stat-label">Total Pipeline</span>
                </div>
                <div class="header-stat">
                    <span class="header-stat-value">{metrics['total_opps']}</span>
                    <span class="header-stat-label">Active Deals</span>
                </div>
                <div class="header-stat">
                    <span class="header-stat-value">{format_percentage(metrics['win_rate'])}</span>
                    <span class="header-stat-label">Win Rate</span>
                </div>
                <div class="live-indicator">
                    <div class="live-dot"></div>
                    <span style="font-size: 12px; font-weight: 500;">LIVE</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Key Metrics Section
    st.markdown('<div class="section-header">Key Performance Indicators</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        mtd_change = ((metrics['pipeline_mtd'] / metrics['pipeline_current']) * 100) if metrics['pipeline_current'] > 0 else 0
        change_class = "positive" if mtd_change >= 50 else "negative"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">💰</div>
            <div class="metric-label">Current Month Pipeline</div>
            <div class="metric-value">{format_currency(metrics['pipeline_current'])}</div>
            <div class="metric-change {change_class}">
                {"↑" if mtd_change >= 50 else "↓"} {format_percentage(mtd_change)} MTD
            </div>
            <div class="progress-container">
                <div class="progress-label">
                    <span>Progress to Goal</span>
                    <span>{format_percentage(metrics['pipeline_current']/25_000_000*100 if metrics['pipeline_current'] else 0)}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(metrics['pipeline_current']/25_000_000*100, 100)}%"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📈</div>
            <div class="metric-label">3-Month Pipeline</div>
            <div class="metric-value">{format_currency(metrics['pipeline_3month'])}</div>
            <div class="metric-subtitle">Next 90 days forecast</div>
            <div class="progress-container">
                <div class="progress-label">
                    <span>Pipeline Health</span>
                    <span>{format_percentage(metrics['pipeline_3month']/100_000_000*100 if metrics['pipeline_3month'] else 0)}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(metrics['pipeline_3month']/100_000_000*100, 100)}%"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-label">FY2025 Pipeline</div>
            <div class="metric-value">{format_currency(metrics['pipeline_fy'])}</div>
            <div class="metric-subtitle">Through March 31, 2025</div>
            <div class="progress-container">
                <div class="progress-label">
                    <span>YTD Performance</span>
                    <span>{format_percentage(metrics['pipeline_fy']/150_000_000*100 if metrics['pipeline_fy'] else 0)}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(metrics['pipeline_fy']/150_000_000*100, 100)}%"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🏆</div>
            <div class="metric-label">Average Deal Size</div>
            <div class="metric-value">{format_currency(metrics['avg_deal_size'])}</div>
            <div class="metric-subtitle">Avg: {int(metrics['avg_days_to_close'])} days to close</div>
            <div class="metric-change positive" style="margin-top: 12px;">
                Top Source: {metrics['top_lead_source']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Sales Performance Section
    st.markdown('<div class="section-header">Sales Performance Analysis</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Sales by Type Grid
        subcol1, subcol2, subcol3 = st.columns(3)
        
        with subcol1:
            project_pct = (metrics['project_mtd'] / metrics['project_forecast'] * 100) if metrics['project_forecast'] > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🏗️ Project Sales</div>
                <div class="metric-value">{format_currency(metrics['project_forecast'])}</div>
                <div class="metric-subtitle">Monthly Target</div>
                <div class="metric-change {'positive' if project_pct >= 80 else 'negative'}" style="margin-top: 12px;">
                    MTD: {format_currency(metrics['project_mtd'])}
                </div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(project_pct, 100)}%; background: {'#10b981' if project_pct >= 80 else '#ef4444'}"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with subcol2:
            trans_pct = (metrics['trans_mtd'] / metrics['trans_forecast'] * 100) if metrics['trans_forecast'] > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">💱 Transactional</div>
                <div class="metric-value">{format_currency(metrics['trans_forecast'])}</div>
                <div class="metric-subtitle">Monthly Target</div>
                <div class="metric-change {'positive' if trans_pct >= 80 else 'negative'}" style="margin-top: 12px;">
                    MTD: {format_currency(metrics['trans_mtd'])}
                </div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(trans_pct, 100)}%; background: {'#10b981' if trans_pct >= 80 else '#f59e0b'}"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with subcol3:
            service_pct = (metrics['service_mtd'] / metrics['service_forecast'] * 100) if metrics['service_forecast'] > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🔧 Service</div>
                <div class="metric-value">{format_currency(metrics['service_forecast'])}</div>
                <div class="metric-subtitle">Monthly Target</div>
                <div class="metric-change {'positive' if service_pct >= 80 else 'negative'}" style="margin-top: 12px;">
                    MTD: {format_currency(metrics['service_mtd'])}
                </div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {min(service_pct, 100)}%; background: {'#10b981' if service_pct >= 80 else '#ef4444'}"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Opportunity Type Distribution
        type_chart = create_type_distribution(df)
        if type_chart:
            st.plotly_chart(type_chart, use_container_width=True, key="type_dist")
    
    # Visual Analytics Section
    st.markdown('<div class="section-header">Visual Analytics</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # Enhanced Gauge Charts
        gauge1 = create_enhanced_gauge(
            metrics['pipeline_current'], 
            25_000_000, 
            "Current Month Pipeline",
            target=20_000_000
        )
        st.plotly_chart(gauge1, use_container_width=True, key="gauge1")
    
    with col2:
        # Pipeline Trend
        trend_chart = create_pipeline_trend(df)
        if trend_chart:
            st.plotly_chart(trend_chart, use_container_width=True, key="trend")
    
    with col3:
        # Quick Stats
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Quick Stats</div>
            <div style="margin-top: 16px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="color: #64748b; font-size: 13px;">Open Opps</span>
                    <span style="font-weight: 600; font-size: 14px;">{metrics['total_opps']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="color: #64748b; font-size: 13px;">Win Rate</span>
                    <span style="font-weight: 600; font-size: 14px; color: #10b981;">{format_percentage(metrics['win_rate'])}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="color: #64748b; font-size: 13px;">Avg Deal</span>
                    <span style="font-weight: 600; font-size: 14px;">{format_currency(metrics['avg_deal_size'])}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #64748b; font-size: 13px;">Avg Close</span>
                    <span style="font-weight: 600; font-size: 14px;">{int(metrics['avg_days_to_close'])}d</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Team Performance Section
    st.markdown('<div class="section-header">Team Performance</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Owner Performance Chart
        owner_chart = create_owner_performance(df)
        if owner_chart:
            st.plotly_chart(owner_chart, use_container_width=True, key="owner_perf")
    
    with col2:
        # Sales Funnel
        funnel_chart = create_sales_funnel(df)
        if funnel_chart:
            st.plotly_chart(funnel_chart, use_container_width=True, key="funnel")
    
    # Footer with auto-refresh info
    st.markdown(f"""
    <div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 12px; margin-top: 40px;">
        Last updated: {st.session_state.last_refresh.strftime('%B %d, %Y at %I:%M %p')} 
        • Auto-refresh: Every 10 minutes 
        • Refresh count: {st.session_state.refresh_count}
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh JavaScript
    st.markdown("""
    <script>
        setTimeout(function() {
            window.location.reload();
        }, 600000);  // 10 minutes
    </script>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()