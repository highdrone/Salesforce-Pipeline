import streamlit as st
import pandas as pd
import plotly.express as px
import io
import base64
import datetime
import warnings
import urllib3

# Suppress urllib3 warnings about LibreSSL on macOS
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")
# Additional suppression for NotOpenSSLWarning
urllib3.disable_warnings()

# For Streamlit Cloud, we can also try setting the environment variable
import os
os.environ['PYTHONWARNINGS'] = "ignore:urllib3"

# Import Salesforce after warning suppression
from simple_salesforce import Salesforce

# Page configuration
st.set_page_config(
    page_title="Salesforce Opportunity Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .stButton > button {
        width: 100%;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Main function to fetch opportunities
def fetch_opportunities(sf):
    try:
        # Import time at the beginning of the function to avoid UnboundLocalError
        import time
        
        # Create placeholder for status messages
        status_placeholder = st.empty()
        
        # Start with a minimal query that has fewer fields to avoid permission issues
        query = """
        SELECT 
            Id, Name, StageName
        FROM Opportunity
        """
        
        # Execute the query
        status_placeholder.info("Fetching opportunities from Salesforce...")
        
        # Handle pagination for large datasets
        all_records = []
        query_result = sf.query(query)
        all_records.extend(query_result.get('records', []))
        
        # Check if more records exist
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
            
        # Convert to DataFrame - very carefully handle possible None values
        records = []
        for record in all_records:
            # Skip the Salesforce attributes
            if record and 'attributes' in record:
                record_dict = {k: v for k, v in record.items() if k != 'attributes'}
            else:
                record_dict = {}
                
            records.append(record_dict)
            
        # Create basic dataframe with just ID, Name and Stage
        df = pd.DataFrame(records)
        
        # Rename columns to match expected format
        column_mapping = {
            'Id': 'Opportunity ID',
            'Name': 'Opportunity Name',
            'StageName': 'Stage'
        }
        df = df.rename(columns=column_mapping)
        
        # Try to get more fields in separate queries if available
        try:
            # Try to get additional fields in a separate query
            if len(df) > 0:
                sample_opp_id = df['Opportunity ID'].iloc[0]
                status_placeholder.info(f"Successfully retrieved basic opportunity data. Checking for additional fields...")
                
                # Try to get more fields for the first opportunity to see what's available
                sample_query = f"""
                SELECT 
                    Id, Amount, CloseDate, CreatedDate, 
                    Probability, Owner.Name, AccountId,
                    Account.Name, FiscalYear, FiscalQuarter
                FROM Opportunity
                WHERE Id = '{sample_opp_id}'
                LIMIT 1
                """
                
                sample_result = sf.query(sample_query)
                if sample_result.get('records'):
                    status_placeholder.success("Additional fields are available. Retrieving complete data...")
                    
                    # Now get all opportunities with the fields that we know exist
                    complete_query = """
                    SELECT 
                        Id, Name, StageName, Amount, CloseDate, 
                        CreatedDate, Probability, Owner.Name, AccountId,
                        Account.Name, FiscalYear, FiscalQuarter
                    FROM Opportunity
                    """
                    
                    # Handle pagination for complete data
                    complete_records = []
                    query_result = sf.query(complete_query)
                    complete_records.extend(query_result.get('records', []))
                    
                    # Check if more records exist
                    total_size = query_result.get('totalSize', 0)
                    status_placeholder.info(f"Found {total_size} total opportunities with complete data, retrieving all records...")
                    
                    # Continue querying if there are more records
                    while query_result.get('done') is False:
                        query_result = sf.query_more(query_result.get('nextRecordsUrl'), True)
                        complete_records.extend(query_result.get('records', []))
                        status_placeholder.info(f"Retrieved {len(complete_records)} of {total_size} opportunities with complete data...")
                    
                    if complete_records:
                        # Process records with additional fields
                        processed_records = []
                        for record in complete_records:
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
                                'Fiscal Quarter': record.get('FiscalQuarter')
                            }
                            
                            # Carefully handle nested fields
                            if record.get('Owner') and isinstance(record.get('Owner'), dict):
                                record_dict['Opportunity Owner'] = record.get('Owner', {}).get('Name')
                                
                            if record.get('Account') and isinstance(record.get('Account'), dict):
                                record_dict['Account Name'] = record.get('Account', {}).get('Name')
                            
                            processed_records.append(record_dict)
                        
                        # Create more complete dataframe
                        df = pd.DataFrame(processed_records)
                    
        except Exception as e:
            status_placeholder.warning(f"Could not retrieve additional fields. Using basic opportunity data only. Error: {str(e)}")
            # Clear warning after 5 seconds
            import time
            time.sleep(5)
            status_placeholder.empty()
        
        # Try to convert date strings to datetime objects
        for date_field in ['Close Date', 'Created Date']:
            if date_field in df.columns:
                df[date_field] = pd.to_datetime(df[date_field], errors='coerce')
        
        # Add year and quarter from dates if not available directly
        if 'Close Date' in df.columns and 'Fiscal Year' not in df.columns:
            df['Fiscal Year'] = df['Close Date'].dt.year
        
        if 'Close Date' in df.columns and 'Fiscal Quarter' not in df.columns:
            df['Fiscal Quarter'] = df['Close Date'].dt.quarter
        
        # Calculate derived fields if the necessary columns exist
        if 'Amount' in df.columns and 'Probability (%)' in df.columns:
            df['Weighted AVG'] = df['Amount'] * df['Probability (%)'] / 100
        
        # Calculate Age in days from Created Date - FIX TIMEZONE ISSUE
        if 'Created Date' in df.columns:
            try:
                # Make sure both timestamps are timezone-naive
                now = pd.Timestamp.now().tz_localize(None)
                
                # Convert Created Date to timezone-naive if it has timezone info
                if df['Created Date'].dt.tz is not None:
                    created_dates = df['Created Date'].dt.tz_localize(None)
                else:
                    created_dates = df['Created Date']
                
                # Calculate age in days
                df['Age'] = (now - created_dates).dt.days
            except Exception as age_error:
                status_placeholder.warning(f"Could not calculate opportunity age: {str(age_error)}")
                # Clear warning after 5 seconds
                import time
                time.sleep(5)
                status_placeholder.empty()
        
        # Print year distribution for debugging
        year_distribution = df.groupby('Fiscal Year').size()
        status_placeholder.info(f"Year distribution: {year_distribution.to_dict()}")
        time.sleep(10)  # Show this info for longer
        
        # Display final success message with count, then clear after 5 seconds
        status_placeholder.success(f"Found {len(df)} opportunities in Salesforce.")
        import time
        time.sleep(5)
        status_placeholder.empty()
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching opportunities: {str(e)}")
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        return pd.DataFrame()

# Download function for CSV export
def download_csv(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="opportunities.csv">Download CSV File</a>'
    return href

# Create visualizations based on available data
def create_visualizations(df):
    if df.empty:
        st.write("No data to display.")
        return
    
    # Display metrics at the top
    st.subheader("Overview")
    metric_cols = st.columns(4)
    
    with metric_cols[0]:
        st.metric("Total Opportunities", f"{len(df):,}")
    
    if 'Amount' in df.columns:
        with metric_cols[1]:
            total_amount = df['Amount'].sum()
            st.metric("Total Amount", f"${total_amount:,.2f}")
            
    if 'Weighted AVG' in df.columns:
        with metric_cols[2]:
            weighted_total = df['Weighted AVG'].sum()
            st.metric("Weighted Pipeline", f"${weighted_total:,.2f}")
            
    if 'Probability (%)' in df.columns:
        with metric_cols[3]:
            avg_probability = df['Probability (%)'].mean()
            st.metric("Avg. Probability", f"{avg_probability:.1f}%")
    
    # Create charts based on available columns
    col1, col2 = st.columns(2)
    
    # Opportunities by Stage
    if 'Stage' in df.columns:
        with col1:
            st.subheader("Opportunities by Stage")
            stage_counts = df['Stage'].value_counts().reset_index()
            stage_counts.columns = ['Stage', 'Count']
            
            fig = px.bar(
                stage_counts,
                x='Stage',
                y='Count',
                color='Stage',
                title='Number of Opportunities by Stage'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Amount by Stage
    if 'Stage' in df.columns and 'Amount' in df.columns:
        with col2:
            st.subheader("Amount by Stage")
            stage_amounts = df.groupby('Stage')['Amount'].sum().reset_index()
            
            fig = px.bar(
                stage_amounts,
                x='Stage',
                y='Amount',
                color='Stage',
                title='Total Amount by Stage',
                text_auto=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # More visualizations in the next row
    col1, col2 = st.columns(2)
    
    # Fiscal Year visualizations
    if 'Fiscal Year' in df.columns:
        with col1:
            st.subheader("Opportunities by Fiscal Year")
            year_counts = df.groupby('Fiscal Year').size().reset_index()
            year_counts.columns = ['Year', 'Count']
            year_counts = year_counts.sort_values('Year')
            
            fig = px.bar(
                year_counts,
                x='Year',
                y='Count',
                color='Count',
                title='Opportunities by Fiscal Year'
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            if 'Amount' in df.columns:
                st.subheader("Amount by Fiscal Year")
                year_amounts = df.groupby('Fiscal Year')['Amount'].sum().reset_index()
                year_amounts.columns = ['Year', 'Amount']
                year_amounts = year_amounts.sort_values('Year')
                
                fig = px.bar(
                    year_amounts,
                    x='Year',
                    y='Amount',
                    color='Amount',
                    title='Total Amount by Fiscal Year'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # More visualizations in the next row
    col1, col2 = st.columns(2)
    
    # Timeline visualizations
    if 'Close Date' in df.columns:
        with col1:
            st.subheader("Opportunities Over Time")
            
            # Make sure Close Date is a datetime
            df['Close Date'] = pd.to_datetime(df['Close Date'], errors='coerce')
            
            # Group by month
            df['Month'] = df['Close Date'].dt.strftime('%Y-%m')
            timeline_data = df.groupby('Month').size().reset_index()
            timeline_data.columns = ['Month', 'Count']
            timeline_data = timeline_data.sort_values('Month')
            
            fig = px.line(
                timeline_data,
                x='Month',
                y='Count',
                title='Opportunities by Close Date',
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Top Accounts visualization
    if 'Account Name' in df.columns:
        with col2:
            st.subheader("Top Accounts")
            top_accounts = df['Account Name'].value_counts().head(10).reset_index()
            top_accounts.columns = ['Account', 'Count']
            
            fig = px.bar(
                top_accounts,
                y='Account',
                x='Count',
                orientation='h',
                title='Top 10 Accounts by Opportunity Count',
                color='Count'
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
    
    # Display raw data in an expandable section
    with st.expander("View Raw Data"):
        st.dataframe(df, use_container_width=True)

# Main app
def main():
    st.sidebar.image("https://www.salesforce.com/content/dam/web/en_us/www/images/home/logo-salesforce.svg", width=200)
    st.title("Salesforce Opportunities Dashboard")
    
    # Generate a session-specific ID for unique keys
    if 'session_id' not in st.session_state:
        st.session_state.session_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    session_id = st.session_state.session_id
    
    # Hardcoded credentials for automatic login
    sf_credentials = {
        'username': "william.evans@avidex.com",
        'password': "D_w?ygrM6g9rp",
        'security_token': "V7W9o94PW3TVtBsqaS5zkNKS",
        'domain': 'login'
    }
    
    # Show connection status in sidebar
    st.sidebar.subheader("Connection Status")
    st.sidebar.info("✅ Auto-connected to Salesforce")
    
    # Add manual refresh button with a unique key
    refresh_key = f"refresh_button_{session_id}"
    if st.sidebar.button("🔄 Refresh Data", key=refresh_key):
        # Clear any cached data
        if 'salesforce_data' in st.session_state:
            del st.session_state['salesforce_data']
            st.rerun()  # Force a rerun to update everything
    
    # Attempt to fetch and display data
    try:
        # Use session state to store data
        if 'salesforce_data' not in st.session_state:
            # Create placeholder for connection message
            connection_placeholder = st.empty()
            
            # Use the st.spinner context manager
            with st.spinner("Connecting to Salesforce..."):
                # Connect to Salesforce using hardcoded credentials
                sf = Salesforce(
                    username=sf_credentials['username'],
                    password=sf_credentials['password'],
                    security_token=sf_credentials['security_token'],
                    domain=sf_credentials['domain']
                )
                
                sidebar_placeholder = st.sidebar.empty()
                sidebar_placeholder.success("✅ Connected to Salesforce")
                # Clear success message after 5 seconds
                import time
                time.sleep(5)
                sidebar_placeholder.empty()
                
                # Fetch opportunities
                with st.spinner("Fetching all opportunities (this may take some time)..."):
                    df = fetch_opportunities(sf)
                    
                    if not df.empty:
                        # Store data in session state
                        st.session_state['salesforce_data'] = df
                        # The success message is handled within fetch_opportunities
                    else:
                        error_placeholder = st.empty()
                        error_placeholder.error("No opportunities could be retrieved from Salesforce.")
                        info_placeholder = st.empty()
                        info_placeholder.info("Please check your Salesforce permissions and try again.")
                        # Clear messages after 10 seconds
                        time.sleep(10)
                        error_placeholder.empty()
                        info_placeholder.empty()
                        return
        else:
            # Use cached data
            df = st.session_state['salesforce_data']
            # Show temporary message
            temp_message = st.empty()
            temp_message.success(f"Showing {len(df)} opportunities from Salesforce.")
            # Clear after 5 seconds
            import time
            time.sleep(5)
            temp_message.empty()
        
        # Add filters in sidebar
        st.sidebar.subheader("Filters")
        
        filtered_df = df.copy()
        
        # Stage filter (if available)
        if 'Stage' in df.columns:
            stage_options = ['All'] + sorted(df['Stage'].unique().tolist())
            selected_stage = st.sidebar.selectbox("Stage", stage_options, key=f"stage_filter_{session_id}")
            
            if selected_stage != 'All':
                filtered_df = filtered_df[filtered_df['Stage'] == selected_stage]
        
        # Account filter (if available)
        if 'Account Name' in df.columns:
            # Filter out None/NaN values and convert to list of strings
            valid_accounts = df['Account Name'].dropna().unique().tolist()
            account_options = ['All'] + sorted(valid_accounts)
            selected_account = st.sidebar.selectbox("Account", account_options, key=f"account_filter_{session_id}")
            
            if selected_account != 'All':
                filtered_df = filtered_df[filtered_df['Account Name'] == selected_account]
        
        # Date range filter (if available)
        if 'Close Date' in df.columns:
            date_col = 'Close Date'
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            valid_dates = df[date_col].dropna()
            if not valid_dates.empty:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
                
                # Calculate default dates: today and today + 3 days
                today = datetime.date.today()
                three_days_later = today + datetime.timedelta(days=90)
                
                # Make sure default dates are within the available range
                default_start = max(today, min_date) if today <= max_date else min_date
                default_end = min(three_days_later, max_date) if three_days_later >= min_date else max_date
                
                date_range = st.sidebar.date_input(
                    "Close Date Range",
                    value=(default_start, default_end),
                    min_value=min_date,
                    max_value=max_date,
                    key=f"date_filter_{session_id}"
                )
                
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    filtered_df = filtered_df[(filtered_df[date_col].dt.date >= start_date) & 
                                           (filtered_df[date_col].dt.date <= end_date)]
        
        # Show filter summary
        filter_count = len(filtered_df)
        total_count = len(df)
        if filter_count < total_count:
            st.sidebar.info(f"Filtered: {filter_count} of {total_count} opportunities")
        
        # Create visualizations with filtered data
        create_visualizations(filtered_df)
        
        # Add download option
        st.sidebar.subheader("Export Options")
        st.sidebar.markdown(download_csv(filtered_df), unsafe_allow_html=True)
        
        # Show last updated time
        st.sidebar.caption(f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        st.info("Please check your Salesforce credentials and connection.")

if __name__ == "__main__":
    main()