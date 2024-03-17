# Derisk: Stock Market Research

## Objective
How can GenAI help us to explain the big “why” behind stock price movement based on company related news?​ 

Looking to decode the mysterious movements of stock prices? Say hello to our latest innovation: Derisk, a GenAI innovation for stock market research.

Gone are the days of tirelessly scouring through endless news articles and Reddit threads to understand why a company's stock price is on the move. With GenAI Stock Insights, we've revolutionized the process, making it easier and more efficient than ever before.


## Prerequisites
1. Python>=3.9 is recommended
1. Azure Open AI access key


## Setup
1. Clone this repository
    ```
    git clone https://github.com/Akirahai/Derisk_Temasek.git
    ```
1. Create a virtual environment 
    ```
    python -m venv venv
    ```
1. Activate virtual environment 
    * On Mac machine or WSL on Windows
    ```
    source venv/bin/activate 
    ```   
    * On Windows machine (if not using WSL)
    ```
    .\venv\Scripts\activate
    ```
1. Install packages 
    ```
    pip install -r requirements.txt
    ```
1. [Optional] Additional installations required for `openai-whisper` and `pydub` - `ffmpeg` and `rust`. 
    - See the README at https://github.com/openai/whisper
    - Feel free to skip this if there are no requirements to process audio or video files
1. Setup environment variables. Replace the environment variables in `.env` with the values that will be provided
    ```
    cp -i .env.example .env
    ```

## Run
1. On subsequent runs, do remember to activate virtual environment 
1. Run app
    ```
    streamlit run dashboard.py
    ```

## Working diagram explaination

1. Upload Your Data: Simply upload a CSV file containing sets of components and their time-series stock prices. Our system takes care of the rest.

2. Dynamic Visualization: Watch as we transform raw data into dynamic visualizations, showing the fluctuations in stock prices over time. It's like watching the heartbeat of the market come to life.

3. GenAI Summarization: Our GenAI engine combs through vast amounts of public and media trends, summarizing the key insights behind the stock movements. No stone is left unturned as we uncover the underlying factors driving the market.

4. Reddit Sentiment Analysis: Wondering what the Reddit community has to say about the company you're interested in? GenAI analyzes sentiment from Reddit discussions, providing valuable insights into public perception.

5. Downloadable Reports Once we've gathered all the data and generated insights, you can easily download them for further analysis or sharing with your team.

With Derisk, decoding stock market mysteries has never been easier. Say goodbye to guesswork and hello to data-driven decision-making. Ready to take your stock analysis to the next level? Try Derisk today!

## Product Demo

[![Derisk](https://img.youtube.com/vi/PXKkQn0AjSM/0.jpg)](https://www.youtube.com/watch?v=PXKkQn0AjSM "Derisk: GenAI Innovation for Stock Market Research")