# google_search_api_wrapper.py
import os
import requests
from utils.database import check_url_in_sentiment_sources 

def search_financial_news(query, days_ago=1, k=30):
    results = []
    start_index = 1
    total_results_needed = k
    max_results_per_page = 10

    while total_results_needed > 0:
        num_results = min(total_results_needed, max_results_per_page)
        params = {
            "key": os.getenv("GOOGLE_SEARCH_API_KEY_BACKUP"),
            "cx": os.getenv("GOOGLE_SEARCH_ENG_ID_BACKUP"),
            "q": f"{query} Financial News inurl:news OR inurl:article",
            "dateRestrict": f"d{days_ago}",
            "start": start_index,
            "num": num_results
        }

        endpoint = "https://www.googleapis.com/customsearch/v1"
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])

        for item in items:
            link = item.get('link')
            if check_url_in_sentiment_sources(link) == 0:
                results.append((item['title'],item['link']))

        total_results_needed -= len(items)
        start_index += len(items)

        if not items or "nextPage" not in data.get("queries", {}):
            break
    return results
