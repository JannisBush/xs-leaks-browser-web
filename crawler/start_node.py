import os
import socket
import psycopg2
import hashlib
import random
import signal
from celery import Celery
from celery.signals import (worker_process_init, worker_process_shutdown,
                            celeryd_init)
import redis
import subprocess
import json
import time
from pathlib import Path

app = Celery("node", broker="pyamqp://guest@localhost//")
app.conf.task_default_queue = "node"
db_conn = None
r = None
LOG_DIR = "/tmp/node-crawler"


def get_free_port():
    """Returns a free port of the system. Be aware of race conditions."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("localhost", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@celeryd_init.connect
def global_init(**kwargs):
    """Global celery init function only called once,
    regardless of number of workers."""
    # call init and setup
    print("Global init")
    pass


@worker_process_init.connect
def init(**kwargs):
    """Worker init function, called once per worker.
    Setup db connections and process properties."""
    global db_conn
    global r
    # Signal OS that we do not care about exit statuses of child processes
    # Necessary to not create defunct/zombie processes as we start processes
    # without waiting for them
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    param_dict = {
               "host": os.getenv("DB_HOST"),
               "database": os.getenv("DB_NAME"),
               "user": os.getenv("DB_USER"),
               "password": os.getenv("DB_PASSWORD"),
               "port": os.getenv("DB_PORT"),
    }
    try:
        r = redis.Redis()
        db_conn = psycopg2.connect(**param_dict)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    print("Connection succesfull")


@worker_process_shutdown.connect
def close_worker(**kwargs):
    """Worker shutdown function, called once per worker.
    Close db connection."""
    global db_conn
    if db_conn:
        db_conn.close()
        print("Closed db")


@app.task
def test_site(site, cookies):
    """Test a site.

    Site is the name of a site cookiehunter managed to register and login.
    Cookies are the corresponding cookies.

    Start a mitmproxy to save and replay requests
    and then start a node_crawler that uses this proxy.
    """
    global db_conn
    global r
    # Cookies is a list of dicts [{'domain': '', 'name': 'a', ...}, ...]
    # Put the cookies into redis such that they can be fetched again later
    r.set(site, json.dumps(cookies))
    try:
        cookies = True
        site = site
        # The starting URL of the site
        if site.endswith("-unpruned"):
            url = f"https://{site[:-9]}/"
        else:
            url = f"https://{site}/"
        addInfo = ""
        url_hash = hashlib.sha1(bytes(url, "utf-8")).hexdigest()
        addInfoHash = hashlib.md5(bytes(addInfo, "utf-8")).hexdigest()
        level = 0
        rank = None
        job_query = "INSERT INTO job (description) VALUES (%s) RETURNING job_id"
        site_query = "INSERT INTO sites (job_id, site, cookies, counter, crawl_status) VALUES (%s, %s, %s, 1, 0)"
        url_query = "INSERT into url (job_id, site, url, cookies, url_hash, level, addInfo, addinfo_hash, alexa_rank) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"
        with db_conn, db_conn.cursor() as cur:
            # Write the crawl job in the db
            cur.execute(job_query, [f"{site}: cookies:{cookies}"])
            job_id = cur.fetchone()[0]
            # Write the site in the db
            cur.execute(site_query, [job_id, site, cookies])
            # Write the start URL in the db
            cur.execute(url_query, [job_id, site, url, cookies, url_hash,
                                    level, addInfo, addInfoHash, rank])

            # Start mitmproxy on a free port
            port = str(get_free_port())
            r.set(port, f"{site}:::::{cookies}")
            Path(f"{LOG_DIR}/{job_id}_{site}").mkdir(parents=True, exist_ok=True)
            with open(f"{LOG_DIR}/{job_id}_{site}/mitm.log", "w") as f:
                if site == "172.17.0.1:44320":
                    # Ignore cert errors to test our local test site
                    pid = subprocess.Popen(["mitmdump", "-s", "crawler/save_and_replay.py", "-q", "--ssl-insecure", "-p", port],
                                           stdout=f, stderr=f, cwd="..").pid
                else:
                    # Normal run, block cert erros (brwoser blocks them by default too)
                    pid = subprocess.Popen(["mitmdump", "-s", "crawler/save_and_replay.py", "-q", "-p", port],
                                          stdout=f, stderr=f, cwd="..").pid
            r.set(f"{site}:::::{cookies}", pid)
            # Give the proxy enough time to start
            time.sleep(10)

            # Start the node_crawler proccess using subprocess
            with open(f"{LOG_DIR}/{job_id}_{site}/err.log", "w") as err_f:
                with open(f"{LOG_DIR}/{job_id}_{site}/inf.log", "w") as log_f:
                    proc = subprocess.Popen(["node", "start.js", "--mode", "run",
                                             "--job_id", str(job_id), "--crawler_id", str(job_id),
                                             "--user_data_dir", f"/tmp/node-crawler{job_id}/",
                                             "--headless", "--proxyStartPort", port, "--module", "set_cookies"],
                                            stdout=log_f, stderr=err_f, cwd="../../node-crawler")

        print(f"Started crawler for: {site}, {job_id}, cookies: {cookies}, mitmpid: {pid}, port: {port}")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
