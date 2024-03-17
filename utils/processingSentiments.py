import streamlit as st
import concurrent.futures
import time
import asyncio
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.llm import get_completionCustom
from utils.systemPrompts import compare_and_mergeSentimentsSysPrompt
from utils.googleSearch import search_financial_news
from utils.webScrapping import scrape_url
from utils.systemPrompts import sysPromptSummariseArticle
from utils.database import insert_sentiments_and_sources , get_company_id_by_name , get_company_id_by_isin

class UnionFind:
    def __init__(self, size):
        self.root = [i for i in range(size)]
        self.rank = [1] * size

    def find(self, x):
        if x == self.root[x]:
            return x
        self.root[x] = self.find(self.root[x])
        return self.root[x]

    def union(self, x, y):
        rootX = self.find(x)
        rootY = self.find(y)
        if rootX != rootY:
            if self.rank[rootX] > self.rank[rootY]:
                self.root[rootY] = rootX
            elif self.rank[rootX] < self.rank[rootY]:
                self.root[rootX] = rootY
            else:
                self.root[rootY] = rootX
                self.rank[rootX] += 1

def process_sentiment_array(sentiment_array, batch_size=10, sleep_duration=1):
    print(f'Debugging check: beginning article compare: {sentiment_array}')  
    n = len(sentiment_array)
    uf = UnionFind(n)

    # Prepare and execute comparison tasks in batches
    tasks = [(i, j, sentiment_array[i], sentiment_array[j]) for i in range(n) for j in range(i + 1, n)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
        for batch_start in range(0, len(tasks), batch_size):
            batch = tasks[batch_start:batch_start + batch_size]
            futures = {executor.submit(compare_and_merge, *task): task[:2] for task in batch}
            for future in concurrent.futures.as_completed(futures):
                i, j, result = future.result()
                if result:
                    uf.union(i, j)
            time.sleep(sleep_duration)  # Sleep to mitigate potential rate limiting

    # Aggregate sentiments into groups based on Union-Find roots
    groups = {}
    for i in range(n):
        root = uf.find(i)
        if root not in groups:
            groups[root] = {'sentiment': sentiment_array[i]['sentiment'], 'sources': set()}
        groups[root]['sources'].update(sentiment_array[i]['sources'])


    # Compile the final list with one sentiment representing each group
    merged_sentiments = [{'sentiment': group['sentiment'], 'sources': list(group['sources'])} for group in groups.values()]
    print(f'Debugging check: completing article compare: {sentiment_array}')  
    return merged_sentiments


def compare_and_merge(i, j, sentiment1, sentiment2):
    result = get_completionCustom(
        messages=[
            {"role": "system", "content": f"{compare_and_mergeSentimentsSysPrompt}"},
            {"role": "user", "content": f"{[sentiment1['sentiment'],sentiment2['sentiment']]}"}
        ]
    )
    if result == "1":
        return i, j, True
    return i, j, False

def process_article(company_name,url):
    print(f'Debugging check: starting article scrape: {company_name} {url}')  
    pressData = scrape_url(url)
    if pressData:
        print(f'Debugging check: getting article summary: {company_name} {url}')  
        summary = get_completionCustom(
            messages=[
                {"role": "system", "content": sysPromptSummariseArticle(company_name)},
                {"role": "user", "content": pressData}
            ]
        )
        if summary != "IRRELEVANT":
            parsed_summary = json.loads(summary)
            parsed_summary['url'] = url
            print(f'Debugging check: returning article summary: {company_name} {url}')  
            return parsed_summary

def sentiment_for_company(isin,company_name,Lookback=1,numberOfArticles=30,updateDB=True):

    print(f'Debugging check: staring processing for {isin} {company_name}')

    search_results = search_financial_news(company_name,Lookback, numberOfArticles)

    print(f'Debugging check: completed search news {isin} {company_name}')
    print(f'Debugging check: completed search news results: \n {search_results}')  

    companyIDByisin = get_company_id_by_isin(isin) 
    companyIDByname = get_company_id_by_name(company_name) 

    summaryResults = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_article,company_name,url) for _, url in search_results]
        summaryResults = [future.result() for future in as_completed(futures)]
    
    postitiveArray = []
    negativeArray = [] 
    for article in summaryResults: 
        if article:
            source = article['url']
            for posSentiment in article["Positive"]: 
                postitiveArray.append({"sentiment": posSentiment, 'sources': [source]})
            for negSentiment in article["Negative"]: 
                negativeArray.append({"sentiment": negSentiment, 'sources': [source]})

    positiveMerged = process_sentiment_array(postitiveArray)
    negativeMerged = process_sentiment_array(negativeArray)

    print(positiveMerged)
    print(negativeMerged)
    print(f'Debugging check: completed extracting positive sent: \n {positiveMerged}')
    print(f'Debugging check: completed extracting negative sent: \n {negativeMerged}')  

    noOfvalidArticles = len(summaryResults)

    if updateDB:
        # print(f'Debugging check: attempting to update db for {isin} {company_name}')  
        if companyIDByisin is not None:
            insert_sentiments_and_sources(companyIDByisin,positiveMerged,1)
            insert_sentiments_and_sources(companyIDByisin,negativeMerged,0)
        elif companyIDByname is not None:
            insert_sentiments_and_sources(companyIDByname,positiveMerged,1)
            insert_sentiments_and_sources(companyIDByname,negativeMerged,0)

    if positiveMerged != []:
        for sentiment in positiveMerged: 
            weight = len(sentiment["sources"]) / noOfvalidArticles
            sentiment["weight"] = weight
        positive_df = pd.DataFrame(positiveMerged)
        positive_df = positive_df.rename(columns={"sentiment": "Sentiment", "weight": "Weight"})
        positive_df = positive_df.sort_values(by='Weight', ascending=False)
    else: 
        positive_df = None 
        
    if negativeMerged != []:
        for sentiment in negativeMerged: 
            weight = len(sentiment["sources"]) / noOfvalidArticles
            sentiment["weight"] = weight
        negative_df = pd.DataFrame(negativeMerged)
        negative_df = negative_df.rename(columns={"sentiment": "Sentiment", "weight": "Weight"})
        negative_df = negative_df.sort_values(by='Weight', ascending=False)
    else: 
        negative_df = None 
    return positive_df , negative_df