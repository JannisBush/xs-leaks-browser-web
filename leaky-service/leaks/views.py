import pickle
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.auth import logout, login, authenticate
import logging
import requests

from echo.views import echo
from .models import URLDict, column_look_up, to_dict

logger = logging.getLogger(__name__)

# Example url_dict
url_dict = {
    1: {
        'content-type': ['application/javascript'],
        'Content-Security-Policy': ["default-src 'self'; img-src *; media-src media1.com media2.com; script-src userscripts.example.com"],
        'Cross-Origin-Opener-Policy': ['unsafe-none'],
        'Cross-Origin-Resource-Policy': ['same-site'],
        'X-Frame-Options': ['deny'],
        'X-Content-Type-Options': ['no-sniff'],
        'Content-Disposition': ['inline'],
        'Location': ['http://test.dev'],
        'ecocnt_html': ['meta_refresh=0;url=http://test.com?url=abc&abc=abc,num_frames=5,div_id=try,post_message=hi"aa\''],
        'ecohd_status': ['404'],
        'ecodly': ['100'],
    }
}

# Get correct url_dict from file
try:
    with open("url_dict.pickle", "rb") as f:
        url_dict = pickle.load(f)
        ver = url_dict.get("version")
except FileNotFoundError:
    ver = "Not set"

def login_view(request):
    """Login the request as our testuser."""
    logger.info(f"Login: {request.META.get('HTTP_USER_AGENT')}")
    user = authenticate(request, username="test", password="team40web")
    login(request, user)
    return HttpResponse()


def logout_view(request):
    """Logout the request."""
    logout(request)
    return HttpResponse()


def test_login(request):
    """Return a success page is the user is auth, otherwise an empty response.

    Clients can use this to check if the auth worked (using driver.title)
    """
    if request.user.is_authenticated:
        return render(request, "leaks/success.html")
    else:
        return HttpResponse()

def get_ver(request):
    """Returns the version of the current url dict."""
    return HttpResponse(ver)

def get_info(request, url_id):
    """Returns the content of the url_dict of url_id as json.
    
    One can specify a url_dict_version to get data of an older version.
    """
    url_dict_version = request.GET.get("url_dict_version", ver)
    try:
        info = to_dict(URLDict.objects.get(url_dict_version=url_dict_version, url_id=url_id))
        code = 200
    except URLDict.DoesNotExist:
        info = {"error": f"(url_dict_version={url_dict_version}, url_id={url_id}) does not exist"}
        code = 404
    return JsonResponse(info, status=code)

def save_dict(request):
    """Saves the current url_dict to the database.

    Warning: slow, this can take quite some time.
    """
    url_entries = []
    for url_id in url_dict:
        if url_id == "version":
            continue
        logger.info(url_id)
        entry = {
            "url_dict_version": ver,
            "url_id": url_id}
        for el, val in url_dict[url_id].items():
            if  el.startswith("ecocnt"):
                entry["body"] = f"{el}={val[0]}"
            else:
                new_el = column_look_up.get(el, el)
                entry[new_el] = val[0]
        url_entries.append(URLDict(**entry))
    
    # Create everything in one go
    URLDict.objects.bulk_create(url_entries)
    return HttpResponse()

def leaks(request, id_number, auth_status):
    """Return the correct response from the echo service.

    request: request object
    id_number: int, key in the url dict that tells us what to return
    auth_status: str, if "auth", we check if the request is authenticated and abort if not

    Note: all get and post parameters are ignored
    """
    if auth_status == "auth" and not request.user.is_authenticated:
        logger.warning(
            f"abort user not authenticated! {request.META.get('HTTP_USER_AGENT')}")
        return render(request, "leaks/fail.html")
    else:
        request.POST = {}
        request.GET = {}
        request.GET = url_dict.get(id_number, {})
        return echo(request)

def set_cookies(request):
    """Set cookies to test cookie behavior."""
    response = HttpResponse("Set cookies")
    response.set_cookie("notset_false", "received", samesite=None, secure=False)
    response.set_cookie("none_false", "received", samesite="None", secure=False)
    response.set_cookie("lax_false", "received", samesite="Lax", secure=False)
    response.set_cookie("strict_false", "received", samesite="Strict", secure=False)
    response.set_cookie("notset_true", "received", samesite=None, secure=True)
    response.set_cookie("none_true", "received", samesite="None", secure=True)
    response.set_cookie("lax_true", "received", samesite="Lax", secure=True)
    response.set_cookie("strict_true", "received", samesite="Strict", secure=True)
    return response

def check_cookies(request):
    """Check which cookies and sec-fetch attributes are send."""
    browser = request.GET.get("browser", "unknown")
    version = request.GET.get("version", "unknown")
    inc_method = request.GET.get("inc_method", "unknown")
    org_site = request.GET.get("org_site", "unknown")
    db_url = request.GET.get("db_url", "http://172.17.0.1:8002/dbserver/save_test/")

    # print(f"{browser}-{version}-{inc_method}")

    cookies_received = {}
    for value in ["notset_false", "none_false", "lax_false", "strict_false", "notset_true", "none_true", "lax_true", "strict_true"]:
        cookies_received[value] = request.COOKIES.get(value, "not_received")
    # print(cookies_received)

    sec_fetch = {}
    for value in ["Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site", "Sec-Fetch-User"]:
        sec_fetch[value] = request.headers.get(value, "not_received") 
    # print(sec_fetch)
    
    data = {
            "browser": browser,
            "version": version,
            "inc_method": inc_method,
            "org_site": org_site,
            "rec_site": request.get_host(),
            "c_ns_f": cookies_received["notset_false"],
            "c_ns_t": cookies_received["notset_true"],
            "c_n_f": cookies_received["none_false"],
            "c_n_t": cookies_received["none_true"],
            "c_l_f": cookies_received["lax_false"],
            "c_l_t": cookies_received["lax_true"],
            "c_s_f": cookies_received["strict_false"],
            "c_s_t": cookies_received["strict_true"],
            "sec_fetch_dest": sec_fetch["Sec-Fetch-Dest"],
            "sec_fetch_mode": sec_fetch["Sec-Fetch-Mode"],
            "sec_fetch_site": sec_fetch["Sec-Fetch-Site"],
            "sec_fetch_user": sec_fetch["Sec-Fetch-User"],
    }
    res = requests.post(db_url, json=data)

    return HttpResponse(f"Cookies: {cookies_received},<br> Sec-Fetch: {sec_fetch}")
