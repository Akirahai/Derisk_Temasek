import praw

from utils.llm import get_completionCustom
from utils.systemPrompts import sysPromptSentimentPost

def search_Reddit(company_name, time):
    
    # Reddit API credentials
    reddit = praw.Reddit(client_id='0Ezl3E3RfWWZ32I3jcNJbA',
                        client_secret='JjZGW70-dbtnF9GNgXTPv2tYeFByIw',
                        user_agent='checking_company')

    # Subreddit to search
    subreddit_name = "all"

    # Search query
    search_query = company_name

    # Search posts within the specified time range
    posts = reddit.subreddit(subreddit_name).search(search_query, time_filter = time, sort='top')

    Full_posts = []
    for post in posts:
        p = {}
        p["Title"] =  post.title
        p["URL"] = post.url
        p["Score"] = post.score
        p["Contents"] = post.selftext
        Full_posts.append(p)
    
    return Full_posts

