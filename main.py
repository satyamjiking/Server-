import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def load_cookies(driver, cookies_file):
    with open(cookies_file, "r") as f:
        cookies = json.load(f)
    for cookie in cookies:
        driver.add_cookie(cookie)

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    # Step 1: Facebook login page open karo
    driver.get("https://www.facebook.com")
    time.sleep(3)

    # Step 2: cookie.json load karo
    try:
        load_cookies(driver, "cookie.json")
        driver.refresh()
        time.sleep(5)
    except Exception as e:
        print("[ERROR] Cookie load nahi ho payi:", e)
        driver.quit()
        return

    # Step 3: check login success
    if "facebook.com" in driver.current_url:
        print("[BOT] ✅ Login Success!")
    else:
        print("[BOT] ❌ Login Failed!")

    driver.quit()

if __name__ == "__main__":
    main()
