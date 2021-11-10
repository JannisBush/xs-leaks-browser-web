# Usage: mitmdump -nr <already-saved-flow-file> -s "mitm_response_decode.py"
import sys
import hashlib
import redis
from pathlib import Path
from mitmproxy import http, ctx
from celery import Celery
import typing
from publicsuffix2 import fetch
from publicsuffix2 import PublicSuffixList
app = Celery('db', broker='pyamqp://guest@localhost//')
r = redis.Redis()
count = 0
base_dir = "/tmp/httpcontent"
duplicate_headers = set()

def decode(s, encodings=("ascii", "utf-8", "latin1")):
    """Try to decode given bytes using different encodings.
    Taken from: https://stackoverflow.com/a/273631/11782367
    """
    for encoding in encodings:
        try:
            return s.decode(encoding)
        except UnicodeDecodeError:
            pass
    return s.decode('ascii', 'ignore')


def convert_headers(headers):
    """Convert headers (netlib.http.Headers) to a json-convertable dict."""
    header_dict = {}
    for head, val in headers:
        # We need to convert everything to str,
        # because it needs to be json-convertable for celery
        # Alternatively MultiDictView.to_dict() could be used?,
        # but we still would need to convert everything to a string
        head = decode(head).lower()  # Convert all headers to lowercase
        val = decode(val)
        if head in header_dict:
            if not head in duplicate_headers:
                print(f"{head} appears more than once!")
                duplicate_headers.add(head)
            old_val = header_dict[head]
            # Header folding as per RFC7230
            header_dict[head] = f"{old_val}, {val}"
        else:
            header_dict[head] = val
    return header_dict


def write_cont(body_hash, content):
    """Save the content of a request/response to disk."""
    if not r.get(body_hash):
        r.set(body_hash, "Saved")
        with open(f"{base_dir}/{body_hash[0]}/{body_hash[1]}/{body_hash}", "wb") as f:
            f.write(content)


class LogEverything:
    def __init__(self, port):
        """Init the LogEverything class."""
        self.error_count = 0

        self.site, self.cookies = r.get(port).decode("utf-8").split(":::::")
        print(f"Init proxy for {self.site}, cookies: {self.cookies}, port: {port}.")

        # Get the newest publicsuffixlist in a tree format
        psl_file = fetch()
        self.psl = PublicSuffixList(psl_file)

        # Create dirs to save request/response bodies to
        for first in "0123456789abcdef":
            for second in "0123456789abcdef":
                Path(f"{base_dir}/{first}/{second}").mkdir(parents=True, exist_ok=True)

    def done(self):
        """Called when mitmdump finishes (bug: currently not for ctlr+c)"""
        print(f"Number of errors that occured: {self.error_count}")


    def get_site(self, hostname):
        """Returns the site from a hostname."""
        if "172.17.0.1" in hostname:
            return "172.17.0.1:44320"
        site = self.psl.get_public_suffix(hostname)
        if self.site.endswith("-unpruned"):
            site = site + "-unpruned"
        return site

    def response(self, flow: http.HTTPFlow):
        """Process a response.

        If the flow is replayed it means that the request was done without cookies.
        Otherwise the request was done with cookies.
        """
        if flow.is_replay == "request":
            # print("replayed request response")
            cookies = False
        else:
            # print("first response")
            cookies = True

        # If the request or the response has no body, set it to empty
        # (we cannot hash None)
        req_content = flow.request.content
        if req_content is None:
            req_content = b""
        resp_content = flow.response.content
        if resp_content is None:
            resp_content = b""
        req_body_hash = hashlib.sha1(req_content).hexdigest()
        resp_body_hash = hashlib.sha1(resp_content).hexdigest()

        # Save the content to disk
        write_cont(req_body_hash, req_content)
        write_cont(resp_body_hash, resp_content)

        # Save the response
        data = {
                "req_url": flow.request.url,
                "req_method": flow.request.method,
                "req_headers": convert_headers(flow.request.headers.fields),
                "req_body_hash": req_body_hash,
                "resp_version": flow.response.http_version,
                "resp_code": flow.response.status_code,
                "resp_headers": convert_headers(flow.response.headers.fields),
                "resp_body_hash": resp_body_hash,
                "cookies": cookies,
                "site": self.site,
                "real_site": self.get_site(flow.request.host),

        }
        app.send_task('main.list_data', args=[data], kwargs={})

    def request(self, flow):
        """Process a request.

        Duplicate the request without cookies.
        """
        # print(f"version: {flow.request.http_version}, method: {flow.request.method} request: {flow.request.url}, headers: {bytes(flow.request.headers)}")
        # print(flow.request.headers.fields)
        if flow.is_replay == "request":
            # print("replayed request")
            return
        # print(flow)

        # Replay first-level GET requests without cookies
        # print(flow.request.host, self.site)
        site = self.get_site(flow.request.host)
        if (site == self.site) and (flow.request.method == "GET"):
            flow = flow.copy()
            try:
                del flow.request.headers["Cookie"]
            except KeyError:
                pass
            ctx.master.commands.call("replay.client", [flow])

    def error(self, flow):
        # print(f"error for {flow.request.url}, error: {flow.error}")
        self.error_count += 1


addons = [
        LogEverything(sys.argv[-1])
]
