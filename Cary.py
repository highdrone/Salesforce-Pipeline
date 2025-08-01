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

# Suppress warnings
warnings.filterwarnings("ignore")
urllib3.disable_warnings()

# Page config
st.set_page_config(
    page_title="Cary Forecasts MTD",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Google-style CSS
st.markdown("""
<style>
    /* Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@300;400;500;700&display=swap');
    
    /* Reset */
    .main { padding: 0; }
    .block-container { padding: 1rem; max-width: 100%; }
    
         /* Avidex Brand Colors */
     :root {
         --avidex-blue: #1e40af;
         --avidex-dark-blue: #1e3a8a;
         --avidex-light-blue: #3b82f6;
         --primary-green: #059669;
         --primary-orange: #ea580c;
         --primary-red: #dc2626;
         --primary-yellow: #d97706;
         --accent-teal: #0d9488;
         --accent-pink: #db2777;
         --light-grey: #f1f5f9;
         --border-color: #e2e8f0;
         --text-dark: #1e293b;
         --text-muted: #64748b;
     }
    
    /* Typography */
    .stApp {
        font-family: 'Roboto', 'Google Sans', Arial, sans-serif;
        background-color: var(--light-grey);
        color: #202124;
    }
    
         /* Header */
     .google-header {
         background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
         color: white;
         padding: 12px 20px;
         margin: -1rem -1rem 1rem -1rem;
         box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
     }
    
    .header-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .logo-title {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    
    .google-logo {
        width: 32px;
        height: 32px;
    }
    
         h1 {
         font-family: 'Google Sans', 'Roboto', sans-serif;
         font-size: 20px;
         font-weight: 500;
         color: white;
         margin: 0;
         line-height: 1.2;
     }
     
     .subtitle {
         font-size: 12px;
         color: rgba(255,255,255,0.9);
         margin: 2px 0 0 48px;
     }
    
         .refresh-badge {
         background: rgba(255,255,255,0.2);
         color: white;
         padding: 4px 12px;
         border-radius: 20px;
         font-size: 11px;
         font-weight: 500;
         border: 1px solid rgba(255,255,255,0.3);
     }
    
         /* Cards */
     .metric-card {
         background: white;
         border-radius: 12px;
         padding: 16px;
         border: 1px solid var(--border-color);
         height: 100%;
         transition: all 0.3s ease;
         box-shadow: 0 1px 3px rgba(0,0,0,0.1);
     }
     
     .metric-card:hover {
         transform: translateY(-2px);
         box-shadow: 0 8px 25px rgba(0,0,0,0.15);
     }
    
    /* Metrics */
         .metric-label {
         font-size: 11px;
         font-weight: 600;
         color: var(--text-muted);
         text-transform: uppercase;
         letter-spacing: 0.5px;
         margin-bottom: 6px;
     }
     
     .metric-value {
         font-size: 28px;
         font-weight: 600;
         color: var(--text-dark);
         line-height: 1;
         font-family: 'Google Sans', 'Roboto', sans-serif;
     }
    
         .metric-subtitle {
         font-size: 12px;
         color: var(--text-muted);
         margin-top: 2px;
     }
     
     /* Status colors */
     .status-positive { color: var(--primary-green); }
     .status-negative { color: var(--primary-red); }
     .status-warning { color: var(--primary-orange); }
    
         /* Section headers */
     .section-header {
         font-size: 18px;
         font-weight: 600;
         color: var(--text-dark);
         margin: 16px 0 12px 0;
         font-family: 'Google Sans', 'Roboto', sans-serif;
         text-align: center;
         padding: 8px 0;
         border-bottom: 2px solid var(--avidex-blue);
     }
    
    /* Charts */
    .chart-container {
        background: white;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid var(--border-color);
    }
    
    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    
    /* Responsive */
    @media (max-width: 1920px) {
        .metric-value { font-size: 28px; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.datetime.now()
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0

# Auto-refresh function
def auto_refresh():
    time_since_refresh = (datetime.datetime.now() - st.session_state.last_refresh).total_seconds()
    if time_since_refresh > 600:  # 10 minutes
        st.session_state.refresh_count += 1
        st.session_state.last_refresh = datetime.datetime.now()
        if 'salesforce_data' in st.session_state:
            del st.session_state['salesforce_data']
        st.rerun()

# Fetch data function
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_opportunities():
    """Fetch opportunities from Salesforce"""
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
            Owner_Name__c, ForecastCategory
        FROM Opportunity
        WHERE IsDeleted = false
        AND Branch__c = '700'
        LIMIT 10000
        """
        
        result = sf.query_all(query)
        records = result['records']
        
        # Process records
        data = []
        for record in records:
            data.append({
                'Stage': record.get('StageName'),
                'Amount': float(record.get('Amount', 0) or 0),
                'Close Date': record.get('CloseDate'),
                'Probability': float(record.get('Probability', 0) or 0),
                'Type': record.get('Type', 'Unknown'),
                'ForecastCategory': record.get('ForecastCategory', 'Unknown'),
                'Owner': record.get('Owner', {}).get('Name') if record.get('Owner') else record.get('Owner_Name__c', 'Unknown')
            })
        
        df = pd.DataFrame(data)
        df['Close Date'] = pd.to_datetime(df['Close Date'])
        return df
        
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

# Calculate metrics
def calculate_metrics(df):
    """Calculate dashboard metrics"""
    if df.empty:
        return {
            'pipeline_current': 0,
            'pipeline_3month': 0,
            'pipeline_fy': 0,
            'total_opps': 0,
            'project_forecast': 0,
            'project_mtd': 0,
            'trans_forecast': 0,
            'trans_mtd': 0,
            'service_forecast': 0,
            'service_mtd': 0
        }
    
    now = pd.Timestamp.now()
    current_month = now.month
    current_year = now.year
    
    # Pipeline metrics - matching Salesforce filters
    # Apply ForecastCategory filter: "equals Best Case, Closed, Commit, Pipeline"
    valid_forecast_categories = ['BestCase', 'Closed', 'Commit', 'Pipeline']
    filtered_opportunities = df[
        df['ForecastCategory'].isin(valid_forecast_categories)
    ]
    
    # Current Month Pipeline - all opportunities active in current month
    current_month_pipeline = filtered_opportunities[
        (filtered_opportunities['Close Date'].dt.month == current_month) & 
        (filtered_opportunities['Close Date'].dt.year == current_year)
    ]['Amount'].sum()
    
    # MTD Pipeline - opportunities closing from 1st of current month to today
    # Filter out invalid dates first
    valid_dates = filtered_opportunities[
        (filtered_opportunities['Close Date'] >= pd.Timestamp('2020-01-01')) &
        (filtered_opportunities['Close Date'] <= pd.Timestamp('2030-12-31'))
    ]
    
    # Get current date and first day of current month
    current_date = pd.Timestamp.now()
    mtd_start = current_date.replace(day=1)
    
    # MTD Pipeline: opportunities with close date from 1st of current month to today
    mtd_pipeline = valid_dates[
        (valid_dates['Close Date'] >= mtd_start) & 
        (valid_dates['Close Date'] <= current_date)
    ]['Amount'].sum()
    
    # If MTD is 0, use current month pipeline instead
    if mtd_pipeline == 0:
        mtd_pipeline = current_month_pipeline
    
    # 3-Month Pipeline - sum of current month + next 2 months
    three_month_pipeline = valid_dates[
        (valid_dates['Close Date'] >= now) & 
        (valid_dates['Close Date'] <= now + pd.DateOffset(months=2))
    ]['Amount'].sum()
    
    # FY Pipeline - through March 31, 2025
    fy_pipeline = valid_dates[
        (valid_dates['Close Date'] >= pd.Timestamp(2024, 4, 1)) & 
        (valid_dates['Close Date'] <= pd.Timestamp(2025, 3, 31))
    ]['Amount'].sum()
    
    # Sales by type - using same close date filtering as pipeline
    # Use current month pipeline filtering (all opportunities in current month)
    sales_by_type = filtered_opportunities[
        (filtered_opportunities['Close Date'].dt.month == current_month) & 
        (filtered_opportunities['Close Date'].dt.year == current_year)
    ]
    
    # Total Opportunities - all open opportunities for Branch 700
    # Filter out closed opportunities (Closed Won, Closed Lost)
    open_opportunities = df[~df['Stage'].isin(['Closed Won', 'Closed Lost'])]
    total_open_opps = len(open_opportunities)
    
    metrics = {
        'pipeline_current': current_month_pipeline,
        'pipeline_mtd': mtd_pipeline,
        'pipeline_3month': three_month_pipeline,
        'pipeline_fy': fy_pipeline,
        'total_opps': total_open_opps,
        'project_forecast': filtered_opportunities[filtered_opportunities['Type'] == 'System']['Amount'].sum(),
        'project_mtd': sales_by_type[sales_by_type['Type'] == 'System']['Amount'].sum(),
        'trans_forecast': filtered_opportunities[filtered_opportunities['Type'] == 'Transactional']['Amount'].sum(),
        'trans_mtd': sales_by_type[sales_by_type['Type'] == 'Transactional']['Amount'].sum(),
        'service_forecast': filtered_opportunities[filtered_opportunities['Type'] == 'Service']['Amount'].sum(),
        'service_mtd': sales_by_type[sales_by_type['Type'] == 'Service']['Amount'].sum()
    }
    
    return metrics

# Create gauge chart
def create_gauge(value, max_value, title):
    """Create a simple gauge chart"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 14}},
        number = {'font': {'size': 28}},
                 gauge = {
             'axis': {'range': [0, max_value]},
             'bar': {'color': "#1e40af"},
             'steps': [
                 {'range': [0, max_value * 0.4], 'color': "#dbeafe"},
                 {'range': [max_value * 0.4, max_value * 0.7], 'color': "#3b82f6"},
                 {'range': [max_value * 0.7, max_value], 'color': "#1e3a8a"}
             ],
             'threshold': {
                 'line': {'color': "#dc2626", 'width': 4},
                 'thickness': 0.75,
                 'value': value * 0.9
             }
         }
    ))
    
    fig.update_layout(
        height=180,
        margin=dict(l=15, r=15, t=30, b=15),
        paper_bgcolor='white',
        font={'family': 'Roboto, sans-serif'}
    )
    
    return fig

# Create bar chart
def create_bar_chart(df):
    """Create owner performance bar chart"""
    # Filter by Forecast Category and use same close date filtering as pipeline
    valid_forecast_categories = ['BestCase', 'Closed', 'Commit', 'Pipeline']
    now = pd.Timestamp.now()
    current_month = now.month
    current_year = now.year
    
    # Filter out invalid dates first
    valid_dates_df = df[
        (df['Close Date'] >= pd.Timestamp('2020-01-01')) &
        (df['Close Date'] <= pd.Timestamp('2030-12-31'))
    ]
    
    # Use same filtering as pipeline - current month opportunities
    filtered_df = valid_dates_df[
        (valid_dates_df['ForecastCategory'].isin(valid_forecast_categories)) &
        (valid_dates_df['Close Date'].dt.month == current_month) &
        (valid_dates_df['Close Date'].dt.year == current_year)
    ]
    
    if filtered_df.empty:
        return None
    
    owner_sales = filtered_df.groupby('Owner')['Amount'].sum().sort_values(ascending=True).tail(8)
    
    fig = px.bar(
        x=owner_sales.values,
        y=owner_sales.index,
        orientation='h',
        color_discrete_sequence=['#1e40af']
    )
    
    fig.update_layout(
        height=220,
        margin=dict(l=8, r=8, t=8, b=8),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font={'family': 'Roboto, sans-serif', 'size': 11},
        xaxis={'tickformat': ',.0f', 'showgrid': True, 'gridcolor': '#f0f0f0'},
        yaxis={'showgrid': False}
    )
    
    fig.update_traces(
        text=[f'${x:,.0f}' for x in owner_sales.values],
        textposition='outside'
    )
    
    return fig

# Format currency
def format_currency(value):
    """Format currency values"""
    if value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:.0f}"

# Main app
def main():
    # Check for auto-refresh
    auto_refresh()
    
    # Header
    st.markdown(f"""
    <div class="google-header">
        <div class="header-content">
            <div>
                <div class="logo-title">
                    <h1>Cary Forecasts MTD</h1>
                </div>
                <div class="subtitle">Last updated: {st.session_state.last_refresh.strftime('%B %d, %Y at %I:%M %p')}</div>
            </div>
            <div class="refresh-badge">Auto-refresh ON</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch data
    with st.spinner('Loading data...'):
        df = fetch_opportunities()
        
        metrics = calculate_metrics(df)
    
    # Pipeline Overview
    st.markdown('<div class="section-header">Pipeline Overview</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        gauge = create_gauge(metrics['pipeline_current'], 25_000_000, "Pipeline - Current Month")
        st.plotly_chart(gauge, use_container_width=True, key="gauge1")
    
    with col2:
        gauge = create_gauge(metrics['pipeline_3month'], 100_000_000, "Pipeline - Current Month + Next 2 Months")
        st.plotly_chart(gauge, use_container_width=True, key="gauge2")
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">FY2025 Pipeline</div>
            <div class="metric-value">{format_currency(metrics['pipeline_fy'])}</div>
            <div class="metric-subtitle">Through March 31</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Opportunities</div>
            <div class="metric-value">{metrics['total_opps']:,}</div>
            <div class="metric-subtitle">Active records</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Sales Performance
    st.markdown('<div class="section-header">Sales Performance</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Sales metrics grid
        subcol1, subcol2, subcol3 = st.columns(3)
        
        with subcol1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Project</div>
                <div class="metric-value">{format_currency(metrics['project_forecast'])}</div>
                <div class="metric-subtitle">Forecast</div>
                <div class="metric-value status-negative" style="font-size: 24px; margin-top: 16px;">
                    {format_currency(metrics['project_mtd'])}
                </div>
                <div class="metric-subtitle">MTD Actual</div>
            </div>
            """, unsafe_allow_html=True)
        
        with subcol2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Transactional</div>
                <div class="metric-value">{format_currency(metrics['trans_forecast'])}</div>
                <div class="metric-subtitle">Forecast</div>
                <div class="metric-value status-warning" style="font-size: 24px; margin-top: 16px;">
                    {format_currency(metrics['trans_mtd'])}
                </div>
                <div class="metric-subtitle">MTD Actual</div>
            </div>
            """, unsafe_allow_html=True)
        
        with subcol3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Service</div>
                <div class="metric-value">{format_currency(metrics['service_forecast'])}</div>
                <div class="metric-subtitle">Forecast</div>
                <div class="metric-value status-negative" style="font-size: 24px; margin-top: 16px;">
                    {format_currency(metrics['service_mtd'])}
                </div>
                <div class="metric-subtitle">MTD Actual</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div style="font-size: 14px; font-weight: 500; margin-bottom: 12px;">Top Sales by Owner</div>', 
                   unsafe_allow_html=True)
        
        bar_chart = create_bar_chart(df)
        if bar_chart:
            st.plotly_chart(bar_chart, use_container_width=True, key="bar_chart")
        else:
            st.info("No closed won opportunities to display")
    
    # Auto-refresh JavaScript
    st.markdown("""
    <script>
        setTimeout(function() {
            window.location.reload();
        }, 600000);  // 10 minutes
    </script>
    """, unsafe_allow_html=True)
    
    # Show opportunities table at the bottom
    st.markdown('<div class="section-header">Opportunities Data</div>', unsafe_allow_html=True)
    
    # Get the filtered opportunities used in calculations
    valid_forecast_categories = ['BestCase', 'Closed', 'Commit', 'Pipeline']
    valid_dates_df = df[
        (df['Close Date'] >= pd.Timestamp('2025-08-01')) &
        (df['Close Date'] <= pd.Timestamp('2025-08-31'))
    ]
    
    filtered_opportunities = valid_dates_df[
        valid_dates_df['ForecastCategory'].isin(valid_forecast_categories)
    ]
    
    # Show table of opportunities with important columns
    if not filtered_opportunities.empty:
        # Select important columns and format them
        display_df = filtered_opportunities[['Owner', 'Type', 'ForecastCategory', 'Close Date', 'Amount', 'Probability']].copy()
        display_df['Amount'] = display_df['Amount'].apply(lambda x: f"${x:,.0f}")
        display_df['Close Date'] = display_df['Close Date'].dt.strftime('%Y-%m-%d')
        display_df['Probability'] = display_df['Probability'].apply(lambda x: f"{x:.0f}%")
        
        # Rename columns for better display
        display_df = display_df.rename(columns={
            'Owner': 'Owner',
            'Type': 'Type', 
            'ForecastCategory': 'Forecast Category',
            'Close Date': 'Close Date',
            'Amount': 'Amount',
            'Probability': 'Probability (%)'
        })
        
        st.write(f"**Total Opportunities:** {len(filtered_opportunities)}")
        st.dataframe(display_df, use_container_width=True)
        
        # Show summary statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Pipeline Value", f"${filtered_opportunities['Amount'].sum():,.0f}")
        
        with col2:
            avg_prob = filtered_opportunities['Probability'].mean()
            st.metric("Average Probability", f"{avg_prob:.0f}%")
        
        with col3:
            avg_amount = filtered_opportunities['Amount'].mean()
            st.metric("Average Deal Size", f"${avg_amount:,.0f}")
    else:
        st.write("No opportunities match the filtering criteria.")
    


if __name__ == "__main__":
    main()