import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# env load
load_dotenv()

FB_USER = os.getenv("FB_USER")
FB_PASS = os.getenv("FB_PASS")
TARGET_ID = os.getenv("TARGET_ID")

if not FB_USER or not FB_PASS or not TARGET_ID:
    print("[ERROR] Missing FB_USER / FB_PASS / TARGET_ID in environment.")
    exit(1)

# file.txt read
def load_message():
    if os.path.exists("file.txt"):
        with open("file.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Default test message"

def start_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # Railway पर chromium का default path
    chrome_options.binary_location = "/usr/bin/chromium"

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def main():
    msg = load_message()
    print("📄 File.txt content loaded:", msg
