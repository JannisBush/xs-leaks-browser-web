import sys
import os
from django.db import models


# os.environ["DJANGO_SETTINGS_MODULE"] = "../settings"

class URL_data(models.Model):
    req_url = models.TextField()
    req_method = models.TextField()
    req_headers = models.JSONField()
    req_body_hash = models.TextField()
    req_body_info = models.TextField()
    resp_version = models.TextField()
    resp_code = models.IntegerField()
    resp_headers = models.JSONField()
    resp_body_hash = models.TextField()
    resp_body_info = models.TextField()
    resp_body_tika_info = models.JSONField()
    cookies = models.BooleanField()
    site = models.TextField()
    real_site = models.TextField()
    hash_uniq = models.TextField(unique=True)
    count = models.IntegerField(default=1)

    class Meta:
        indexes = [
                models.Index(fields=["hash_uniq",]),
                models.Index(fields=["site",]),
                # models.Index(fields=["site", "req_url",]),  # req_url can be very long (query parameters of api calls, so this index can fail with `index row size ... exceeds maximum value ...`
        ]


class site_results(models.Model):
    site = models.TextField(unique=True)
    count = models.IntegerField(default=1)
    tranco_rank = models.IntegerField(default=-1)
    login = models.TextField()  # Set from cookiehunter: one of failed, heuristic, google, fb
    cookies = models.JSONField(null=True)
    cookie_end = models.TextField() # Time when cookiehunter was finished
    num_urls = models.IntegerField(null=True)  # How many URLs exist that have results for cookies/no-cookies
    num_basic_pruning = models.IntegerField(null=True)  # How many URLs after basic pruning
    num_input_rows = models.IntegerField(null=True)  # How many input rows for the trees (build from the basic pruned URLs)
    crawl_end = models.TextField()
    dyn_conf_urls = models.JSONField(null=True)
    dyn_conf_firefox = models.IntegerField(null=True)
    dyn_conf_chrome = models.IntegerField(null=True)
    dyn_end = models.TextField()
    dyn_conf_retest_urls = models.JSONField(null=True)
    dyn_conf_retest_firefox = models.IntegerField(null=True)
    dyn_conf_retest_chrome = models.IntegerField(null=True)
    dyn_retest_end = models.TextField()
    confirmed_urls = models.JSONField(null=True)
    confirmed_urls_firefox = models.IntegerField(null=True)
    confirmed_urls_chrome = models.IntegerField(null=True)
    confirmed_leak_urls = models.JSONField(null=True)
    confirmed_df_dict = models.JSONField(null=True)

    class Meta:
        indexes = [
                models.Index(fields=["site",]),
        ]
