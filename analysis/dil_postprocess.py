import time
import glob
import itertools
import h2o
import pandas as pd
import json

from database_connector import connect, postgresql_to_dataframe
from helper_functions import get_ef, get_of, get_gf, get_wf, get_tf

base_url = "http://172.17.0.1:8001/apg"


def get_browser_mapping():
    """Get browser id to name mapping from db."""
    # Connect to the database
    conn = connect()
    column_names = ["id", "browser" ]
    # Execute the "SELECT" query
    df = postgresql_to_dataframe(conn, "SELECT id, browser from dbcon_browser",
                                 column_names)
    conn.close()
    df = df.set_index("id")
    return df.to_dict()["browser"]


id_to_name = get_browser_mapping()  # {1: "firefox", 2: "chrome"}
name_to_id = {v: k for k, v in id_to_name.items()}


def get_working_incs(leaks):
    """Return all inclusion methods that might work for every browser."""
    incs = {"1": set(), "2": set()}
    for col in leaks.filter(regex="/mojo/"):
        browser = col.split("/mojo/")[1].split("/")[0]
        inc = col.split("::")[1].split(".mojo")[0]
        incs[browser].add(inc)

    return incs


def get_working_incs_row(row, incs):
    """Return all working inclusion methods for both browsers for a row."""
    working = {"1": [], "2": []}
    for brow in incs:
        for meth in incs[brow]:
            if row.filter(regex=f".*/{brow}/.*::{meth}.mojo").any():
                working[brow].append(meth)
    return working["1"], working["2"]


def create_urls(row):
    """Create all URLs that need to be tested dynamically."""
    urls = {"firefox": [], "chrome": []}
    for brow in ["firefox", "chrome"]:
        incs = row[brow]
        for inc in incs:
            # If a redirect occurs in one case only or redirect to two different pages, every leak channel might work on the resulting page
            # Only apply this for redirects based on the Location header
            # Every HTML page can redirect with <meta-refresh>, but this should be rare
            if inc == "iframe-csp" and row["Location_count"] > 1:
                for inc_method in get_inc_methods(brow):
                    urls[brow].append(f"{base_url}/{inc_method}/?url={row['URL']}")
                break
            else:
                urls[brow].append(f"{base_url}/{inc}/?url={row['URL']}")
    return urls["firefox"], urls["chrome"]


def get_inc_methods(browser):
    """Return all inclusion methods applicable for a given browser."""
    return ["script", "link-stylesheet", "link-prefetch", "img", "iframe", "video", "audio", "object", "embed", "embed-img", "window.open", "iframe-csp"]


def get_dyn_urls(leaks, incs, d, poss, log=False, unpruned=False):
    """Return all URLs that need to be tested dynamically."""
    # Return all combinations of URLs (unpruned, not even basic pruning) x inc_methods
    # (Some pruning is done as d only contains URLs that have a result for a GET request for both states)
    if unpruned:
        print("Test all combinations")
        base_urls = d["URL"].unique()
        urls_to_test = range(d["URL"].nunique())
        urls = {}
        for brow in ["chrome", "firefox"]:
            urls[brow] = []
            for url in base_urls:
                for inc in get_inc_methods(brow):
                    urls[brow].append(f"{base_url}/{inc}/?url={url}")
    # Return all leak channels for each URL that might work (basic pruning + advanced tree pruning)
    else:    
        leaks[["firefox", "chrome"]] = leaks.apply(get_working_incs_row, axis=1, incs=incs, result_type="expand")
        if log:
            display(leaks[["firefox", "chrome"]])
        urls_to_test = leaks[["firefox", "chrome", "Location_count"]].reset_index()
        url_df = urls_to_test.apply(create_urls, axis=1, result_type="expand")
        urls = {}
        urls["firefox"], urls["chrome"] = list(set(itertools.chain(*url_df[0].to_list()))), list(set(itertools.chain(*url_df[1].to_list())))
    if log:
        print(f"Firefox URLs: {len(urls['firefox'])}, Chrome URLs: {len(urls['chrome'])}, unique urls to test: {len(urls_to_test)}, non-pruned base URLs: {d['URL'].nunique()}, basic-pruned URLs: {poss['URL'].nunique()}, Firefox non-pruned test URLs: {d['URL'].nunique() * 11}, Chromiun non-pruned test URLs: {d['URL'].nunique() * 10}")
        print(urls["firefox"][:5], urls["chrome"][:5])
    return urls


def get_dyn_results(site, conn=None, close=True):
    """Returns df of the results of the dynamic confirmation."""
    # Connect to the database if no connection is passed
    if conn is None:
        conn = connect()
    column_names = ["id", "loading_time", "timed_out", "apg_url", "complete_time", "retest_num",
                    "cookies", "site", "browser_id", "events_id", "global_properties_id",
                    "object_properties_id", "test_id", "window_properties_id",
                    ]
    # Execute the "SELECT " query
    # Do not reduce_leaky_endpoints everything to category? (req_url or hash_uniq are not suited for categories)
    df = postgresql_to_dataframe(conn, f"SELECT * from dbcon_leakresult WHERE site='{site}'",
                                 column_names, non_cat=["apg_url"])
    
    if close:
        conn.close()
    return df


def add_retest_url(retest_row):
    """Get URL from apg_url and append to the retest list."""
    url = retest_row["apg_url"].split("&browser=")[0]
    browser = id_to_name[retest_row["browser_id"]]
    retest_row["browser"] = browser
    retest_row["url"] = url
    return retest_row


def get_retest_urls(df, log=False, retest_num=0):
    """Get all URLs that need a retest (worked in the first test or second test)."""
    timeout = df[df["timed_out"] == True]
    if log:
        print(f"Timeout URLs: {timeout.shape[0]}")
    df = df.drop(timeout.index)
    frame = df.loc[df["retest_num"] == retest_num].groupby(
        ["browser_id", "test_id"])[["events_id", "global_properties_id",
                                    "object_properties_id", "window_properties_id"]].agg(["nunique", "count"])
    nunique_count = 2  # How many different values a working leak method should have
    # Get all leak channels that worked
    # pot_leaks = frame[frame.filter(regex="nunique", axis=1).isin([nunique_count]).any(axis=1) & frame.filter(regex="count", axis=1).isin([2]).all(axis=1)].reset_index()
    pot_leaks = frame[frame.filter(regex="nunique", axis=1).ge(nunique_count).any(axis=1)].reset_index()
    if log:
        display(pot_leaks)
    pot = pd.DataFrame()
    for _, row in pot_leaks.iterrows():
        browser_id = row["browser_id"].values[0]
        test_id = row["test_id"].values[0]
        pot = pot.append(df.loc[(df["browser_id"] == browser_id) & (df["test_id"] == test_id)])
    # Incorrect as both conditions are compared independetly
    # pot = df.loc[(df["browser_id"].isin(pot_leaks["browser_id"])) & (df["test_id"].isin(pot_leaks["test_id"]))]
    if log:
        print(pot.shape)
    if len(pot) == 0:
        return {"firefox": [], "chrome": []}, None, None

    retest_url_frame= pot.loc[(df["cookies"] == True) & (df["retest_num"] == retest_num)][["browser_id", "apg_url"]].apply(add_retest_url, axis=1)
    retest_url_groups = retest_url_frame[["browser", "url"]].groupby("browser")
    retest = {}
    for browser, urls in retest_url_groups:
        retest[browser] = urls["url"].to_list()

    if log:
        print(retest["firefox"][:10], len(retest["firefox"]))
    return retest, pot, pot_leaks


def merge_dfs(res, conn):
    """Merge the leak_result table with the corresponding entries for the observation tables."""
    ef = get_ef(conn)
    of = get_of(conn)
    gf = get_gf(conn, non_cat=["gp_window_postMessage"])
    wf = get_wf(conn)
    res = res.merge(ef, how="left", on="events_id")
    res = res.merge(gf, how="left", on="global_properties_id")
    res = res.merge(of, how="left", on="object_properties_id")
    res = res.merge(wf, how="left", on="window_properties_id")
    return res


def to_int_save(value):
    """Converts string to int, returns -1 if no int."""
    try:
        return int(value)
    except ValueError:
        return -1


def check_empty(values_cookies, values_no_cookies, negative_values, method=lambda x,y: x in y, convert=lambda x: x):
    """Returns True if one mode only returns negative values and the other does not return negative values.
    
    value_cookies: Series, results of run with cookies
    value_no_cookies: Series, results of run without cookies
    negative_values: list, results that count as negative
    method: function(val, negative_values), function to check if the value is negative or not, default: in
    convert: functiont(val), function to convert value first, default: id
    """
    negative_cookies = sum([method(convert(val), negative_values) for val in values_cookies.values])
    negative_no_cookies = sum([method(convert(val), negative_values) for val in values_no_cookies.values])
    # If in total two results are negative, and they can't be equal, it can only be two negative values and 0 negative values
    return sum([negative_cookies, negative_no_cookies]) == 2 and negative_cookies != negative_no_cookies


def check_method(method, method_cookies, method_no_cookies, log):
    """Check if a leak method is exploitable, when it is unclear
    
    method is a string representing a leak method, e.g., gp_window_postMessage
    method_cookies is a pandas Dataframe with two results for the runs with cookies
    method_no_cookies is a pandas Dataframe with two results for the runs without cookies
    
    To get here, either both cookies/no-cookies returned two different results or one got two different results and the other only one
    If the method obviously works:
        - both cookies/no-cookies are different and the same for both runs
    Or obviously does not work:
        - both cookies/no-cookies are the same and the same for both runs
        - one of cookies/no-cookies is the same for both runs and the other mode has this value once
    This function is not reached as the method is already marked as working/not-working.
    Here, edge cases are handled:
    e.g., op_frame_count should count as working, if one mode returns 0 frames in both runs and the other mode a random number != 0.
    """
    if method == "event_set":
        # Check for event_set smooth
        # One mode has error in both runs, the other has no errors
        count_error = len(method_cookies.str.contains("error")), len(method_no_cookies.str.contains("error"))
        if sum(count_error) == 2 and count_error[0] != count_error[1]:
            return True
        # One mode has load in both runs, the other has not
        count_load = len(method_cookies.str.contains("load")), len(method_no_cookies.str.contains("load"))
        if sum(count_load) == 2 and count_load[0] != count_load[1]:
            return True
        else:
            # One mode only got no results, the other got results
            return check_empty(method_cookies, method_no_cookies, ["[]"])
        
    elif method == "event_list":
        # Special cases already handled in "event_set"
        return False
    
    elif method == "load_count":
        # Check for only 0 once
        return check_empty(method_cookies, method_no_cookies, [0])
    
    elif method == "gp_securitypolicyviolation":
        # Exceptions/Violations occured in one mode only
        return check_empty(method_cookies, method_no_cookies, ["js-undefined"])
    
    elif method == "gp_window_postMessage":
        post_message_count_c = len(method_cookies.iloc[0].split(",")), len(method_cookies.iloc[1].split(","))
        post_message_count_n = len(method_no_cookies.iloc[0].split(",")), len(method_no_cookies.iloc[1].split(","))
        # One mode got got no postMessages, the other did
        if (sum(post_message_count_c) == 0) ^ (sum(post_message_count_n) == 0):
            # Assert that one mode got postMessages in both runs (should not happen as we check this in group_cookies)
            assert not(any([val == 0 for val in post_message_count_c])) or not(any([val == 0 for val in post_message_count_n]))
            return True
        # Both got a different number of postMessages, but the same in both runs (exact text is different, e.g., timestamps or ids in the messages)
        if (len(set(post_message_count_c)) == 1) and (len(set(post_message_count_n)) == 1) and not (post_message_count_c[0] == post_message_count_n[0]):
            return True
        # Do some more advanced check to check that the messages between modes are different and within modes are similar (Jaro string distance?)
        else:
            return check_empty(method_cookies, method_no_cookies, ["[]"])
    
    elif method == "gp_window_onerror":
        # Only one error can be observed cross-site, so this should not return any positives
        return check_empty(method_cookies, method_no_cookies, ["[]"])
    
    elif method == "op_el_duration":
        # One is empty twice, the other non-empty twice
        return check_empty(method_cookies, method_no_cookies, ["js-NaN", "js-undefined"])
    
    elif method == "op_el_media_error":
        # One in error twice, the other no error twice
        return check_empty(method_cookies, method_no_cookies, ["js-null", "js-undefined"])
    
    elif method == "op_el_naturalHeight":
        # One is empty twice, the other not
        # With natural width, one can distinguish images that are the size of the error icon, from the error icon
        return check_empty(method_cookies, method_no_cookies, ["0", "js-undefined"])
    
    elif method == "op_el_naturalWidth":
        # One is empty twice, the other not
        return check_empty(method_cookies, method_no_cookies, ["0", "js-undefined"])
    
    elif method == "op_el_videoHeight":
        # One is empty twice, the other not
        return check_empty(method_cookies, method_no_cookies, ["0", "js-undefined"])
    
    elif method == "op_el_videoWidth":
        # One is empty twice, the other not
        return check_empty(method_cookies, method_no_cookies, ["0", "js-undefined"])
    
    elif method == "op_frame_count":
        # If one mode only got 0 frames or errors, and the other got different amount of frames each time it works
        check_all_negative = check_empty(method_cookies, method_no_cookies, ["0", "js-undefined", "Not possible"])
        # One only got erros, the other only got counts
        check_negative = check_empty(method_cookies, method_no_cookies, ["js-undefined", "Not possible"])
        # Possible improvement: one returned small count twice, the other large count twice
        return check_all_negative or check_negative
        
    elif method == "op_win_CSS2Properties":
        # Cannot work
        return False
    
    elif method == "op_win_history_length":
        # One only has ints, the other only has no ints
        check_int = check_empty(method_cookies, method_no_cookies, [], lambda x, _: x >= 0, to_int_save)
        # One only has larger 0, the other only 0 or no int
        check_larger_zero = check_empty(method_cookies, method_no_cookies, [], lambda x, _: x > 0, to_int_save)
        # One only has larger 1, the other only 0, 1 or no int
        check_larger_one = check_empty(method_cookies, method_no_cookies, [], lambda x, _: x > 1, to_int_save)
        return check_int or check_larger_zero or check_larger_one
        
    elif method == "op_win_opener":
        # Cannot work
        return False
    
    elif method == "op_win_origin":
        # Cannot work
        return False
    
    elif method == "op_win_window":
        # Cannot Work
        return False
    
    else:
        # Method that is not supported, support needs to be added
        raise NotImplemented(method)


def check_methods(group, leak_methods, log, return_all=False):
    """Check a set of leak_methods to see if the work.
    
    Group: df, 4 responses
    Leak_methods: list of string, methods to test
    log: bool, whether to display extra information
    """
    working = []
    cookie_group = group.loc[group["cookies"] == True]
    no_cookie_group = group.loc[group["cookies"] == False]
    first_row = group.iloc[0]
    browser_id = first_row["browser_id"]
    test_id = first_row["test_id"]
    apg_url = first_row["apg_url"]
    browser = first_row["browser"]
    inc_method = first_row["inc_method"]
    url = first_row["url"]
    
    for method in leak_methods:
        template = {"test_id": test_id, "browser_id": browser_id, "apg_url": apg_url, "method": method, "browser": browser, "inc_method": inc_method, "url": url}
        works, method_cookies, method_no_cookies = check_groups(cookie_group, no_cookie_group, method, log)
        # Method works
        if works:
            template["value_cookies"] = method_cookies
            template["value_no_cookies"] = method_no_cookies
            working.append(template)
        # Method specific check is necessary
        elif works is None:
            works_specific = check_method(method, method_cookies, method_no_cookies, log)
            if works_specific:
                template["value_cookies"] = method_cookies.tolist()
                template["value_no_cookies"] = method_no_cookies.tolist()
                working.append(template)
        # Does not work
        else:
            if return_all:
                try:
                    template["value_cookies"] = method_cookies.tolist()
                    template["value_no_cookies"] = method_no_cookies.tolist()
                except AttributeError as e:
                    template["value_cookies"] = method_cookies
                    template["value_no_cookies"] = method_no_cookies
                finally:                                    
                    working.append(template)

            else:
                pass
    if len(working) != 0:
        return working 
    else: 
        return []
        
        
def check_groups(cookie_group, no_cookie_group, leak_method, log):
    """Check if a leak method works.
    
    cookie_group: df, results for the run with cookies (retest=0,1)
    no_cookie_group: df, results for the run without cookies (retest=0,1)
    leak_method: string, leak method in question
    log: bool, whether to display additional information
    
    Returns <Decision>, value_cookies, value_no_cookies
    
    Decision is True, if both groups have only one result that differs
    Decision is False, if both groups share at least one result
    Decision is None, if both groups do not share a value, and at least one has more than one result
    """
    method_cookies = cookie_group[leak_method]
    method_no_cookies = no_cookie_group[leak_method]
    uniques = [method_cookies.nunique(), method_no_cookies.nunique()]
    
    # Both cookies and no-cookies only have one value
    if all(val == 1 for val in uniques):
        # The value is not the same (method works)
        # (This is the equivalent to the old strict check, only that it is one a single method and not a group)
        if method_cookies.iloc[0] != method_no_cookies.iloc[0]:
            if log:
                print(f"{leak_method} works!", method_cookies.values.tolist(), method_no_cookies.values.tolist())
            # Leak works
            return True, method_cookies.iloc[0], method_no_cookies.iloc[0]
        # If it is the same, the method can not work as all results are the same
        else:
            if log:
                print(f"{leak_method} cannot work both cookie and no-cookie have the same single value")
            # Leak cannot work
            return False, method_cookies.iloc[0], method_no_cookies.iloc[0]
    
    # At least one mode has two different values
    else:
        # Cannot work if one value occures in both modes
        for i in [0, 1]:
            for j in [0, 1]:
                if method_cookies.iloc[i] == method_no_cookies.iloc[j]:
                    if log:
                        print(f"{leak_method} cannot work one has only one value and the other one time the same!", method_cookies.values.tolist(), method_no_cookies.values.tolist())
                    # Leak cannot work
                    return False, method_cookies.iloc[0], method_no_cookies.iloc[0]
    
    # Otherwise, a method specific check is necessary
    return None, method_cookies, method_no_cookies


def check_events(group, log):
    """Check whether the events_fired leak channels worked."""
    return check_methods(group, ["event_set", "event_list", "load_count"], log)
        

def check_gps(group, log):
    """Check whether the global_properties leak channels worked."""
    # APG currently does not handle gp_window_getComputedStyle and gp_window_hasOwnProperty correctly
    # So they are not included
    return check_methods(group, ["gp_securitypolicyviolation", "gp_window_onerror", "gp_window_postMessage"], log)


def check_ops(group, log):
    """Check whether the object_properties leak channels worked."""
    return check_methods(group, ["op_el_duration", "op_el_naturalHeight", "op_el_naturalWidth", "op_el_videoHeight", "op_el_videoWidth", "op_el_media_error"], log)


def check_wps(group, log):
    """Check whether the window_properties leak channels worked."""
    return check_methods(group, ["op_frame_count", "op_win_CSS2Properties", "op_win_history_length", "op_win_opener", "op_win_origin", "op_win_window"], log)
    

def get_working_channel(group, log):
    """Return all leak channels that work for a given group.
    
    A group is one apg_url with four results. Two times with cookies, two times without.
    """
    aggs = group[["events_id", "global_properties_id", "object_properties_id", "window_properties_id"]].agg("nunique")
    working = []
    if aggs["events_id"] != 1:
        working.append(check_events(group, log=log))
    if aggs["global_properties_id"] != 1:
        working.append(check_gps(group, log=log))
    if aggs["object_properties_id"] != 1:
        working.append(check_ops(group, log=log))
    if aggs["window_properties_id"] != 1:
        working.append(check_wps(group, log=log))
    return working


def transform_to_df(working):
    """Flatten the working dataframe, for better representation."""
    res = pd.DataFrame([item for sublist in working.iloc[0][0] for item in sublist])
    return res
                     
                     
def get_working_urls_channels(df, log=False, conn=None):
    """Get all URLs that worked twice + the leak channel and result.
    
    df is the leakresult data for the site
    Returns working_df, working_dict, url_dict
    
    working_df: Dataframe with one row per working leak channel including the result (i.e., several rows per URL and inclusion method)
    working_dict: Dict.browser.url.inc_channels, for every browser and every URL, all inclusion channels that worked
    url_dict: Dict.browser.apg_urls, for every browser all apg_urls that worked
    """
    # Get APG_URLs that differed in at least one observed property for the first and second run
    _, pot1, pot_leaks1 = get_retest_urls(df, log=log, retest_num=0)
    _, pot2, pot_leaks2 = get_retest_urls(df, log=log, retest_num=1)
    # Intersection of the ones that were retested after the first run and the ones that would be retested after the second run
    # Only the tests in this intersection can work, but there can be FPs in this set
    if pot1 is None or pot2 is None:
        return pd.DataFrame(), {}, {}
    pot = pd.merge(pot1, pot2, how="inner")
    if log:
        print(f"Pot1 shape: {pot1.shape}, Pot2 shape: {pot2.shape}, Pot shape: {pot.shape}")
        display(pot)
    
    # Get detailed data for the potential leaks from the database
    pot = merge_dfs(pot, conn)  
    pot = pot.apply(add_inc_channel, only=False, axis=1)
    
    # Get all URLs that worked according to the leak oracles
    working = pd.DataFrame(pot.groupby(["test_id", "browser_id"]).apply(get_working_channel, log=log)).reset_index()
    # Transform the results to a nice representation
    working = working.groupby(["test_id", "browser_id"], group_keys=False).apply(transform_to_df)
    if log:
        display(working)
    if len(working) == 0:
        return pd.DataFrame(), {}, {}
    working["value_cookies"] = working["value_cookies"].astype("str")
    working["value_no_cookies"] = working["value_no_cookies"].astype("str")
    
    # Transform working into the two old formats
    working_dict = {}
    url_dict = {}
    browser_groups = working.groupby("browser")
    for browser, group in browser_groups:
        url_group = group.groupby("url")
        working_dict[browser] = {}
        url_dict[browser] = group["apg_url"].unique().tolist()
        for url, group in url_group:
            working_dict[browser][url] = group["inc_method"].unique().tolist()
    
    return working, working_dict, url_dict
    
    
def add_inc_channel(leak_row, only=False):
    """Adds working leak channels to the url_dict."""
    leak_url = leak_row["apg_url"]
    browser_id = leak_row["browser_id"]
    leak_url = leak_url.split("&browser")[0]
    method, url = leak_url.split("/?url=")
    method = method.split("/apg/")[1]
    browser = id_to_name[browser_id]
    
    if only:
        return method

    leak_row["browser"] = browser
    leak_row["url"] = url
    leak_row["inc_method"] = method
    return leak_row


def get_working_urls(pot, pot_leaks, log=False):
    """Get all URLs that where dynamically confirmed and still worked after the reteste."""
    # Check that the potential leak is stable (has the same result twice)
    dup = pot.duplicated(subset=["browser_id", "test_id", "events_id",
                                 "global_properties_id", "object_properties_id",
                                 "window_properties_id", "cookies"])
    dup = pot[dup].sort_values("test_id")
    # Check that the potential leak is stable for both cookies and no-cookies
    both_working = dup.groupby(["browser_id", "test_id"])["id"].count()
    both_working = both_working.loc[both_working == 2].reset_index()
    display(both_working)
    # Display all stable leaks
    dup = dup.loc[(dup["browser_id"].isin(both_working["browser_id"])) & (dup["test_id"].isin(both_working["test_id"]))]
    if log:
        print("Dup, stable leaks")
        display(dup)
    if len(dup) == 0:
        return {"firefox": [], "chrome": []}

    browser_group = dup.loc[dup["cookies"] == True][["browser_id", "apg_url"]].apply(add_inc_channel, axis=1)[["browser", "url", "inc_method", "apg_url"]].groupby("browser")
    working_dict = {}
    url_dict = {}
    for browser, group in browser_group:
        url_group = group.groupby("url")
        working_dict[browser] = {}
        url_dict[browser] = group["apg_url"].to_list()
        for url, group in url_group:
            working_dict[browser][url] = group["inc_method"].to_list()

    if log:
        print(len(url_dict.keys()), {k: v for i, (k, v) in enumerate(url_dict.items()) if i < 10})

    # Error analysis
    # postMessage seems to be a big reason for dropping URLs (might be good if indeed it was a FP or bad if not)
    if log:
        display(pot_leaks.reset_index().filter(regex="nunique", axis=1).value_counts().to_frame())
        dup_frame = dup.groupby(
            ["browser_id", "test_id"])[["events_id", "global_properties_id",
                                        "object_properties_id", "window_properties_id"]].agg(["nunique", "count"])
        display(dup_frame.reset_index().filter(regex="nunique", axis=1).value_counts().to_frame())
    return working_dict, url_dict
