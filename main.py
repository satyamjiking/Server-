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
    print("📄 File.txt content loaded:", msg)

    driver = start_browser()

    try:
        # Facebook login page
        driver.get("https://mbasic.facebook.com/login")
        time.sleep(2)

        # login
        driver.find_element("name", "email").send_keys(FB_USER)
        driver.find_element("name", "pass").send_keys(FB_PASS)
        driver.find_element("name", "login").click()
        time.sleep(3)

        print("✅ Logged in")

        # target chat open
        chat_url = f"https://mbasic.facebook.com/messages/read/?tid=cid.c.{TARGET_ID}"
        driver.get(chat_url)
        time.sleep(2)

        # send message
        textarea = driver.find_element("name", "body")
        textarea.send_keys(msg)
        driver.find_element("name", "send").click()
        time.sleep(2)

        print("📨 Message sent successfully!")

    except Exception as e:
        print("❌ Error:", e)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
