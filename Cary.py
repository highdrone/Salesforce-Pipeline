import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import time
import warnings
import urllib3
import os
from simple_salesforce import Salesforce

# Suppress urllib3 warnings
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")
urllib3.disable_warnings()
os.environ['PYTHONWARNINGS'] = "ignore:urllib3"

# Page configuration for 1080p monitor
st.set_page_config(
    page_title="Cary Forecasts MTD",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS for modern, compact design
st.markdown("""
<style>
    /* Reset and base styles */
    .main {
        padding: 0.5rem 1rem;
        max-width: 1920px;
        margin: 0 auto;
    }
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        max-width: 100%;
    }
    .stApp {
        background: #f0f2f5;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Header styles */
    .dashboard-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem 1.5rem;
        margin: -0.5rem -1rem 1rem -1rem;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .header-title {
        font-size: 1.75rem;
        font-weight: 600;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        font-size: 0.875rem;
        opacity: 0.9;
        margin: 0;
    }
    .refresh-info {
        text-align: right;
        font-size: 0.875rem;
        opacity: 0.9;
    }
    
    /* Card styles */
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    
    /* Gauge styles */
    .gauge-container {
        background: white;
        border-radius: 8px;
        padding: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        height: 260px;
        overflow: hidden;
        position: relative;
    }
    
    /* Chart containers */
    .chart-container {
        background: white;
        border-radius: 8px;
        padding: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        height: 100%;
        overflow: hidden;
        position: relative;
    }
    
    /* Metric styles */
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        margin: 0.25rem 0;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #666;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }
    .metric-comparison {
        display: flex;
        gap: 1.5rem;
        align-items: center;
        justify-content: space-around;
        padding: 0.5rem;
    }
    .metric-item {
        text-align: center;
        flex: 1;
    }
    
    /* Section titles */
    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }
    
    /* Color indicators */
    .positive { color: #10b981; }
    .negative { color: #ef4444; }
    .warning { color: #f59e0b; }
    .neutral { color: #6b7280; }
    
    /* Responsive grid adjustments */
    @media (max-width: 1920px) {
        .metric-value { font-size: 1.75rem; }
        .section-title { font-size: 1.125rem; }
    }
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .css-1rs6os {visibility: hidden;}
    .css-17ziqus {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    /* Compact spacing */
    .stPlotlyChart {
        height: auto !important;
    }
    .element-container {
        margin-bottom: 0.5rem !important;
    }
    div[data-testid="column"] {
        padding: 0 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.datetime.now()
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True

# Auto-refresh logic
def check_refresh():
    current_time = datetime.datetime.now()
    time_diff = (current_time - st.session_state.last_refresh).total_seconds()
    
    # Refresh every 10 minutes (600 seconds)
    if time_diff >= 600 and st.session_state.auto_refresh:
        st.session_state.last_refresh = current_time
        if 'salesforce_data' in st.session_state:
            del st.session_state['salesforce_data']
        st.rerun()

# Fetch opportunities function
def fetch_opportunities(sf):
    try:
        query = """
        SELECT 
            Id, Name, StageName, Amount, CloseDate, CreatedDate, 
            Probability, Owner.Name, AccountId, Account.Name, 
            FiscalYear, FiscalQuarter, Type, IsClosed, IsWon,
            Region__c, Branch__c, Weighted_AVG__c, Gross_Profit__c,
            Owner_Name__c, Account_Name__c
        FROM Opportunity
        WHERE IsDeleted = false
        AND Branch__c = '200'
        """
        
        all_records = []
        query_result = sf.query(query)
        all_records.extend(query_result.get('records', []))
        
        while query_result.get('done') is False:
            query_result = sf.query_more(query_result.get('nextRecordsUrl'), True)
            all_records.extend(query_result.get('records', []))
        
        if not all_records:
            return pd.DataFrame()
            
        processed_records = []
        for record in all_records:
            if record and 'attributes' in record:
                record_dict = {
                    'Opportunity ID': record.get('Id'),
                    'Opportunity Name': record.get('Name'),
                    'Stage': record.get('StageName'),
                    'Amount': record.get('Amount', 0),
                    'Close Date': record.get('CloseDate'),
                    'Created Date': record.get('CreatedDate'),
                    'Probability (%)': record.get('Probability', 0),
                    'Type': record.get('Type'),
                    'Is Closed': record.get('IsClosed'),
                    'Is Won': record.get('IsWon'),
                    'Branch': record.get('Branch__c'),
                    'Weighted AVG': record.get('Weighted_AVG__c'),
                    'Gross Profit': record.get('Gross_Profit__c'),
                }
                
                if record.get('Owner') and isinstance(record.get('Owner'), dict):
                    record_dict['Opportunity Owner'] = record.get('Owner', {}).get('Name')
                else:
                    record_dict['Opportunity Owner'] = record.get('Owner_Name__c')
                    
                if record.get('Account') and isinstance(record.get('Account'), dict):
                    record_dict['Account Name'] = record.get('Account', {}).get('Name')
                else:
                    record_dict['Account Name'] = record.get('Account_Name__c')
                
                processed_records.append(record_dict)
        
        df = pd.DataFrame(processed_records)
        
        # Convert dates
        date_fields = ['Close Date', 'Created Date']
        for date_field in date_fields:
            if date_field in df.columns:
                df[date_field] = pd.to_datetime(df[date_field], errors='coerce')
        
        # Calculate weighted average if needed
        if 'Amount' in df.columns and 'Probability (%)' in df.columns:
            df['Weighted AVG'] = df['Amount'] * df['Probability (%)'] / 100
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching opportunities: {str(e)}")
        return pd.DataFrame()

# Compact gauge chart
def create_compact_gauge(value, max_val, title):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [0, max_val], 'tickwidth': 1},
            'bar': {'color': "#2563eb", 'thickness': 0.3},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "#e5e7eb",
            'steps': [
                {'range': [0, max_val*0.33], 'color': '#fee2e2'},
                {'range': [max_val*0.33, max_val*0.66], 'color': '#fef3c7'},
                {'range': [max_val*0.66, max_val], 'color': '#d1fae5'}
            ],
            'threshold': {
                'line': {'color': "#1f2937", 'width': 2},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'family': '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif'}
    )
    
    return fig

# Compact bar chart
def create_owner_chart(df):
    closed_won = df[df['Stage'] == 'Closed Won'].copy()
    
    if closed_won.empty:
        return None
    
    owner_sales = closed_won.groupby('Opportunity Owner')['Amount'].sum().reset_index()
    owner_sales = owner_sales.sort_values('Amount', ascending=True).tail(10)  # Top 10 only
    
    fig = px.bar(
        owner_sales,
        x='Amount',
        y='Opportunity Owner',
        orientation='h',
        color='Amount',
        color_continuous_scale='Blues',
        text='Amount'
    )
    
    fig.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title='',
        yaxis_title='',
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=False),
        font={'size': 11}
    )
    
    fig.update_traces(
        texttemplate='$%{text:,.0f}',
        textposition='auto',
        textfont_size=9
    )
    
    return fig

# Calculate metrics
def calculate_dashboard_metrics(df):
    metrics = {}
    
    current_date = pd.Timestamp.now()
    current_month = current_date.month
    current_year = current_date.year
    
    # Pipeline metrics
    current_month_opps = df[
        (df['Close Date'].dt.month == current_month) & 
        (df['Close Date'].dt.year == current_year) &
        (df['Stage'] != 'Closed Won')
    ]
    metrics['pipeline_current_month'] = current_month_opps['Amount'].sum()
    
    next_2_months = current_date + pd.DateOffset(months=2)
    pipeline_3_months = df[
        (df['Close Date'] >= current_date) &
        (df['Close Date'] <= next_2_months) &
        (df['Stage'] != 'Closed Won')
    ]
    metrics['pipeline_3_months'] = pipeline_3_months['Amount'].sum()
    
    fy_end = pd.Timestamp(2025, 6, 30)
    pipeline_fy = df[
        (df['Close Date'] >= current_date) &
        (df['Close Date'] <= fy_end) &
        (df['Stage'] != 'Closed Won')
    ]
    metrics['pipeline_fy'] = pipeline_fy['Amount'].sum()
    
    # Sales metrics by type
    for sale_type in ['Project', 'Transactional', 'Service']:
        # Forecast
        forecast = df[
            (df['Type'] == sale_type) &
            (df['Close Date'] >= current_date)
        ]
        metrics[f'{sale_type.lower()}_forecast'] = forecast['Amount'].sum()
        
        # MTD
        mtd = df[
            (df['Type'] == sale_type) &
            (df['Close Date'].dt.month == current_month) &
            (df['Close Date'].dt.year == current_year) &
            (df['Stage'] == 'Closed Won')
        ]
        metrics[f'{sale_type.lower()}_mtd'] = mtd['Amount'].sum()
    
    return metrics

# Main dashboard
def create_dashboard(df, metrics):
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
        <div class="dashboard-header">
            <div class="header-left">
                <div>
                    <h1 class="header-title">Cary Forecasts MTD</h1>
                    <p class="header-subtitle">{datetime.datetime.now().strftime('%B %d, %Y, %I:%M %p')} | Auto-refresh: ON</p>
                </div>
            </div>
            <div class="refresh-info">
                <div>Last refresh: {st.session_state.last_refresh.strftime('%I:%M %p')}</div>
                <div>Next refresh: {(st.session_state.last_refresh + datetime.timedelta(minutes=10)).strftime('%I:%M %p')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Pipeline Row
    st.markdown('<div class="section-title">Pipeline Overview</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container():
            st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
            fig1 = create_compact_gauge(
                metrics['pipeline_current_month'], 
                25000000, 
                "Current Month"
            )
            st.plotly_chart(fig1, use_container_width=True, key="gauge1")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        with st.container():
            st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
            fig2 = create_compact_gauge(
                metrics['pipeline_3_months'], 
                100000000, 
                "3-Month Pipeline"
            )
            st.plotly_chart(fig2, use_container_width=True, key="gauge2")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">FY2025 Pipeline</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">${metrics["pipeline_fy"]/1000000:.1f}M</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Through June 30</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Total Opportunities</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{len(df)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Active Records</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Sales Metrics and Chart Row
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Sales Performance by Type</div>', unsafe_allow_html=True)
        
        # Create three sub-columns for metrics
        subcol1, subcol2, subcol3 = st.columns(3)
        
        with subcol1:
            st.markdown('<div class="metric-comparison">', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="metric-item">
                    <div class="metric-label">Project Forecast</div>
                    <div class="metric-value">${metrics['project_forecast']/1000000:.1f}M</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Project MTD</div>
                    <div class="metric-value negative">${metrics['project_mtd']/1000000:.1f}M</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with subcol2:
            st.markdown('<div class="metric-comparison">', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="metric-item">
                    <div class="metric-label">Trans. Forecast</div>
                    <div class="metric-value">${metrics['transactional_forecast']/1000:.0f}K</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Trans. MTD</div>
                    <div class="metric-value warning">${metrics['transactional_mtd']/1000:.0f}K</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with subcol3:
            st.markdown('<div class="metric-comparison">', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="metric-item">
                    <div class="metric-label">Service Forecast</div>
                    <div class="metric-value">${metrics['service_forecast']/1000000:.1f}M</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Service MTD</div>
                    <div class="metric-value negative">${metrics['service_mtd']/1000000:.1f}M</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Top Sales by Owner</div>', unsafe_allow_html=True)
        owner_chart = create_owner_chart(df)
        if owner_chart:
            st.plotly_chart(owner_chart, use_container_width=True, key="owner_chart")
        else:
            st.info("No closed won opportunities")
        st.markdown('</div>', unsafe_allow_html=True)

# Main app
def main():
    # Check for auto-refresh
    check_refresh()
    
    # Salesforce credentials
    sf_credentials = {
        'username': "william.evans@avidex.com",
        'password': "D_w?ygrM6g9rp",
        'security_token': "V7W9o94PW3TVtBsqaS5zkNKS",
        'domain': 'login'
    }
    
    try:
        # Connect and fetch data
        if 'salesforce_data' not in st.session_state:
            with st.spinner("Connecting to Salesforce..."):
                sf = Salesforce(
                    username=sf_credentials['username'],
                    password=sf_credentials['password'],
                    security_token=sf_credentials['security_token'],
                    domain=sf_credentials['domain']
                )
                
                df = fetch_opportunities(sf)
                
                if not df.empty:
                    st.session_state['salesforce_data'] = df
                    st.session_state.last_refresh = datetime.datetime.now()
                else:
                    st.error("No Cary Branch opportunities found.")
                    return
        else:
            df = st.session_state['salesforce_data']
        
        # Calculate metrics and create dashboard
        metrics = calculate_dashboard_metrics(df)
        create_dashboard(df, metrics)
        
        # Add auto-refresh JavaScript
        st.markdown("""
        <script>
            // Auto-refresh every 10 minutes
            setTimeout(function(){
                window.location.reload();
            }, 600000);
        </script>
        """, unsafe_allow_html=True)
                    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("Please check your Salesforce connection.")

if __name__ == "__main__":
    main()