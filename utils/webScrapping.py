from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from concurrent.futures import ThreadPoolExecutor, as_completed
import json

def setup_driver():
    # Configure options for headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ensure GUI is off
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Path to chromedriver executable
    driver = webdriver.Chrome(options=chrome_options)

    return driver

def scrape_url(url):
    driver = setup_driver()
    try:
        driver.get(url)
        # Wait for the page to load and read the content
        content = driver.page_source
        # Extract relevant text using Selenium's find_elements function
        # Adjust the selector as per your requirements to target the main content
        elements = driver.find_elements(By.TAG_NAME, 'p')
        article_text = ' '.join([element.text for element in elements])
        print(f"debugger articles: {article_text}")
        return article_text
    except:
        print(f"Timed out waiting for page to load: {url}")
        return None
    finally:
        driver.quit()


