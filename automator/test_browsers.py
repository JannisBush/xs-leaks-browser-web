import sys
import os
import json
import redis
import requests
import time
import random
import logging
import datetime
import pickle
import traceback
import numpy as np

from pathlib import Path
from tqdm import tqdm
from multiprocessing.pool import Pool as Pool
from multiprocessing import Queue
from logging.handlers import QueueListener, QueueHandler

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from selenium.webdriver.support import expected_conditions as EC

from get_browserstack import BrowserStack
from get_local_grid import BrowserGrid
# from get_local_tor import BrowserTor  # Currently does not support Selenium 4, which is required by other components
from get_local_chrome import BrowserChrome

#### Helper class ####
class Timeout(object):
    def __init__(self, seconds):
        """Specifiy `seconds` and the code executed in a with-
           block will throw a TimeoutError after `seconds` seconds."""
        self.seconds_before_timeout = seconds
        self.original_trace_function = None
        self.end_time = None

    # Tracing function
    def check_time(self, frame, event, arg):
        if self.original_trace_function is not None:
            self.original_trace_function(frame, event, arg)

        current_time = time.time()
        # Throw a TimeoutError if timed out
        if current_time >= self.end_time:
            raise TimeoutException("Own specified timeout!")

        return self.check_time

    # Begin of `with` block
    def __enter__(self):
        start_time = time.time()
        self.end_time = start_time + self.seconds_before_timeout

        self.original_trace_function = sys.gettrace()
        sys.settrace(self.check_time)
        return self

    # End of `with` block
    def __exit__(self, exc_type, exc_value, tb):
        self.cancel()

        if exc_type is None:
            return

        # Return False to pass the TimeoutError to
        # outer scope (if error occured)
        return False

    def cancel(self):
        sys.settrace(self.original_trace_function)
#### End ####


def get_url_range(url_step):
    """Return the URL range to be tested.
       To make sense of them refer to the leaky-service.
       Default: 
    """
    start = START_URL_NUMBER
    end = start + URL_COUNT
    return range(start, end, url_step)


def get_inc():
    """Return a list of inclusion methots.
       To make sense of them refer to the leaker-service.
    """
    inc = [
        #"script",
        #"link-stylesheet",
        #"link-prefetch",
        #"img",
        #"iframe",
        #"video",
        #"audio",
        #"object",
        #"embed",
        #"embed-img",
        "window.open",
        #"iframe-csp",
    ]
    return inc


def get_urls(url_list=None, url_step=1):
    """Return all URLs that should be tested.
       Made up from the url_range and the inclusion_methods.
    """
    urls = []
    if url_list is None:
        for num in get_url_range(url_step):
            for inc_method in get_inc():
                url = f"{APG_URL}/{inc_method}/?url={BASE_URL}/leaks/{num}/noauth/"
                #url = f"{APG_URL}/{inc_method}/?url={BASE_URL}/echo/?cross-origin-opener-policy=same-origin"
                #url = f"{APG_URL}/{inc_method}/?url={BASE_URL}/echo/?content-disposition=attachment"
                #url = f"{APG_URL}/{inc_method}/?url={BASE_URL}/echo/?ecocnt_html=input_id=test1"
                urls.append(url)
    else:
        for entry in url_list:
            url = f"{APG_URL}/{entry['inc_method']}/?url={BASE_URL}/leaks/{entry['url_id']}/noauth/"
            urls.append(url)

    return urls


def get_browser_info(caps, cap_key, log):
    # Get the wanted Browser specs            
    headless = False  # By default non-headless
    browser = "Unknown"
    if type(caps[cap_key]) == dict:
        sys.exit(
            "DesiredCapabilities/Selenium 3 is not supported, use Options() and Selenium 4")
        # browser = caps[cap_key].get("browserName", "unspecified")
        # logger.info(caps[cap_key])
    else:
        browser = caps[cap_key].__dict__[
            "_caps"].get("browserName", "unspecified")
        # If headless is specified, use a headless browser instead
        if any(headless in caps[cap_key].__dict__.get("_arguments") for headless in ["--headless", "-headless"]):
            headless = True
        if log:
            logger.info(caps[cap_key].__dict__)
    return browser, headless


def test_browsers(browsers, timeout_page_load, timeout_page_execute, wait_time, display_progress, login, url_dict, url_step, retest):
    """Test the given browsers.

    browsers: Instance of BrowserClass
    timeout_page_load: (int) Time in seconds a page is allowed to load (load event fired)
    timeout_page_execute: (int) Time in seconds the page is allowed to execute (starts after loading)
    wait_time: (int) Time in milliseconds a page should wait for postMessages etc
    display_progress: (bool) Whether each browser instance should display progess using tqdm
    login: (bool) Whether to login before testing or not
    url_dict: (dict/None) If not None is a dictionary of URLs to test for different browsers
    url_step: (int) Steps between the URL-ids, (important for MODE=retest)
    retest: (bool) Whether we are in retest mode
    """
    # Get the capabilities (list of wanted browsers)
    caps = browsers.get_caps()
    # Specify how many browsers instances we can open concurrently
    max_concurrency = browsers.get_parallel_limit()
    # How many different browsers are included in the capabilities
    num_browsers = len(caps.keys())
    # Start as many processes as allowed, collect all jobs in a list
    pool = Pool(max_concurrency)
    jobs = []
    
    if url_dict is None:  
        # Get all the urls to test this run
        urls = get_urls(url_step=url_step)
        # optionally shuffle the list to better distribute the load?
        # random.shuffle(urls)

        # Currently only works if all browsers have the same parallel_limit!
        # (Reason: Faster as only created/splitted urls once)
        # (Enhancement: check for this and do something else if not true?)
        cap_currency = max_concurrency  # browsers.get_parallel_limit_cap(cap_key)

        # Split the urls into equal chunks of 500 URLs each
        chunk_size = 100 #500
        url_chunks = [urls[i * chunk_size:(i + 1) * chunk_size]
                    for i in range((len(urls) + chunk_size - 1) // chunk_size)]

        # Create all jobs (url_chunks * browser)
        for chunk_number, url_chunk in enumerate(url_chunks):
            for browser_number, cap_key in enumerate(caps.keys()):
                browser, headless = get_browser_info(caps, cap_key, not chunk_number)
                # All job information, last parameter is the position argument for tqdm
                jobs.append([browsers, browser, cap_key, url_chunk, timeout_page_load,
                            timeout_page_execute, wait_time, (chunk_number * num_browsers) + browser_number + 1, display_progress, login, headless, retest])
    else:
        for browser_number, cap_key in enumerate(caps.keys()):
            browser, headless = get_browser_info(caps, cap_key, True)
            urls_browser = url_dict.get(browser)
            urls = get_urls(urls_browser)
            # Split the urls into equal chunks of 500 URLs each
            chunk_size = 100  #500
            url_chunks = [urls[i * chunk_size:(i + 1) * chunk_size]
                    for i in range((len(urls) + chunk_size - 1) // chunk_size)]

            # Create all jobs url_chunks
            for chunk_number, url_chunk in enumerate(url_chunks):
                # All job information, last parameter is the position argument for tqdm
                jobs.append([browsers, browser, cap_key, url_chunk, timeout_page_load,
                        timeout_page_execute, wait_time, (chunk_number * num_browsers) + browser_number + 1, display_progress, login, headless, retest])


    # Start all jobs using imap_unorded and log the results using tqdm
    result = list(tqdm(pool.imap_unordered(run_session_unpack, jobs),
                  total=len(jobs), desc="Total", position=0, mininterval=1))
    logger.info(result)


def run_session_unpack(args):
    """Helper function to simulate starmap.
    """
    return run_session(*args)


def run_session(browsers, browser, cap_key, urls, timeout_page_load, timeout_page_execute, wait_time, pos, display_progress, cookies, headless, retest, site="", max_try_num=1, restart_num=0):
    """Test all urls for the current browser. (Restarts if an error occured before all urls where tested.)

    browsers: Instance of Browsers
    browser: (str) Name of the currently tested browser
    cap_key: (int) Dictionary key to get to correct capability for the wanted browser from browsers
    urls: (array) List of urls this session should test
    timeout_page_load: (int) seconds a page is allowed to load
    timeout_page_execute: (int) seconds a page is allowed to execute after load
    wait_time: (int) milliseconds a page should wait for postMessages etc.
    pos: (int) pos argument of tqdm to display the progress bar correctly
    display_progress: (bool) whether to display the progress bar or not
    cookies: (bool) whether the driver should add cookies to the driver or not
    headless: (bool) whether the current browser is requested as headless or not
    retest: (bool) whether we are in retest mode or (int) in dynamic confirmation mode: how often have we already tested this
    site: (str) site to test, retrieve cookies from redis (default: "")
    max_try_num: (int) how often a URL should be tried (default: 1)
    restart_num: (int) how often the browser already restarted
    """
    assert (type(retest) == bool) or ((type(retest) == int) and (site != ""))
    # Set vars and log info
    start_time = time.time()
    urls_to_test = len(urls)
    tested_urls = 0
    url = None
    driver = None
    login_failed = False
    logger.info(f"Started {browser}{pos}, {urls_to_test} urls to test")

    # Everthing in a try/catch block to close the driver/browser if an error occurs
    try:
        # Get and configure the driver
        driver = browsers.get_driver(cap_key)
        driver.set_page_load_timeout(timeout_page_load)
        driver_caps = driver.capabilities
        actual_browser = driver_caps.get("browserName")
        version = driver_caps.get("browserVersion")
        if version is None:
            # Some browsers (e.g., opera name the version capability differently)
            version = driver_caps.get("version")
        # The name of the requested browser and the returned browser to not match, warn
        if browser != actual_browser:
            logger.warning(
                f"Mismatch: desired browser {browser}, actual browser {actual_browser}")
        browser = actual_browser

        # Try to login if necessary
        if cookies:
            try:
                add_cookies_driver(driver, browser, site)
            except Exception as e:
                logger.error(f"Add cookies for {site} in {browser} failed because {traceback.format_exc()}. Abort.")
                login_failed = True
                return (cap_key, 0, time.time() - start_time)

        # Test all urls
        for url in tqdm(urls, desc=f"{browser}{pos}", position=(pos % 10) + 1, miniters=5, leave=False) if display_progress else urls:
            test_url(driver, url, timeout_page_execute,
                     browser, version, wait_time, pos, headless, retest, cookies, site, max_try_num=max_try_num)
            tested_urls += 1

    # Catch and log everthing that went wrong
    except Exception as e:
        logger.error(f"{browser}{pos}: error: {e}, last url: {url}")
    finally:
        took = time.time() - start_time
        # In the end close the driver
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"Driver couldn't quit {e}")

        # Restart browser if not all urls are tested yet
        if urls_to_test != tested_urls:
            time.sleep(1)
            if login_failed and restart_num >= 2:
                logger.error(f"Do not restart {browser}{pos}: failed login to often")
                return (cap_key, tested_urls, took)
            else:
                logger.error(
                f"Restart {browser}{pos} because error? tested {tested_urls}, should have tested {urls_to_test}. Took: {took} seconds.")
                cap_key, tested_later, took_later = run_session(browsers, browser, cap_key, urls[tested_urls:], timeout_page_load, timeout_page_execute, wait_time, pos, display_progress, cookies, headless, retest, site, max_try_num, restart_num=restart_num+1)
                return (cap_key, tested_urls + tested_later, took + took_later)
        # Otherwise we are finished
        else:
            logger.info(
                f"{browser}{pos} finished; tested {tested_urls} urls. Took: {took} seconds.")
            return (cap_key, tested_urls, took)


def test_url(driver, url, timeout_page_execute, browser, version, wait_time, pos, headless, retest, cookies, site, try_num=1, max_try_num=1):
    """Test one url.

    driver: Selenium browser driver
    url: (str) url to test
    timeout_page_execute: (int) seconds the page is allowed to execute after load
    browser: (str) name of the current browser
    version: (str) version info
    wait_time: (int) milliseconds a page is allowed to wait for postMessages etc.
    pos: (int)
    headless: (bool)
    retest: (bool) or (int)
    cookies: (bool)
    site: (str)
    try_num: (int) number of tries for the current URL (default: 1)
    max_try_num: (int) how often a URL should be tested before giving up (default: 1)
    """
    # Add dynamic info to the url
    if type(retest) == bool:
        url = f"{url}&browser={browser}&version={version}&wait_time={wait_time}&headless={headless}{'&retest=True' if retest else '&retest=False'}"
    elif type(retest) == int:
        url = f"{url}&browser={browser}&version={version}&wait_time={wait_time}&headless={headless}&retest={retest}{'&cookies=True' if cookies else '&cookies=False'}&site={site}"
    else:
        sys.exit("Invalid type of retest")
    logger.debug(f"{browser}:{pos} testing {url}")
    # Load url for max given time
    try:
        # Additional Timeout to catch hanging browsers that are not catched by Selenium itself
        with Timeout(timeout_page_execute*3):
            # logger.error(f"{browser}:{url}, {driver.get_cookies()}")
            driver.get(url)
            # logger.error(f"{browser}:{url}, {driver.get_cookies()}")
            # Page execution is finished if the title is set to "Information"
            WebDriverWait(driver, timeout_page_execute).until(
                EC.title_contains("Information"),
                message=f"Title is: {driver.title}")

            # Regain focus, if focus was lost due to ID attribute leak
            driver.execute_script("window.focus();")

            org_window = driver.current_window_handle

            # Close download bar, if exist
            # Closing only works in chrome, but only chrome is affected by this leak method
            logger.debug(driver.title)
            if "larger 45" in driver.title:
                logger.debug(
                    f"{browser}:{pos} download bar detected, try to close: {driver.title}")
                driver.switch_to.new_window("tab")
                driver.get("chrome://downloads/")
                kill_download = """
                var item = document.querySelector('downloads-manager').shadowRoot.querySelector('downloads-item').shadowRoot.querySelector('cr-icon-button').shadowRoot.getElementById('maskedImage');
                item.click();
                return item;
                """
                item = driver.execute_script(
                    kill_download)  # Driver might crash here, resulting in double checking a URL (do not try catch here to ensure that download bar is gone, either no error here or due to restart)
                logger.debug(item)
                driver.close()
                driver.switch_to.window(org_window)
                # Need some time to actually close the dowload bar
                time.sleep(0.1)

            # Open a new tab to reset window.history.length and potential other problems
            driver.switch_to.new_window("tab")
            org_window = driver.current_window_handle

            # driver.close() # if not COOP, closes the last tab -> selenium crashes, if COOP, selenium cannot close the tab -> selenium crashes
            # close all other windows when they exist (e.g., if COOP=same-origin) and switch back to original after
            if (len(driver.window_handles) > 1):
                logger.debug(
                    f"{browser}:{pos} more than one window, close all others")
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    if handle != org_window:
                        driver.close()
                driver.switch_to.window(org_window)

    except (TimeoutException, UnexpectedAlertPresentException) as e:
        if type(e) == UnexpectedAlertPresentException:
            logger.warning(f"{browser}:{pos} Alert occured for {url}, try_num: {try_num}. Cancel")
        else:
            # Log that timed out and save in database
            if try_num < max_try_num:
                logger.info(f"{browser}:{pos} timeout occured for {url}, reason: {e}, try_num: {try_num}, max_try_num: {max_try_num}, retry!")
                test_url(driver, url, timeout_page_execute, browser, version, wait_time, pos, headless, retest, cookies, site, try_num+1, max_try_num)
            else:
                logger.info(f"{browser}:{pos} timeout occured for {url}, reason: {e}, try_num: {try_num}, max_try_num: {max_try_num}, save as timeout, no retry!")
                timed_out = True
                inc_method, tested_url = parse_url(url)
                requests.post(LOG_URL, json={
                    "browser": {
                        "browser": browser,
                        "version": version,
                        "headless": headless,
                    },
                    "test": {
                        "test_url": tested_url,
                        "inc_method": inc_method,
                        "url_dict_version": URL_DICT_VERSION,
                    },
                    "timed_out": timed_out,
                    "apg_url": url,
                    "retest": retest,
                    "cookies": cookies, # Is ignored by db backend for Q1
                    "site": site,
                })


def parse_url(url):
    """Return the inclusion method and test_url part of a url.

    Example url: http://192.168.2.148:8001/apg/iframe/?url=https://192.168.2.148:44300/leaks/10643/noauth/&browser=chrome&version=90.0.4430.85&wait_time=500
    Example result: ("iframe", "https://192.168.2.148:44300/leaks/10643/noauth/")
    """
    parts = url.split("?")
    inc_method = parts[0].split("/")[-2:-1][0]
    test_url = parts[1].split("=")[1].split("&")[0]
    return inc_method, test_url


def add_cookies_driver(driver, browser, site):
    """Login the driver using the correct cookies.
    """

    if site == "172.17.0.1:44320":
        driver.get("https://172.17.0.1:44320/leaks/login_direct")
    else:
        r = redis.Redis()
        cookies = json.loads(r.get(site))
        if "-unpruned" in site:
            site = site.split("-unpruned")[0]
        # We need to be on the correct site to set cookies in selenium
        driver.get(f"https://{site}/")
        # Delete all cookies
        driver.delete_all_cookies()
        # Set all cookies, we got from cookiehunter
        for cookie in cookies:
            cookie.pop("domain") # Remove the domain attribute because selenium will prepend a dot, and then the browser will not send it along
            driver.add_cookie(cookie)
    # See if it worked
    logger.info(f"{browser}-{site} has {len(driver.get_cookies())} cookies")

logger = None
def logging_init_handler(queue):
    """Set up logging using QueueHandler.
    """
    global logger
    qh = QueueHandler(queue)
    logger = logging.getLogger("leaks")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(qh)
    logger.propagate = False

# Logging parameters
CONSOLE_LOG_LEVEL = os.getenv("CONSOLE_LOG_LEVEL", "WARNING")
FILE_LOG_LEVEL = os.getenv("FILE_LOG_LEVEL", "WARNING")
LOG_URL = os.getenv("LOG_URL", "http://172.17.0.1:8002/dbserver/v2/")
URL_DICT_VERSION = "INVALID"
LOG_DIR = "/tmp/dil"

def logging_init_listener(worker=1, CONSOLE_LOG_LEVEL=CONSOLE_LOG_LEVEL, FILE_LOG_LEVEL=FILE_LOG_LEVEL, TIMESTAMP=None, LOG_DIR=LOG_DIR):
    """Set up logging using QueueListener.
    """
    if TIMESTAMP is None:
        TIMESTAMP = datetime.datetime.now().strftime('%y%m%d_%H%M%S')

    formatter = logging.Formatter(
        '%(asctime)s\t%(levelname)s -- %(processName)s %(filename)s:%(lineno)s -- %(message)s')

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(CONSOLE_LOG_LEVEL)

    Path(f"{LOG_DIR}/{TIMESTAMP}").mkdir(parents=True, exist_ok=True)

    file_log_path = f"{LOG_DIR}/{TIMESTAMP}/{worker}.log"
    file_logger = logging.FileHandler(filename=file_log_path)
    file_logger.setFormatter(formatter)
    file_logger.setLevel(FILE_LOG_LEVEL)

    queue = Queue()
    listener = QueueListener(queue, console, file_logger,
                             respect_handler_level=True)
    listener.start()

    return listener, queue



if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(
            "Not enough parameters. Use one of local_grid, browserstack, chrome or tor")
    # Choose the correct get_driver file/class
    test_setting = sys.argv[1]
    if test_setting == "local_grid":
        browsers = BrowserGrid()
    elif test_setting == "browserstack":
        browsers = BrowserStack()
    elif test_setting == "tor":
        browsers = BrowserTor()
    elif test_setting == "chrome":
        browsers = BrowserChrome()
    else:
        sys.exit(
            "Invalid test_setting. Use one of local_grid, browserstack, chrome or tor")


    # Set up logging
    listener, queue = logging_init_listener()
    logging_init_handler(queue)

    # Get the process parameters
    timeout_page_load = int(os.getenv("TIMEOUT_PAGE_LOAD"))
    timeout_page_execute = int(os.getenv("TIMEOUT_PAGE_EXECUTE"))
    wait_time = int(os.getenv("WAIT_POSTMESSAGE_ETC"))
    display_progress = bool(os.getenv("DISPLAY_PROGRESS", False))
    # Test SameSite independently, so we do not need to login
    login = bool(os.getenv("LOGIN_BROWSER", False))

    # Get the URL parameters
    BASE_URL = os.getenv("BASE_URL", "https://192.168.2.148:44300")
    LOGIN_URL = f"{BASE_URL}/leaks/login/"
    TEST_LOGIN_URL = f"{BASE_URL}/leaks/test/"
    APG_URL = os.getenv("APG_URL", "http://192.168.2.148:8001/apg")
    LOG_URL = os.getenv("LOG_URL", "http://192.168.2.148:8002/dbserver/")
    START_URL_NUMBER = int(os.getenv("START_URL_NUMBER", 0))
    URL_COUNT = int(os.getenv("URL_COUNT", 100))
    VER_URL = f"{BASE_URL}/leaks/ver/"
    URL_DICT_VERSION = requests.get(VER_URL, verify=False).text

    
    url_dict = None
    url_step = 1
    retest = False

    TEST_MODE = os.getenv("TEST_MODE", "normal")
    if TEST_MODE == "dict":
        # Get the urls from a dictionary (e.g., test all missing ones)
        TEST_DICT_PATH = os.getenv("TEST_DICT_PATH")
        with open(TEST_DICT_PATH, "rb") as f:
            url_dict = pickle.load(f)
    if TEST_MODE == "retest":
        retest = True
        url_step = int(os.getenv("URL_STEP"))
    if len(sys.argv) == 5:
        START_URL_NUMBER = int(sys.argv[2])
        URL_COUNT = int(sys.argv[3])
        browsers = BrowserGrid(sys.argv[4])
    # Test all browsers
    test_browsers(browsers, timeout_page_load,
                  timeout_page_execute, wait_time, display_progress, login, url_dict, url_step, retest)

   # Stop the logging (necessary to not miss any messages)
    listener.stop()
