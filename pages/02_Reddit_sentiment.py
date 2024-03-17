import streamlit as st
import matplotlib.pyplot as plt


from utils.llm import get_completionCustom
from utils.Reddit import search_Reddit
from utils.systemPrompts import sysPromptSentimentPost

import tqdm
# Processing the post
def process_post(post):
    try:
        if post["Contents"] == "":
            pressData = f'{post["Title"]}'
        else:
            pressData = f"""
            Title: {post["Title"]}
            Contents: {post["Contents"]}
            """

        sentiment = get_completionCustom(
            messages=[
                {"role": "system", "content": sysPromptSentimentPost(company_name)},
                {"role": "user", "content": pressData}
            ]
        )

        return sentiment
    except Exception as e:
        # Handle any other unexpected exceptions
        return "IRRELEVANT"


# Draw pie chart
def draw_pie_chart(sentiments, company_name):
    sizes = list(sentiments.values())
    labels = list(sentiments.keys())
    colors = ['#ff9999', '#66b3ff', '#99ff99']  # Custom colors

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, shadow=True, explode=(0, 0, 0), textprops={'color': "black"})
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    ax.set_title(f'Public Sentiment Analysis of {company_name}', color='black', pad=20)
        
    st.pyplot(fig)




# Streamlit UI
st.title("Public Sentiment Search from Reddit")
company_name = st.text_input("Enter a company name:", "")
# Change the company_name to uppercase at the beginning of each word
company_name = company_name.title()


if st.button("Search"):
    st.session_state.pressDataSummaryOverall = []  # Reset the session state for a new search
    if company_name:

        progress_text = st.empty()
        
        progress_pic = st.empty()
        
        progress_text.markdown(f"Processed Sentiment Analysis of **{company_name}** from Reddit. Please wait...")

        
        Full_posts = search_Reddit(company_name, 'week')
        
        progress_bar = st.progress(0)  # Create a progress bar
        
        Sentiment_collect = {'SUPER NEGATIVE': 0, 'NEGATIVE': 0, 'NEUTRAL': 0, 'POSITIVE': 0, 'SUPER POSITIVE': 0}

        # Iterate over Full_posts with tqdm for progress display
        for i, post in enumerate(tqdm.tqdm(Full_posts, desc="Processing posts")):
            sentiment = process_post(post)
            if sentiment in Sentiment_collect.keys():
                Sentiment_collect[sentiment] += int(post["Score"])
            
            # Update progress bar
            progress_bar.progress((i + 1) / len(Full_posts))
        
        Sentiment_graph = {'Negative': Sentiment_collect['SUPER NEGATIVE'] + Sentiment_collect['NEGATIVE'], 
                     'Neutral': Sentiment_collect['NEUTRAL'], 
                     'Positive': Sentiment_collect['SUPER POSITIVE'] + Sentiment_collect['POSITIVE']}
        
        draw_pie_chart(Sentiment_graph, company_name)

    else:
        st.warning("Please enter a company name to search.")