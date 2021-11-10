from celery import Celery
import redis
import json
import time


app = Celery('call', broker='pyamqp://guest@localhost//',)
r = redis.Redis()

if __name__ == '__main__':
    for site in ["chartink.com-unpruned"]:#["172.17.0.1:44320"]:
        # r.set(site, json.dumps([{"domain": site, "name": "abc", "value": "abc"}]))
        # result = app.send_task("does_it_leak.start", args=[site], kwargs={"unpruned": True}, queue="leak")
        result = app.send_task("does_it_leak.start", args=[site], kwargs={}, queue="leak")
    sys.exit()
    time.sleep(10)

    site = "172.17.0.1:8000"
    r.set(site, json.dumps([{"domain": site, "name": "abc", "value": "abc"}]))
    # res = app.send_task("does_it_leak.run", args=[[f"http://172.17.0.1:8001/apg/script/?url=http://{site}/echo/?ecodly=100000000"], site, 0, "firefox", False], kwargs={}, queue="leak")

    result = app.send_task("does_it_leak.start", args=[site], kwargs={}, queue="leak")
   
