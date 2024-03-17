import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import threading
# import asyncio
import numpy as np

# Assuming these functions are defined elsewhere in your codebase
from utils.database import get_all_companies, get_price_history , batch_create_companies , batch_insert_asset_prices , reportHelper
from utils.processingSentiments import sentiment_for_company

# Caching database queries to prevent unnecessary re-fetching
@st.cache_data
def get_all_companies_cached():
    return get_all_companies()

@st.cache_data
def get_price_history_cached(isins, start_date, end_date):
    return get_price_history(isins, start_date, end_date)

@st.cache_data
def calculate_largest_contiguous_change(df, lookback_days):
    if df.empty:
        return pd.DataFrame(columns=['isin', 'start_date', 'end_date', 'price_start', 'price_end', 'price_change_pct'])
    
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by=['isin', 'date'], inplace=True)

    results = []

    for isin, group in df.groupby('isin'):
        # Filter rows within the lookback window from the last available date
        latest_date = group['date'].max()
        lookback_date = latest_date - pd.Timedelta(days=lookback_days)
        within_lookback = group[group['date'] >= lookback_date]

        if not within_lookback.empty:
            # Get the start and end date of the largest contiguous period
            start_date = within_lookback['date'].min()
            end_date = within_lookback['date'].max()

            # Get start and end prices
            price_start = within_lookback.loc[within_lookback['date'] == start_date, 'price'].values[0]
            price_end = within_lookback.loc[within_lookback['date'] == end_date, 'price'].values[0]

            # Calculate price change percentage
            price_change_pct = (price_end - price_start) / price_start * 100

            results.append({
                'isin': isin,
                'start_date': start_date,
                'end_date': end_date,
                'price_start': price_start,
                'price_end': price_end,
                'price_change_pct': price_change_pct
            })

    # Convert results list to DataFrame
    results_df = pd.DataFrame(results)
    
    return results_df


def process_uploaded_file(file, purpose):
    df = pd.read_csv(file)
    df.columns = [col.strip() for col in df.columns]
    print(df,df.columns)
    if purpose == 'Add Companies to Track':
        expected_columns = ['isin', 'asset_name', 'description', 'country_of_exposure', 'inst_type', 'market_cap']
        # Strip white spaces from column names and rename the columns

        if set(expected_columns).issubset(df.columns):
            df['market_cap'] = df['market_cap'].str.replace(',', '')
            # Convert DataFrame to list of tuples
            company_data = df[expected_columns].values.tolist()
            batch_create_companies(company_data)
            # Update session state
            st.session_state.companies = get_all_companies_cached()
        else:
            st.error("Uploaded CSV is missing some required columns for adding companies.")
    
    elif purpose == 'Batch Update Prices':
        expected_columns = ['isin', 'date', 'price']
        if set(expected_columns).issubset(df.columns):
            # Convert DataFrame to list of tuples
            price_data = df[expected_columns].values.tolist()
            batch_insert_asset_prices(price_data)
            # Update session state
            isins = st.session_state.companies['isin'].tolist()
            st.session_state.price_history = get_price_history_cached(isins, st.session_state['start_date'], st.session_state['end_date'])
        else:
            st.error("Uploaded CSV is missing some required columns for updating prices.")

# Initialize session state for companies and price history if not already set
expected_columns_companies_df = ['isin', 'asset_name', 'description', 'country_of_exposure', 'inst_type', 'market_cap']
if 'companies' not in st.session_state or st.session_state.companies.empty:
    st.session_state.companies = get_all_companies_cached()

# Initialize session state for start and end dates if not already set
if 'start_date' not in st.session_state or 'end_date' not in st.session_state:
    st.session_state['end_date'] = datetime.date.today()
    st.session_state['start_date'] = st.session_state['end_date'] - datetime.timedelta(days=7)


# Initialize session state for price history if not already set
expected_columns_price_history = ['isin', 'date', 'price']
if 'price_history' not in st.session_state:
    isins = st.session_state.companies['isin'].tolist()
    price_history_df = get_price_history_cached(isins, st.session_state['start_date'], st.session_state['end_date'])
    
    # Check if the DataFrame is empty or if the ISINs list was empty, and set the structure
    if price_history_df.empty or not isins:
        st.session_state.price_history = pd.DataFrame(columns=expected_columns_price_history)
    else:
        st.session_state.price_history = price_history_df

def plotGraph(start_price_date,end_price_date):
    try:
        isins = st.session_state.companies['isin'].tolist()
        st.session_state.price_history = get_price_history_cached(isins, start_price_date, end_price_date)
        company_names = st.session_state.companies['asset_name'].dropna().unique().tolist()  # Use asset_name column for company names
        selected_company_names = st.multiselect("Select Companies to Plot:", options=company_names, default=company_names)
        
        # Map selected company names back to their ISINs to filter the price history
        selected_isins = st.session_state.companies[st.session_state.companies['asset_name'].isin(selected_company_names)]['isin'].tolist()

        # Merge the filtered price history with the companies DataFrame to get asset names
        if selected_isins:
            filtered_price_history = st.session_state.price_history[st.session_state.price_history['isin'].isin(selected_isins)]
            filtered_price_history = filtered_price_history.merge(st.session_state.companies[['isin', 'asset_name']], on='isin', how='left')
            
            if not filtered_price_history.empty:
                # Use 'asset_name' for the color distinction in the plot instead of 'isin'
                fig = px.line(filtered_price_history, x='date', y='price', color='asset_name', title='Price Trends', labels={'asset_name': 'Company Name'})
                st.plotly_chart(fig)
            else:
                st.warning("No price history available for the selected companies.")
        else:
            st.warning("Please select at least one company to plot the price trends.")
    except NameError:
        st.warning("Set assets to track.")

# UI 
st.title("Dashboard")

# Radio button to choose the purpose of CSV upload
csv_purpose = st.radio("Choose the purpose of the CSV file:",('Add Companies to Track', 'Batch Update Prices'))

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    process_uploaded_file(uploaded_file, csv_purpose)

# 3. Price change plot with Plotly for better interactivity
st.header("Gradient Plot Section")
lookback_window = st.slider("Lookback Window (Days)", min_value=1, max_value=30, value=7)
start_price_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=lookback_window))
end_price_date = st.date_input("End Date", value=datetime.date.today())

# Update session state based on user input
st.session_state['start_date'] = start_price_date
st.session_state['end_date'] = end_price_date

plotGraph(start_price_date,end_price_date)


# 4. Flag section 
st.header("Flag Section")
flag_lookback = st.number_input("Flag Lookback Window (Days)", min_value=2, max_value=30, value=6, key="flag_lookback")
flag_threshold = st.number_input("Flag Threshold (%)", min_value=0.1, max_value=20.0, value=1.0, step=0.1, key="flag_threshold")

# Fetch fresh price history for the flag_lookback period
start_date_flag_section = datetime.date.today() - datetime.timedelta(days=flag_lookback)
end_date_flag_section = datetime.date.today()
isins_flag_section = st.session_state.companies['isin'].tolist()
price_history_flag_section = get_price_history_cached(isins_flag_section, start_date_flag_section, end_date_flag_section)

# Calculate price changes
price_changes = calculate_largest_contiguous_change(price_history_flag_section, flag_lookback)
flagged_companies = price_changes[price_changes['price_change_pct'].abs() >= flag_threshold]

flagged_with_names = pd.merge(flagged_companies, st.session_state.companies[['isin', 'asset_name']], on='isin', how='left')

# Select only the required columns to display
flagged_display = flagged_with_names[['asset_name', 'price_change_pct']]
# Define the color formatting function
def color_format(val):
    color = 'green' if val > 0 else 'red'
    return f'color: {color}'

# Apply the color formatting and round off the 'price_change_pct' column
flagged_display_styled = flagged_display.style.map(color_format, subset=['price_change_pct']).format({'price_change_pct': '{:.2f}%'})

# Display the styled DataFrame
if not flagged_display.empty:
    st.dataframe(flagged_display_styled, use_container_width=True)
else:
    st.write("No companies exceed the specified threshold.")

# Generate report button

def generate_and_display_report():
    # Define start and end dates for the report
    start_date = datetime.date.today() - datetime.timedelta(days=st.session_state['report_lookback'])
    end_date = datetime.date.today()

    merged_sentiments_df = reportHelper(start_date,end_date)

    # Calculate the largest contiguous price change
    price_changes_df = calculate_largest_contiguous_change(st.session_state.price_history, st.session_state['report_lookback'])

    # Merge the sentiments with price changes and asset information
    final_report_df = pd.merge(merged_sentiments_df, price_changes_df, on='isin')

    # Filter to only show the desired columns
    final_report_df = final_report_df[['asset_name', 'price_change_pct', 'extracted_sentiment', 'source_links', 'sentiment_type']].drop_duplicates()
    final_report_df = final_report_df[
    (final_report_df['price_change_pct'] > st.session_state['report_threshold']) |
    (final_report_df['price_change_pct'] < -st.session_state['report_threshold'])]

    # Display the final report on the page
    st.dataframe(final_report_df)

    # Convert the final report to CSV for downloading
    csv = final_report_df.to_csv(index=False)
    st.session_state['report_csv'] = csv

    # Display download button
    st.download_button(label="Download Report", data=st.session_state['report_csv'], file_name="report.csv", mime="text/csv")


st.header("Generate Report")
st.number_input("Report Lookback Window (Days)", min_value=2, max_value=30, value=3, key="report_lookback")
st.number_input("Report Threshold (%)", min_value=0.1, max_value=20.0, value=1.0, step=0.1, key="report_threshold")

if st.button("Generate and Download Report"):
    generate_and_display_report()