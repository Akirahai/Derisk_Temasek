import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import pandas as pd

from utils.processingSentiments import sentiment_for_company

# Initialize session state for storing sentiments and selected ISIN
if 'sentiments' not in st.session_state:
    st.session_state.sentiments = None
if 'searchPageIsin' not in st.session_state:
    st.session_state.searchPageIsin = None

# Streamlit UI
st.title("News Search")

# Radio button to choose between searching tracking assets or new assets
search_option = st.radio("Search option:", ('Search for Tracking Asset', 'Search New'))

if search_option == 'Search for Tracking Asset':
    # Dropdown to select an asset from tracking assets
    company_names = st.session_state.companies['asset_name'].dropna().unique().tolist()
    selected_company_name = st.selectbox("Select an asset:", company_names)
    company_name = selected_company_name
    # Update searchPageIsin with the selected company's ISIN
    st.session_state.searchPageIsin = st.session_state.companies[st.session_state.companies['asset_name'] == selected_company_name]['isin'].iloc[0]
else:
    # Text input for entering a new asset name
    company_name = st.text_input("Enter a new asset name:", "")

# User input for the number of articles to process
numberOfArticles = st.number_input("Number of articles to process:", min_value=1, value=20, step=1)

if st.button('Search'):
    # Determine if we need to update the database based on the selection
    update_db = search_option == 'Search for Tracking Asset'
    isin = st.session_state.searchPageIsin if update_db else None

    # Perform the sentiment search
    sentiments = sentiment_for_company(isin=isin, numberOfArticles=numberOfArticles, company_name=company_name, updateDB=update_db)
    st.session_state.sentiments = sentiments

# Display the sentiments if available
if st.session_state.sentiments is not None: 
    positive_df, negative_df = st.session_state.sentiments

    # Display Positive Sentiments in a Table
    st.subheader("Positive Insight")
    if positive_df is not None:
        # Rename columns for display
        positive_df_display = positive_df.rename(columns={"Sentiment": "Insight", "Weight": "Corroboration Frequency"})
        st.table(positive_df_display[['Insight', 'Corroboration Frequency']].style.format({'Corroboration Frequency': "{:.2f}"}))
    else: 
        st.write("No positive Insights")
            
    # Display Negative Sentiments in a Table
    st.subheader("Negative Insights")
    if negative_df is not None:
        # Rename columns for display
        negative_df_display = negative_df.rename(columns={"Sentiment": "Insight", "Weight": "Corroboration Frequency"})
        st.table(negative_df_display[['Insight', 'Corroboration Frequency']].style.format({'Corroboration Frequency': "{:.2f}"}))
    else: 
        st.write("No negative Insight")
else:
    st.warning("Please enter an asset name to search.")
