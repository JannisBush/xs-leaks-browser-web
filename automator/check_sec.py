import os
import time

from get_local_grid import BrowserGrid

def get_inc():
    """Return a list of inclusion methots.
       To make sense of them refer to the leaker-service.
    """
    inc = [
        "script",
        "link-stylesheet",
        "link-prefetch",
        "img",
        "iframe",
        "video",
        "audio",
        "object",
        "embed",
        "embed-img",
        "window.open",
    ]
    return inc

def test_browsers(browsers, check_url):
    caps = browsers.get_caps()
    for browser_number, cap_key in enumerate(caps.keys()):
        print(cap_key)
        driver = browsers.get_driver(cap_key)
        driver_caps = driver.capabilities
        browser = driver_caps.get("browserName")
        version = driver_caps.get("browserVersion")
        driver.get(f"{SET_URL}/leaks/set_cookies/")
        print(driver.get_cookies())
        for inc in get_inc():
            driver.get(f"{CROSS_URL}/apg/test/{inc}/?browser={browser}&version={version}&url={check_url}")
            time.sleep(1)
        driver.quit()



if __name__ == "__main__":
    browsers = BrowserGrid()

    CROSS_URL = os.getenv("CROSS_URL", "http://172.17.0.1:8001")
    SET_URL = os.getenv("SET_URL", "https://172.17.0.1:44300")
    check_url = f"{SET_URL}/leaks/check_cookies/"

    test_browsers(browsers, check_url)
