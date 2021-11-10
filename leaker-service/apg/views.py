import os
import logging
import requests
from django.shortcuts import render
from django.http import HttpResponse
from .inclusion_methods import inclusion_methods

# Url of the server accepting the results of the apg
log_server = os.getenv("LOG_URL")
ver_url = f"{os.getenv('BASE_URL')}/leaks/ver/"
logger = logging.getLogger(__name__)
try:
    url_dict_version = requests.get(ver_url, verify=False).text
except Exception as e:
    logger.warning(f"Couldn't load url_dict_version, {e}")
    url_dict_version = "Unknown"

def get_attack_page(request, inc_method):
    """Generate an attack page for the given inc_method.

    Many things can be specified using query parameters
    """
    try:
        context = inclusion_methods[inc_method].copy()
        context["inc_method"] = inc_method
    except KeyError:
        logger.warning(f"Inclusion method: {inc_method} not supported")
        return HttpResponse(f"Inclusion method: {inc_method} not supported")
    # Additional parameters    
    test_url = request.GET.get("url", "https://example.com") # Problem: if there is more than one get parameter in the test_url, it is lost!
    test_url = request.get_full_path().split("?url=", 1)[1].split("&browser=")[0] # Only works, if we specify browser as the first GET parameter not belonging to the test_url
    context["test_url"] = test_url
    context["hash"] = request.GET.get("hash", "test1")
    context["browser"] = request.GET.get("browser", "unknown")
    context["version"] = request.GET.get("version", "unknown")
    context["wait_time"] = request.GET.get("wait_time", "200")  # 200 is not enough for chrome, e.g., link-prefetch often has not finished errors yet
    context["headless"] = request.GET.get("headless", "False")
    context["retest"] = request.GET.get("retest", "False")
    context["log_server"] = log_server
    context["url_dict_version"] = url_dict_version
    context["site"] = request.GET.get("site", "")
    context["cookies"] = request.GET.get("cookies", "False")

    # Opionally set CSP to only allow loading of the `test_url` (block redirects)
    # Log url also has to be allowed
    if context.get("csp") is not None:
        context["csp"] = context["csp"].replace("<test_url>", test_url.split("?")[0])
        context["csp"] = context["csp"].replace("<log_url>", log_server)

    # Return the attack page
    return render(request, "apg/attack_page.html", context)

def get_test_page(request, inc_method):
    """Generate a (cookie) test page for the given inc_method."""
    try:
        context = inclusion_methods[inc_method].copy()
        context["inc_method"] = inc_method
    except KeyError:
        logger.warning(f"Inclusion method: {inc_method} not supported")
        return HttpResponse(f"Inclusion method: {inc_method} not supported")

    browser = request.GET.get("browser", "unknown")
    version = request.GET.get("version", "unknown")
    org_site = request.get_host()
    test_url = request.GET.get("url", "http://127.0.0.1:8000/leaks/check_cookies/")
    context["test_url"] = f"{test_url}?browser={browser}&version={version}&inc_method={inc_method}&org_site={org_site}"

    # Return the test page
    return render(request, "apg/test_page.html", context)
