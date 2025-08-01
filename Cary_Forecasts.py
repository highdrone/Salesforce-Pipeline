import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
import datetime
import time
import warnings
import urllib3
import os

# Suppress urllib3 warnings about LibreSSL on macOS
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")
# Additional suppression for NotOpenSSLWarning
urllib3.disable_warnings()

# For Streamlit Cloud, we can also try setting the environment variable
os.environ['PYTHONWARNINGS'] = "ignore:urllib3"

# Import Salesforce after warning suppression
from simple_salesforce import Salesforce


# Page configuration for 1080p monitor
st.set_page_config(
    page_title="Cary Forecasts MTD",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add custom CSS for Google-inspired dashboard styling
st.markdown("""
<style>
    .main {
        padding: 0;
        margin: 0;
    }
    .stApp {
        background: #f8f9fa;
        min-height: 100vh;
        font-family: 'Google Sans', 'Roboto', Arial, sans-serif;
    }
    .dashboard-header {
        background: #ffffff;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .metric-card {
        background: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 1rem;
        border: 1px solid #e8eaed;
    }
    .gauge-container {
        text-align: center;
        padding: 1rem;
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        border: 1px solid #e8eaed;
        overflow: hidden;
        position: relative;
    }
    .owner-chart {
        background: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        border: 1px solid #e8eaed;
        overflow: hidden;
        position: relative;
    }
    .sales-metrics {
        background: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        border: 1px solid #e8eaed;
        overflow: hidden;
        position: relative;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 500;
        color: #202124;
        text-align: center;
        margin: 0.5rem 0;
        font-family: 'Google Sans', 'Roboto', Arial, sans-serif;
    }
    .metric-label {
        font-size: 1rem;
        color: #5f6368;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .section-title {
        font-size: 1.5rem;
        font-weight: 500;
        color: #202124;
        margin-bottom: 1rem;
        text-align: center;
        font-family: 'Google Sans', 'Roboto', Arial, sans-serif;
    }
    .logo {
        width: 48px;
        height: 48px;
    }
    .header-title {
        font-size: 2rem;
        font-weight: 500;
        color: #202124;
        margin: 0;
        font-family: 'Google Sans', 'Roboto', Arial, sans-serif;
    }
    .header-subtitle {
        font-size: 0.875rem;
        color: #5f6368;
        margin: 0;
        font-weight: 400;
    }
    .pipeline-section {
        margin-bottom: 2rem;
    }
    .sales-section {
        margin-bottom: 2rem;
    }
    .chart-container {
        height: 400px;
    }
    /* Google Material Design colors */
    .metric-positive {
        color: #34a853;
    }
    .metric-negative {
        color: #ea4335;
    }
    .metric-warning {
        color: #fbbc04;
    }
    /* Hide scrollbars */
    ::-webkit-scrollbar {
        display: none;
    }
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Main function to fetch opportunities with enhanced data
def fetch_opportunities(sf):
    try:
        status_placeholder = st.empty()
        
        # Enhanced query to get all necessary fields for the dashboard
        query = """
        SELECT 
            Id, Name, StageName, Amount, CloseDate, CreatedDate, 
            Probability, Owner.Name, AccountId, Account.Name, 
            FiscalYear, FiscalQuarter, Type, IsClosed, IsWon,
            Region__c, Branch__c, Weighted_AVG__c, Gross_Profit__c,
            Gross_Profit_Percentage__c, Project_Number__c, 
            Quote_Number__c, Job_Number__c, Project_Start_Date__c, 
            Estimated_Project_End_Date__c, Bid_Due_Date__c, 
            RFI_Due_Date__c, Job_Walk_Date__c,
            Opportunity_Created_For__c, Is_this_a_Renewal__c,
            Owner_Name__c, Account_Name__c, Owner_Branch__c, 
            Owner_Region__c
        FROM Opportunity
        WHERE IsDeleted = false
        """
        
        status_placeholder.info("Fetching opportunities from Salesforce...")
        
        # Handle pagination for large datasets
        all_records = []
        query_result = sf.query(query)
        all_records.extend(query_result.get('records', []))
        
        total_size = query_result.get('totalSize', 0)
        status_placeholder.info(f"Found {total_size} total opportunities, retrieving all records...")
        
        # Continue querying if there are more records
        while query_result.get('done') is False:
            query_result = sf.query_more(query_result.get('nextRecordsUrl'), True)
            all_records.extend(query_result.get('records', []))
            status_placeholder.info(f"Retrieved {len(all_records)} of {total_size} opportunities...")
        
        if not all_records:
            status_placeholder.error("No opportunities found in your Salesforce org.")
            return pd.DataFrame()
            
        # Process records with enhanced fields
        processed_records = []
        for record in all_records:
            if record and 'attributes' in record:
                            record_dict = {
                                'Opportunity ID': record.get('Id'),
                                'Opportunity Name': record.get('Name'),
                                'Stage': record.get('StageName'),
                                'Amount': record.get('Amount'),
                                'Close Date': record.get('CloseDate'),
                                'Created Date': record.get('CreatedDate'),
                                'Probability (%)': record.get('Probability'),
                                'Customer ID': record.get('AccountId'),
                                'Fiscal Year': record.get('FiscalYear'),
                    'Fiscal Quarter': record.get('FiscalQuarter'),
                    'Type': record.get('Type'),
                    'Is Closed': record.get('IsClosed'),
                    'Is Won': record.get('IsWon'),
                    'Region': record.get('Region__c'),
                    'Branch': record.get('Branch__c'),
                    'Weighted AVG': record.get('Weighted_AVG__c'),
                    'Gross Profit': record.get('Gross_Profit__c'),
                    'Gross Profit %': record.get('Gross_Profit_Percentage__c'),
                    'Project Number': record.get('Project_Number__c'),
                    'Quote Number': record.get('Quote_Number__c'),
                    'Job Number': record.get('Job_Number__c'),
                    'Project Start Date': record.get('Project_Start_Date__c'),
                    'Estimated Project End Date': record.get('Estimated_Project_End_Date__c'),
                    'Bid Due Date': record.get('Bid_Due_Date__c'),
                    'RFI Due Date': record.get('RFI_Due_Date__c'),
                    'Job Walk Date': record.get('Job_Walk_Date__c'),
                    'Opportunity Created For': record.get('Opportunity_Created_For__c'),
                    'Is Renewal': record.get('Is_this_a_Renewal__c'),
                    'Owner Name': record.get('Owner_Name__c'),
                    'Account Name': record.get('Account_Name__c'),
                    'Owner Branch': record.get('Owner_Branch__c'),
                    'Owner Region': record.get('Owner_Region__c')
                }
                
                # Handle nested fields
                            if record.get('Owner') and isinstance(record.get('Owner'), dict):
                                record_dict['Opportunity Owner'] = record.get('Owner', {}).get('Name')
                                
                            if record.get('Account') and isinstance(record.get('Account'), dict):
                                record_dict['Account Name'] = record.get('Account', {}).get('Name')
                            
                            processed_records.append(record_dict)
                        
        # Create DataFrame
                        df = pd.DataFrame(processed_records)
                    
        # Filter for Cary Branch data only (API name is 200)
        if 'Branch' in df.columns:
            df = df[df['Branch'] == '200'].copy()
        
        # Convert date strings to datetime objects
        date_fields = ['Close Date', 'Created Date', 'Project Start Date', 
                      'Estimated Project End Date', 'Bid Due Date', 'RFI Due Date', 'Job Walk Date']
        for date_field in date_fields:
            if date_field in df.columns:
                df[date_field] = pd.to_datetime(df[date_field], errors='coerce')
        
        # Calculate derived fields
        if 'Amount' in df.columns and 'Probability (%)' in df.columns:
            df['Weighted AVG'] = df['Amount'] * df['Probability (%)'] / 100
        
        # Calculate Age in days
        if 'Created Date' in df.columns:
            try:
                now = pd.Timestamp.now().tz_localize(None)
                if df['Created Date'].dt.tz is not None:
                    created_dates = df['Created Date'].dt.tz_localize(None)
                else:
                    created_dates = df['Created Date']
                df['Age'] = (now - created_dates).dt.days
            except Exception as age_error:
                status_placeholder.warning(f"Could not calculate opportunity age: {str(age_error)}")
        
        # Add fiscal year and quarter if not available
        if 'Close Date' in df.columns and 'Fiscal Year' not in df.columns:
            df['Fiscal Year'] = df['Close Date'].dt.year
        
        if 'Close Date' in df.columns and 'Fiscal Quarter' not in df.columns:
            df['Fiscal Quarter'] = df['Close Date'].dt.quarter
        
        status_placeholder.success(f"Found {len(df)} Cary Branch opportunities in Salesforce.")
        time.sleep(3)
        status_placeholder.empty()
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching opportunities: {str(e)}")
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        return pd.DataFrame()

# Create enhanced gauge chart function
def create_gauge_chart(value, min_val, max_val, title, color_scheme='red_yellow_green'):
    if color_scheme == 'red_yellow_green':
        colors = ['#e74c3c', '#f39c12', '#27ae60']
        thresholds = [min_val, (min_val + max_val) / 2, max_val]
    else:
        colors = ['#27ae60', '#f39c12', '#e74c3c']
        thresholds = [min_val, (min_val + max_val) / 2, max_val]
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 16, 'color': '#202124'}},
        delta = {'reference': max_val, 'font': {'size': 12}},
        gauge = {
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "#5f6368"},
            'bar': {'color': "#4285f4", 'thickness': 0.3},
            'bgcolor': "#f8f9fa",
            'borderwidth': 1,
            'bordercolor': "#dadce0",
            'steps': [
                {'range': [thresholds[0], thresholds[1]], 'color': '#ea4335'},
                {'range': [thresholds[1], thresholds[2]], 'color': '#fbbc04'},
                {'range': [thresholds[2], max_val], 'color': '#34a853'}
            ],
            'threshold': {
                'line': {'color': "#202124", 'width': 3},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#202124', 'family': 'Google Sans, Roboto, Arial, sans-serif'}
    )
    
    return fig

# Create enhanced owner sales chart
def create_owner_sales_chart(df):
    # Filter for closed won opportunities
    closed_won = df[df['Stage'] == 'Closed Won'].copy()
    
    if closed_won.empty:
        return None
    
    # Group by owner and sum amounts
    owner_sales = closed_won.groupby('Opportunity Owner')['Amount'].sum().reset_index()
    owner_sales = owner_sales.sort_values('Amount', ascending=True)
    
    # Create enhanced horizontal bar chart
            fig = px.bar(
        owner_sales,
        x='Amount',
        y='Opportunity Owner',
        orientation='h',
        title='Owner Project Sales MTD Cary',
        color='Amount',
        color_continuous_scale='Blues',
        text='Amount'
    )
    
    fig.update_layout(
        height=350,
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis_title='Sum of Amount ($)',
        yaxis_title='Opportunity Owner',
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#202124', 'family': 'Google Sans, Roboto, Arial, sans-serif'},
        title={'font': {'size': 16, 'color': '#202124'}}
    )
    
    fig.update_traces(
        texttemplate='$%{text:,.0f}',
        textposition='outside'
    )
    
    return fig

# Calculate dashboard metrics
def calculate_dashboard_metrics(df):
    metrics = {}
    
    # Current date for filtering
    current_date = pd.Timestamp.now()
    current_month = current_date.month
    current_year = current_date.year
    
    # Pipeline - Current Month
    current_month_opps = df[
        (df['Close Date'].dt.month == current_month) & 
        (df['Close Date'].dt.year == current_year) &
        (df['Stage'] != 'Closed Won')
    ]
    metrics['pipeline_current_month'] = current_month_opps['Amount'].sum()
    
    # Pipeline - Current Month + Next 2 Months
    next_2_months = current_date + pd.DateOffset(months=2)
    pipeline_3_months = df[
        (df['Close Date'] >= current_date) &
        (df['Close Date'] <= next_2_months) &
        (df['Stage'] != 'Closed Won')
    ]
    metrics['pipeline_3_months'] = pipeline_3_months['Amount'].sum()
    
    # Pipeline - Now through FY2025
    fy_end = pd.Timestamp(2025, 6, 30)  # Assuming fiscal year ends June 30
    pipeline_fy = df[
        (df['Close Date'] >= current_date) &
        (df['Close Date'] <= fy_end) &
        (df['Stage'] != 'Closed Won')
    ]
    metrics['pipeline_fy'] = pipeline_fy['Amount'].sum()
    
    # Project Sales Forecast
    project_forecast = df[
        (df['Type'] == 'Project') &
        (df['Close Date'] >= current_date)
    ]
    metrics['project_sales_forecast'] = project_forecast['Amount'].sum()
    
    # Project Sales MTD
    project_mtd = df[
        (df['Type'] == 'Project') &
        (df['Close Date'].dt.month == current_month) &
        (df['Close Date'].dt.year == current_year) &
        (df['Stage'] == 'Closed Won')
    ]
    metrics['project_sales_mtd'] = project_mtd['Amount'].sum()
    
    # Transactional Forecast
    transactional_forecast = df[
        (df['Type'] == 'Transactional') &
        (df['Close Date'] >= current_date)
    ]
    metrics['transactional_forecast'] = transactional_forecast['Amount'].sum()
    
    # Transactional MTD
    transactional_mtd = df[
        (df['Type'] == 'Transactional') &
        (df['Close Date'].dt.month == current_month) &
        (df['Close Date'].dt.year == current_year) &
        (df['Stage'] == 'Closed Won')
    ]
    metrics['transactional_mtd'] = transactional_mtd['Amount'].sum()
    
    # Service Forecast
    service_forecast = df[
        (df['Type'] == 'Service') &
        (df['Close Date'] >= current_date)
    ]
    metrics['service_forecast'] = service_forecast['Amount'].sum()
    
    # Service MTD
    service_mtd = df[
        (df['Type'] == 'Service') &
        (df['Close Date'].dt.month == current_month) &
        (df['Close Date'].dt.year == current_year) &
        (df['Stage'] == 'Closed Won')
    ]
    metrics['service_mtd'] = service_mtd['Amount'].sum()
    
    return metrics

# Create enhanced dashboard layout
def create_dashboard(df, metrics):
    # Dashboard header with logo and title
    st.markdown("""
    <div class="dashboard-header">
        <img src="https://www.salesforce.com/content/dam/web/en_us/www/images/home/logo-salesforce.svg" class="logo">
        <div>
            <h1 class="header-title">Cary Forecasts MTD</h1>
            <p class="header-subtitle">July 31, 2025, 10:00 AM | Viewed by Mike Procopio</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Pipeline Gauge Charts
    st.markdown('<div class="section-title">Pipeline Metrics</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
        fig1 = create_gauge_chart(
            metrics['pipeline_current_month'], 
            0, 23000000, 
            "Pipeline - Current Month"
        )
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown(f'<div class="metric-value">${metrics["pipeline_current_month"]:,.0f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Current Month Pipeline</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
        with col2:
        st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
        fig2 = create_gauge_chart(
            metrics['pipeline_3_months'], 
            0, 100000000, 
            "Pipeline - Current Month + Next 2 Months"
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown(f'<div class="metric-value">${metrics["pipeline_3_months"]:,.0f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">3-Month Pipeline</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Pipeline - Now through FY2025</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">${metrics["pipeline_fy"]:,.0f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Keith\'s pipeline remainder of FY</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Sales Metrics and Owner Chart
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="sales-metrics">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Sales Metrics</div>', unsafe_allow_html=True)
        
        # Project Sales
        col1a, col1b = st.columns(2)
        with col1a:
            st.markdown('<div class="metric-label">Project Sales Forecast</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">${metrics["project_sales_forecast"]:,.1f}</div>', unsafe_allow_html=True)
        with col1b:
            st.markdown('<div class="metric-label">Project Sales MTD</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value metric-negative">${metrics["project_sales_mtd"]:,.1f}</div>', unsafe_allow_html=True)
        
        # Transactional Sales
        col2a, col2b = st.columns(2)
        with col2a:
            st.markdown('<div class="metric-label">Transactional Forecast</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">${metrics["transactional_forecast"]:,.0f}</div>', unsafe_allow_html=True)
        with col2b:
            st.markdown('<div class="metric-label">Transactional MTD</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value metric-warning">${metrics["transactional_mtd"]:,.0f}</div>', unsafe_allow_html=True)
        
        # Service Sales
        col3a, col3b = st.columns(2)
        with col3a:
            st.markdown('<div class="metric-label">Service Forecast</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">${metrics["service_forecast"]:,.1f}</div>', unsafe_allow_html=True)
        with col3b:
            st.markdown('<div class="metric-label">Service MTD</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value metric-negative">${metrics["service_mtd"]:,.1f}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="owner-chart">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Owner Project Sales MTD Cary</div>', unsafe_allow_html=True)
        owner_chart = create_owner_sales_chart(df)
        if owner_chart:
            st.plotly_chart(owner_chart, use_container_width=True)
        else:
            st.info("No closed won opportunities found for owner breakdown")
        st.markdown('</div>', unsafe_allow_html=True)

# Main app
def main():
    # Hardcoded credentials for automatic login
    sf_credentials = {
        'username': "william.evans@avidex.com",
        'password': "D_w?ygrM6g9rp",
        'security_token': "V7W9o94PW3TVtBsqaS5zkNKS",
        'domain': 'login'
    }
    
    # Attempt to fetch and display data
    try:
        # Use session state to store data
        if 'salesforce_data' not in st.session_state:
            connection_placeholder = st.empty()
            
            with st.spinner("Connecting to Salesforce..."):
                sf = Salesforce(
                    username=sf_credentials['username'],
                    password=sf_credentials['password'],
                    security_token=sf_credentials['security_token'],
                    domain=sf_credentials['domain']
                )
                
                with st.spinner("Fetching Cary Branch opportunities..."):
                    df = fetch_opportunities(sf)
                    
                    if not df.empty:
                        st.session_state['salesforce_data'] = df
                    else:
                        error_placeholder = st.empty()
                        error_placeholder.error("No Cary Branch opportunities could be retrieved from Salesforce.")
                        info_placeholder = st.empty()
                        info_placeholder.info("Please check your Salesforce permissions and try again.")
                        time.sleep(10)
                        error_placeholder.empty()
                        info_placeholder.empty()
                        return
        else:
            df = st.session_state['salesforce_data']
        
        # Calculate metrics
        metrics = calculate_dashboard_metrics(df)
        
        # Create dashboard
        create_dashboard(df, metrics)
                    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        st.info("Please check your Salesforce credentials and connection.")

if __name__ == "__main__":
    main()