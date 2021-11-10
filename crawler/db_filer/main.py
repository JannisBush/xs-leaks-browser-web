import os
import django
from celery import Celery
from celery.signals import worker_process_init, celeryd_init
import redis
import subprocess
import hashlib
import pickle
import json
import traceback
import tika
from tika import parser

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from db.models import URL_data, site_results
from django.db.models import F
from django.db import DataError

app = Celery('db', broker='pyamqp://guest@localhost//')
base_dir = "/tmp/httpcontent"


@celeryd_init.connect
def global_init(**kwargs):
    """Start apache tika in the global start function."""
    print("Global start")
    tika.initVM()
    parser.from_file('main.py')
    print("Start success")


@worker_process_init.connect
def init(**kwargs):
    """Set up redis in the worker init function."""
    global r
    r = redis.Redis()
    print("Connection succesfull")


def get_info(cont_hash):
    """Returns file/content info using the file command."""
    global r
    file_info = r.get(f"fileinfo:{cont_hash}")
    if not file_info:
        file_info = subprocess.check_output(["file", f"{base_dir}/{cont_hash[0]}/{cont_hash[1]}/{cont_hash}"])
        r.set(f"fileinfo:{cont_hash}", file_info)
    return file_info


def get_tika(cont_hash):
    """Returns file/content info using apache tika."""
    global r
    file_info = r.get(f"fileinfotika:{cont_hash}")
    if not file_info:
        file_info = parser.from_file(f"{base_dir}/{cont_hash[0]}/{cont_hash[1]}/{cont_hash}")["metadata"]
        # # Remove Tika info (e.g. how long it took)
        # for k in list(file_info.keys()):
        #     if k.startswith("X-"):
        #         del file_info[k]
        file_info = json.dumps(file_info)
        file_info = file_info.replace("\\u0000", "")  # Remove null bytes
        r.set(f"fileinfotika:{cont_hash}", json.dumps(file_info))
        return json.loads(file_info)
    else:
        return json.loads(file_info)


def get_hash(u):
    """Returns the hash of a url_dict."""
    to_hash = [u["req_url"], u["site"], u["real_site"], u["cookies"], u["req_method"], u["resp_code"], u["resp_version"]]
    return hashlib.sha1(pickle.dumps(to_hash)).hexdigest()


@app.task(soft_time_limit=15)
def list_data(u):
    """Task to save the results of crawling a url.

    u: dict of type URL_data
    """
    # Get the info on the content of the request and response body
    u["resp_body_info"] = get_info(u["resp_body_hash"])
    u["req_body_info"] = get_info(u["req_body_hash"])
    u["resp_body_tika_info"] = get_tika(u["resp_body_hash"])
    u["hash_uniq"] = get_hash(u)

    # Create an entry or increase the count for this URL
    try:
        url_data, created = URL_data.objects.get_or_create(hash_uniq=u["hash_uniq"], defaults=u)
    except DataError as e:
        traceback.print_exc()
        u["resp_body_tika_info"] = {"tika": "contains Null byte"}
        url_data, created = URL_data.objects.get_or_create(hash_uniq=u["hash_uniq"], defaults=u)
    finally:
        if not created:
            url_data.count = F("count") + 1
            url_data.save()


@app.task(soft_time_limit=15)
def save_results(site, data):
    """Task to save general results for a site."""
    site, _ = site_results.objects.update_or_create(site=site, defaults=data)
