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
        results = sf.query(query)
        
        if not results.get('records'):
            status_placeholder.error("No opportunities found in your Salesforce org.")
            return pd.DataFrame()
            
        # Convert to DataFrame - very carefully handle possible None values
        records = []
        for record in results.get('records', []):
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
                    Account.Name
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
                        Account.Name
                    FROM Opportunity
                    """
                    
                    complete_results = sf.query(complete_query)
                    
                    if complete_results.get('records'):
                        # Process records with additional fields
                        complete_records = []
                        for record in complete_results.get('records', []):
                            record_dict = {
                                'Opportunity ID': record.get('Id'),
                                'Opportunity Name': record.get('Name'),
                                'Stage': record.get('StageName'),
                                'Amount': record.get('Amount'),
                                'Close Date': record.get('CloseDate'),
                                'Created Date': record.get('CreatedDate'),
                                'Probability (%)': record.get('Probability'),
                                'Customer ID': record.get('AccountId')
                            }
                            
                            # Carefully handle nested fields
                            if record.get('Owner') and isinstance(record.get('Owner'), dict):
                                record_dict['Opportunity Owner'] = record.get('Owner', {}).get('Name')
                                
                            if record.get('Account') and isinstance(record.get('Account'), dict):
                                record_dict['Account Name'] = record.get('Account', {}).get('Name')
                            
                            complete_records.append(record_dict)
                        
                        # Create more complete dataframe
                        df = pd.DataFrame(complete_records)
                    
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
    
    # Initialize session state variables for credentials if they don't exist
    if 'sf_credentials' not in st.session_state:
        # Try to get username and password from secrets.toml
        try:
            username = st.secrets["salesforce"]["username"]
            password = st.secrets["salesforce"]["password"]
            domain = st.secrets["salesforce"].get("domain", "login")
            
            # Initialize with secrets but empty security token
            st.session_state.sf_credentials = {
                'username': username,
                'password': password,
                'security_token': '',
                'domain': domain
            }
            using_secrets = True
        except:
            # If no secrets found, start with empty credentials
            st.session_state.sf_credentials = {
                'username': '',
                'password': '',
                'security_token': '',
                'domain': 'login'
            }
            using_secrets = False
    else:
        # Check if we're using secrets for username/password
        try:
            using_secrets = (st.session_state.sf_credentials['username'] == st.secrets["salesforce"]["username"])
        except:
            using_secrets = False
    
    # Add Salesforce credential form to sidebar
    st.sidebar.subheader("Salesforce Credentials")
    
    # Create a form for the credentials
    with st.sidebar.form(key="credentials_form"):
        if using_secrets:
            # If using secrets, only show security token field
            st.markdown("**Username and password loaded from secrets**")
            security_token = st.text_input("Security Token (required)", 
                                          type="password", 
                                          value=st.session_state.sf_credentials['security_token'])
        else:
            # If not using secrets, allow full credential entry
            username = st.text_input("Username (Email)", value=st.session_state.sf_credentials['username'])
            password = st.text_input("Password", type="password", value=st.session_state.sf_credentials['password'])
            security_token = st.text_input("Security Token", type="password", value=st.session_state.sf_credentials['security_token'])
            domain = st.text_input("Domain (Default: login)", value=st.session_state.sf_credentials['domain'])
        
        submit_button = st.form_submit_button(label="Connect to Salesforce")
        
        if submit_button:
            if using_secrets:
                # Only update the security token
                st.session_state.sf_credentials['security_token'] = security_token
            else:
                # Store all credentials in session state
                st.session_state.sf_credentials = {
                    'username': username,
                    'password': password,
                    'security_token': security_token,
                    'domain': domain if domain else 'login'
                }
            
            # Clear any cached data to force refresh
            if 'salesforce_data' in st.session_state:
                del st.session_state['salesforce_data']
    
    # Show connection status
    if using_secrets and st.session_state.sf_credentials['security_token']:
        st.sidebar.info("Ready to connect with credentials from secrets.toml")
    elif not using_secrets and st.session_state.sf_credentials['username'] and st.session_state.sf_credentials['password']:
        st.sidebar.info("Ready to connect with provided credentials")
    else:
        if using_secrets:
            st.sidebar.warning("Please enter your Salesforce security token to connect")
        else:
            st.sidebar.warning("Please enter your Salesforce credentials to connect")
    
    # Add manual refresh button with a unique key
    refresh_key = f"refresh_button_{session_id}"
    if st.sidebar.button("🔄 Refresh Data", key=refresh_key):
        # Clear any cached data
        if 'salesforce_data' in st.session_state:
            del st.session_state['salesforce_data']
            st.rerun()  # Force a rerun to update everything
    
    # Check if we have credentials to connect
    if using_secrets:
        credentials_provided = st.session_state.sf_credentials['security_token']
    else:
        credentials_provided = (st.session_state.sf_credentials['username'] and 
                              st.session_state.sf_credentials['password'] and
                              st.session_state.sf_credentials['security_token'])
    
    if not credentials_provided:
        if using_secrets:
            st.info("Please enter your Salesforce security token in the sidebar to get started.")
            st.write("""
            ### How to get your Salesforce security token:
            1. Log in to Salesforce
            2. Go to your profile (click your name/image in the top right)
            3. Select "Settings"
            4. In the left sidebar, navigate to "My Personal Information" > "Reset Security Token"
            5. Click the "Reset Security Token" button
            6. A new security token will be emailed to you
            """)
        else:
            st.info("Please enter your Salesforce credentials in the sidebar to get started.")
            st.write("""
            ### How to get your Salesforce security token:
            1. Log in to Salesforce
            2. Go to your profile (click your name/image in the top right)
            3. Select "Settings"
            4. In the left sidebar, navigate to "My Personal Information" > "Reset Security Token"
            5. Click the "Reset Security Token" button
            6. A new security token will be emailed to you
            """)
        return
    
                    # Attempt to fetch and display data if credentials are provided
    try:
        # Use session state to store data
        if 'salesforce_data' not in st.session_state:
            # Create placeholder for connection message
            connection_placeholder = st.empty()
            
            # Use the st.spinner context manager
            with st.spinner("Connecting to Salesforce..."):
                # Connect to Salesforce using provided credentials
                sf = Salesforce(
                    username=st.session_state.sf_credentials['username'],
                    password=st.session_state.sf_credentials['password'],
                    security_token=st.session_state.sf_credentials['security_token'],
                    domain=st.session_state.sf_credentials['domain']
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
                
                date_range = st.sidebar.date_input(
                    "Close Date Range",
                    value=(min_date, max_date),
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