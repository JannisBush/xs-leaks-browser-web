import json
import os
import time
import redis
import psycopg2
import pandas as pd
from billiard import current_process
from datetime import datetime
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown, celeryd_init, worker_shutdown, task_failure
from celery.exceptions import SoftTimeLimitExceeded

from test_browsers import run_session, logging_init_handler, logging_init_listener
from dil_preprocess import get_url_data, basic_pruning
from dil_predict import init, predict_trees, reduce_leaky_endpoints
from dil_postprocess import get_working_incs, get_dyn_urls, get_dyn_results, get_retest_urls, get_working_urls, get_working_urls_channels

from get_local_grid import BrowserGrid, browser_to_cap

browsers = BrowserGrid()
app = Celery("leak", broker="pyamqp://guest@localhost//", backend="rpc://")
app.conf.task_default_queue = "leak"
app.conf.worker_prefetch_multiplier = 1
app.conf.broker_connection_timeout = 10
db_conn = None
models = None
listener = None
r = None
timestamp = None

@task_failure.connect
def task_failed(**kwargs):
    global models
    print(kwargs)
    print(len(models))
    models = init()
    print(f"{len(models)} models loaded")

@celeryd_init.connect
def global_init(**kwargs):
    """Set up h2o models in global init."""
    print("Global init")
    global models
    global listener
    global timestamp
    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
    # time.sleep(20)
    models = init()
    # Sometimes this is never reached (without an error)! Why? Fix it!
    print(f"{len(models)} models loaded")


@worker_shutdown.connect
def close_worker(**kwargs):
    """Shutdown worker."""
    pass


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Connect to db in worker init."""
    global db_conn
    global listener
    global r
    global timestamp
    param_dict = {
               "host": os.getenv("DB_HOST"),
               "database": os.getenv("DB_NAME"),
               "user": os.getenv("DB_USER"),
               "password": os.getenv("DB_PASSWORD"),
               "port": os.getenv("DB_PORT"),
    }
    try:
        db_conn = psycopg2.connect(**param_dict)
        listener, queue = logging_init_listener(current_process().index, "ERROR", "INFO", timestamp)
        logging_init_handler(queue)
        r = redis.Redis()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    print("Connection succesfull")
    # init()


@worker_process_shutdown.connect
def close_worker_process(**kwargs):
    """Close db connection in worker shutdown."""
    global db_conn
    global listener
    if db_conn:
        db_conn.close()
        print("Closed db")
    if listener:
        listener.stop()
        print("Closed listener")


@app.task(soft_time_limit=18000)
def run(urls, site, retest, browser, cookies):
    """Dynamically test all URLs given."""
    global browsers
    try:
        print(f"Testing {len(urls)} urls for {site} in {browser} with cookies={cookies}, retest={retest}")
        chunk_size = 100  # Test a maximux of 100 URLs before the browser gets restarted
        url_chunks = [urls[i * chunk_size:(i + 1) * chunk_size] for i in range((len(urls) + chunk_size - 1) // chunk_size)]
        for url_chunk in url_chunks:
            settings = {
                    "browsers": browsers,
                    "browser": browser,
                    "cap_key": browser_to_cap[browser],  # Firefox is 1, Chrome is 0
                    "urls": url_chunk,
                    "timeout_page_load": 20,  # 20s for the initial load
                    "timeout_page_execute": 10,  # 10s for the execution of the page
                    "wait_time": 2000,  # 2000ms waiting time for postMessages, and co on a page
                    "pos": 0,
                    "display_progress": False,
                    "cookies": cookies,
                    "headless": False,
                    "retest": retest,
                    "site": site,
                    "max_try_num": 2,  # Try a timeout out URL again
            }
            run_session(**settings)
    except SoftTimeLimitExceeded:
        print(f"Time for {site} exceeded, stop dynamic confirmation now!")
    finally:
        if retest == 0:
            retest_sites.delay(site)
        else:
            final.delay(site)


@app.task(soft_time_limit=500)
def start(site, cookies=None, unpruned=False):
    """Start testing of a site.

    Get all URLs/inc_methods that might work according to tree.
    Then test them dynamically.
    """
    global db_conn
    print(site)
    # Get the URLs that might work
    dat = get_url_data(site, conn=db_conn, close=False)
    af, d, poss, results = basic_pruning(dat)
    if not cookies:
        results["crawl_end"] = str(datetime.now())
    
    if unpruned:
        print("Unpruned run!")
        site = f"{site}-unpruned"
    if site.endswith("-unpruned"):
        unpruned = True
        print("Unpruned run!")

    if af is None:
        urls = {}
    else:
        leaky_endpoints = predict_trees(af)
        if leaky_endpoints == {}:
            urls = {}
        else:
            leaks = reduce_leaky_endpoints(leaky_endpoints)
            incs = get_working_incs(leaks)
            urls = get_dyn_urls(leaks, incs, d, poss, unpruned=unpruned)

    results["dyn_conf_urls"] = urls
    results["dyn_conf_firefox"] = len(urls.get("firefox", []))
    results["dyn_conf_chrome"] = len(urls.get("chrome", []))
    app.send_task("main.save_results", args=[site, results], kwargs={}, queue="celery")

    # Dynamically test the URLs that might work
    for browser in ["firefox", "chrome"]:
        for cookies in [True, False]:
            run.delay(urls.get(browser, []), site, 0, browser, cookies)


@app.task(soft_time_limit=500)
def retest_sites(site):
    """Retest all URLs that worked."""
    global r
    global db_conn

    count = r.incr(f"{site}::first_count")
    if count == 4:
        # Both runs are finished
        # Get the results? Which leaks worked?
        df = get_dyn_results(site, conn=db_conn, close=False)
        retest, _, _ = get_retest_urls(df)
        results = {}
        results["dyn_conf_retest_urls"] = retest
        results["dyn_conf_retest_firefox"] = len(retest.get("firefox", []))
        results["dyn_conf_retest_chrome"] = len(retest.get("chrome", []))
        results["dyn_end"] = str(datetime.now())
        app.send_task("main.save_results", args=[site, results], kwargs={}, queue="celery")

        # Dynamically retest
        for browser in ["firefox", "chrome"]:
            for cookies in [True, False]:
                # Retest those to minize fps
                run.delay(retest.get(browser, []), site, 1, browser, cookies)


@app.task(soft_time_limit=500)
def final(site):
    """Save all URLs that are leakable after two dynamic confirmation rounds."""
    global r
    global db_conn

    count = r.incr(f"{site}::second_count")
    if count == 4:
        # Get the final working ones
        working_df, working_urls, leak_urls = get_working_urls_channels(get_dyn_results(site, conn=db_conn, close=False), conn=db_conn)
        print(f"Site: {site}, working_urls: {working_urls}")
        # save the final (and all intermediate) results in db!
        results = {}
        results["confirmed_urls"] = working_urls
        results["confirmed_urls_firefox"] = len(leak_urls.get("firefox", []))
        results["confirmed_urls_chrome"] = len(leak_urls.get("chrome", []))
        results["confirmed_leak_urls"] = leak_urls
        results["confirmed_df_dict"] = working_df.to_dict("list")
        results["dyn_retest_end"] = str(datetime.now())
        app.send_task("main.save_results", args=[site, results], kwargs={}, queue="celery")
