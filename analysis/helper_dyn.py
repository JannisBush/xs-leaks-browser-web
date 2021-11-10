from database_connector import connect, postgresql_to_dataframe
import pandas as pd
from pandas.api.types import CategoricalDtype
import datetime
import textdistance
import difflib
import hashlib
import pickle

from dil_preprocess import get_url_data, basic_pruning
from dil_predict import init, predict_trees, reduce_leaky_endpoints
from dil_postprocess import get_working_incs, get_dyn_urls, get_working_urls_channels, get_dyn_results

def get_crawl_data():
    """Return the data from node_crawler site table."""
    conn = connect()
    column_names = ["job_id", "site_id", "site", "cookies", "counter", "crawl_status", "crawler"]
    df = postgresql_to_dataframe(conn, "select * from sites", column_names)
    conn.close()
    return df

def get_pipeline_overview():
    """Return the data from the complete pipeline."""
    # Connect to the database
    conn = connect()
    column_names = ["id", "site", "login", "cookies", "cookie_end", "num_urls", 
                    "num_basic_pruning", "num_input_rows", "crawl_end", "dyn_conf_urls", 
                    "dyn_conf_firefox", "dyn_conf_chrome", "dyn_end",
                    "dyn_conf_retest_urls", "dyn_conf_retest_firefox", "dyn_conf_retest_chrome", "dyn_retest_end",
                    "confirmed_urls", "confirmed_urls_firefox", "confirmed_urls_chrome",
                    "count", "tranco_rank", "confirmed_leak_urls", "confirmed_df_dict",
                    ]
    non_cat = ["login", "dyn_conf_urls", "dyn_conf_retest_urls", "confirmed_urls", "cookies", "confirmed_leak_urls", "confirmed_df_dict"]
    # Execute the "SELECT *" query
    site_results = postgresql_to_dataframe(conn, "select * from db_site_results", column_names, non_cat=non_cat)
    conn.close()
    return site_results


def get_leak_data():
    """Return the data from dbcon_leakresult."""
    conn = connect()
    column_names = ["id", "loading_time", "timed_out", "apg_url", "complete_time",
                    "retest_num", "cookies", "site", "browser_id", "events_id", "global_properties_id",
                    "object_properties_id", "test_id", "window_properties_id",
                    ]
    non_cat = ["cookies"]
    # Execute the "SELECT *" query
    leak_results = postgresql_to_dataframe(conn, "select * from dbcon_leakresult", column_names, non_cat=non_cat)
    conn.close()
    return leak_results


def get_isotime(iso):
    """Converts a isostr to datetime or returns None."""
    try:
        return datetime.datetime.fromisoformat(iso)
    except ValueError:
        None
        # return datetime.datetime.fromordinal(datetime.date(year=1980, month=1, day=1).toordinal()
        
        
def calc_diff(time1, time2):
    """Returns the difference between two time objects or returns None."""
    try:
        return time1 - time2
    except TypeError:
        return None
    
def get_time(row):
    """Calculate the timing of a row."""
    start = get_isotime(row["cookie_end"])
    end_crawl = get_isotime(row["crawl_end"])
    end_dyn = get_isotime(row["dyn_end"])
    end_final = get_isotime(row["dyn_retest_end"])
    return (row["site"], row["tranco_rank"], calc_diff(end_crawl, start), calc_diff(end_dyn, end_crawl), calc_diff(end_final, end_dyn))


def display_timing(df):
    """Calculate and display information on timimg."""
    time_crawl = df.loc[df["crawl_end"] != ""].apply(get_time, axis=1, result_type="expand")
    time_crawl = time_crawl.rename(columns={0: "site", 1: "tranco_rank", 2: "crawling time", 3: "dynamic confirmation time", 4: "dynamic reconfirmation time"})
    display(time_crawl)  # if time is over 9 hours, this could be because of a bug in our pipeline: e.g., ning, chess and vimeo
    display(time_crawl.agg(["min", "max", "mean", "std"]))

    
def get_cookie_stats(row):
    """Row has a column cookies with a list of cookie dicts.
       Every entry in the list will get transformed to one row in a df that is returned.
    """
    try:
        cookies = row.iloc[0]["cookies"]
    except IndexError:
        return None
    if type(cookies) == list:
        cookie_count = len(cookies)
        row["name"] = "Not set"
        row["value"] = "Not set"
        row["secure"] = "Not set"
        row["httpOnly"] = "Not set"
        row["sameSite"] = "Not set"
        row = row.loc[row.index.repeat(cookie_count)]
        for count, cookie in enumerate(cookies):
            row["name"].iloc[count] = cookie["name"]
            row["value"].iloc[count] = cookie["value"]
            row["secure"].iloc[count] = cookie.get("secure", "Not set")
            row["httpOnly"].iloc[count] = cookie.get("httpOnly", "Not set")
            row["sameSite"].iloc[count] = cookie.get("sameSite", "Not set")
            # Collect stats for each cookie, guess if session cookie (regex on Name + nature of value?), record security attributes (how many use sameSite, etc)
            # Later see if there is a relation between vulnerable sites and the cookie settings of these sites?!
            # print(cookie["name"], cookie["value"], cookie.get("secure", "Not set"), cookie.get("httpOnly", "Not set"), cookie.get("sameSite", "Not set"))
    return row


def show_only_first(df1, df2, info, head=3):
    """Show all rows only existing in the first df, both frames have a column: id."""
    c = df1.merge(df2, on="id")
    res = df1.loc[~df1.id.isin(c.id)]
    if len(res) > 0:
        print(f"{info} for {len(res)} sites")
        with pd.option_context("max_columns", None):
            display(res.head(head))
    return res


def get_pipeline_stats(df, log=True):
    """Df is a (sub)frame of db_site_results.
       Get info of how many sites went missing in the various steps.
    """
    cookies_found = df.loc[df["cookies"] != {}]
    pipeline_started = df.loc[df["login"].str.contains(r"pipepline|actual site")]
    started_cookie_hunter = df.loc[df["login"].str.contains("pipepline")]
    started_manual = df.loc[df["login"].str.contains("actual site")]
    
    # Add the ones that failed in the unpruned run ("Bug": we update the wrong cookiehunter entries for the unpruned runs, so we need to do this)
    pipeline_started = pipeline_started.append(df.loc[df["site"].isin(["bravenet.com", "amazon.in", "faucetcrypto.com", "bshare.cn"])])
    cookies_found = cookies_found.append(df.loc[df["site"].isin(["bravenet.com", "amazon.in", "faucetcrypto.com", "bshare.cn"])])
    started_cookie_hunter = started_cookie_hunter.append(df.loc[df["site"].isin(["bravenet.com", "amazon.in", "faucetcrypto.com", "bshare.cn"])])
    
    crawled = df.loc[df["crawl_end"] != ""]
    crawled_min = df.loc[df["num_urls"] >= 1]
    crawled_success = df.loc[df["num_urls"] >= 3]
    pruned = df.loc[df["num_basic_pruning"] > 0]
    num_input_rows = df.loc[df["num_input_rows"] > 0]

    pot_ft = df.loc[df["dyn_conf_firefox"] > 0]
    pot_ct = df.loc[df["dyn_conf_chrome"] > 0]
    pot = df.loc[df["id"].isin(list(set(pot_ft["id"].values.tolist()) | set(pot_ct["id"].values.tolist())))]
    pot_both = df.loc[df["id"].isin(list(set(pot_ft["id"].values.tolist()) & set(pot_ct["id"].values.tolist())))]

    pot_fr = df.loc[df["dyn_conf_retest_firefox"] > 0]
    pot_cr = df.loc[df["dyn_conf_retest_chrome"] > 0]
    pot_r = df.loc[df["id"].isin(list(set(pot_fr["id"].values.tolist()) | set(pot_cr["id"].values.tolist())))]
    pot_r_both = df.loc[df["id"].isin(list(set(pot_fr["id"].values.tolist()) & set(pot_cr["id"].values.tolist())))]

    conf_f = df.loc[df["confirmed_urls_firefox"] > 0]
    conf_c = df.loc[df["confirmed_urls_chrome"] > 0]
    conf = df.loc[df["id"].isin(list(set(conf_f["id"].values.tolist()) | set(conf_c["id"].values.tolist())))]
    conf_both = df.loc[df["id"].isin(list(set(conf_f["id"].values.tolist()) & set(conf_c["id"].values.tolist())))]

    info_text = (
        f"Cookiehunter:\n"
        f"Total sites attempted: {len(df)}, some success (cookies collected): {len(cookies_found)}, full success (pipeline started): {len(pipeline_started)}\n"
        f"Pipeline started cookiehunter: {len(started_cookie_hunter)}, started selenium login replay: {len(started_manual)}\n"
        f"\nCrawling:\n"
        f"Crawl started: {len(crawled)}, at least one URL crawled: {len(crawled_min)}, at least three URLs crawled: {len(crawled_success)}\n"
        f"\nPruning:\n"
        f"At least one URL remains after basic pruninng: {len(pruned)}, at least one input row for trees: {len(num_input_rows)}\n"
        f"Trees:\n"
        f"At least one potential vulnerable firefox: {len(pot_ft)}, at least one potential vulnerable chrome: {len(pot_ct)}\n"
        f"At least one potential vulnerable either: {len(pot)}, at least one potential vulnerable both: {len(pot_both)}\n"
        f"\nSingle confirmation:\n"
        f"At least one different observation firefox: {len(pot_fr)}, at least one different observation chrome: {len(pot_cr)}\n"
        f"At least one different observation either: {len(pot_r)}, at least one different observation both: {len(pot_r_both)}\n"
        f"\nDouble confirmation:\n"
        f"At least one vulnerable firefox: {len(conf_f)}, at least one vulnerable chrome: {len(conf_c)}\n"
        f"At least one vulnerable either: {len(conf)}, at least one vulnerable both: {len(conf_both)}\n"
    )
    if log:
        print(info_text)
    
    
    # Sanity checks, should not occur
    show_only_first(pipeline_started, cookies_found, "Started without cookies")
    show_only_first(pipeline_started, crawled, "Started but not crawled")
    show_only_first(crawled_min, crawled, "Crawl check")
    show_only_first(crawled_success, crawled_min, "Crawl check")
    show_only_first(pruned, num_input_rows, "No input rows after pruning")

    if log:
        print("For some sites our testing infrastructure was partially down during testing (67 sites), after the infrastructure was ready again. We retested but for 21 the login failed (e.g., google SSO changed behavior in between and does not allow selenium anymore). We remove these from the following test")
    cookie_hunter_second_failed = show_only_first(crawled, pipeline_started, "Crawled without started", 21)
    
    # Remove the sites that failed a second login, and did never got tested properly
    df = df.loc[~df.index.isin(cookie_hunter_second_failed.index)]
    
    # Interesting cases
    if log:
        show_only_first(crawled, crawled_min, "Not crawled properly (e.g., cert error)")
        show_only_first(pot, crawled_success, "Potential vulnerable with less than 3 URLs crawled")
        show_only_first(crawled_min, pruned, "Crawled but excluded after basic pruning")
        show_only_first(num_input_rows, pot, "No potential leaks after tree pruning")
        show_only_first(pot, pot_r, "No observed difference in potential URLs")
        show_only_first(pot_r, conf, "No confirmed URLs after retesting")
        show_only_first(conf_f, conf_c, "Only in firefox confirmed")
        show_only_first(conf_c, conf_f, "Only in chrome confirmed")
    
    
    return df, conf_both, conf


sec_rel_headers = [
    "content-type",
    "x-frame-options",
    "content-disposition",
    "cross-origin-opener-policy",
    "x-content-type-options",
    "cross-origin-resource-policy",
    "content-security-policy",  
    "location",
]

to_test = sec_rel_headers + ["code"]

acc = {}
def process_responses(row):
    """Get only the relevant data from the crawl."""
    global acc
    headers = row["resp_headers"]  # All headers in the db are saved as lowercase
    sec_df = {}
    sec_df["url"] = row["req_url"]
    sec_df["site"] = row["site"]
    sec_df["real_site"] = row["real_site"]
    sec_df["cookies"] = row["cookies"]
    sec_df["code"] = row["resp_code"]
    sec_df["body"] = row["resp_body_hash"]
    headers_basic_pruned = {}
    for header in sec_rel_headers:
        header_val = headers.get(header, "Empty") 
        # Remove some info from headers here to deduplicate (e.g., filename in content-disposition?)
        if header == "content-disposition":
            header_val = header_val.split(";")[0]
        # Add post-processing for CSP
        sec_df[header] = header_val
        if not header == "content-security-policy":
            headers_basic_pruned[header] = header_val
    for header in headers:
        count = acc.get(header, 0)
        acc[header] = count + 1
        
    # Calculate hashes of the responses, either hash everything, remove some headers including randomness or only keep the tree headers (basic pruning)
    hash_all = [sec_df["url"], sec_df["site"], sec_df["code"], headers, sec_df["body"]]
    headers_min_pruned = headers.copy()
    for header in ["date", "server", "cache-control", "last-modified", "etag", "vary", "expires", "age"]:
        headers_min_pruned.pop(header, None)
    hash_min_pruned = [sec_df["url"], sec_df["site"], sec_df["code"], headers_min_pruned, sec_df["body"]]
    hash_basic_pruned = [sec_df["url"], sec_df["site"], sec_df["code"], headers_basic_pruned, sec_df["body"]]

    sec_df["hash_all"] = hashlib.sha1(pickle.dumps(hash_all)).hexdigest()
    sec_df["hash_min_pruned"] = hashlib.sha1(pickle.dumps(hash_min_pruned)).hexdigest()
    sec_df["hash_basic_pruned"] = hashlib.sha1(pickle.dumps(hash_basic_pruned)).hexdigest()
    
    return sec_df

def get_acc():
    global acc
    return acc
    
    
def display_response_summary(df, index="cookies", check=None):
    """Display response groups."""
    if check is None:
        global to_test
        to_check = to_test.copy()
        to_check.remove("content-security-policy")
    else:
        to_check = check
    table_dict = {}
    with pd.option_context("max_columns", 200):
        display(df.groupby(index).nunique())
        for prop in to_check:
            pivot = df.pivot_table(index=index, columns=prop, aggfunc="size", fill_value=0)
            pivot.loc["Total"] = pivot.sum()
            res = pivot.loc[:, pivot.max().sort_values(ascending=False).index]
            display(res)
            table_dict[prop] = res
            # display(df[prop].value_counts().to_frame())
        pivot = df.pivot_table(index=index, columns=to_check, aggfunc="size", fill_value=0)
        pivot.loc["Total"] = pivot.sum()
        res = pivot.loc[:, pivot.max().sort_values(ascending=False).index]
        res
        display(res)
        table_dict["total"] = res
    return table_dict
        


def display_changed(df):
    """Display rows where different headers/status-code are observed for cookies/no-cookies"""
    # Drop the ones with only one or more than two observations
    count_urls = df.groupby(["url", "site", "real_site"])["cookies"].count()
    display(count_urls.value_counts())
    count_index = count_urls[count_urls == 2].index
    df = df.set_index(["url", "site", "real_site"])
    df = df.loc[count_index]
    df = df.reset_index()
    print(df.info())
    
    # Drop the ones that are the same for cookies/no-cookies
    df = df.drop_duplicates(subset=to_test + ["url", "site", "real_site"], keep=False)
    
    # Display remaining ones
    display(df.sort_values(["site", "real_site", "url", "cookies"]))
    
    
def parse_apg_url(apg_url):
    """Return the method, url and browser from an apg_url."""
    method = apg_url.split("/apg/")[1].split("/?url=")[0]
    url = apg_url.split("/?url=")[1].split("&browser")[0]
    try:
        browser = apg_url.split("&browser=")[1].split("&")[0]
    except IndexError:
        browser = None
    return method, url, browser

    
def parse_method_url(row, col, acc):
    """Get URL, method and browser from the apg url."""
    row_dict = row[col]
    site = row["site"]
    if type(row_dict) == dict:
        browser_l = []
        method_l = []
        url_l = []
        l = []
        for browser in row_dict:
            for apg_url in row_dict[browser]:
                method = apg_url.split("/apg/")[1].split("/?url=")[0]
                url = apg_url.split("/?url=")[1]
                browser_l.append(browser)
                method_l.append(method)
                url_l.append(url)
                l.append([browser, method, url])
                acc.append({"site": site, "browser": browser, "method": method, "url": url})
        return [browser_l, method_l, url_l]
    
    
def get_query(string, pos=1):
    """Get query parameter of a URL."""
    try:
        return string.split("?")[pos]
    except IndexError:
        if pos == 1:
            return ""
        else:
            return string

    
def info_grouping(grouping, info, info_frame, info_frame_new, log=False):
    for key, group in grouping:
        f = group.loc[group["browser"] == "firefox"]
        c = group.loc[group["browser"] == "chrome"]
        if log:
            print(f"Grouping: {key}, number vuln: {len(group)}, chrome: {len(c)}, firefox: {len(f)}")
            display(group.head())
            
        leak_url_dict = {}
        leak_url_set = leak_url_dict, set(f[["site", "inc_method", "url"]].drop_duplicates().itertuples(index=False, name=None)), set(c[["site", "inc_method", "url"]].drop_duplicates().itertuples(index=False, name=None))
                
        leak_channel_dict = {}
        leak_channel_set = leak_channel_dict, set(f[["site", "inc_method", "method", "url"]].drop_duplicates().itertuples(index=False, name=None)), set(c[["site", "inc_method", "method", "url"]].drop_duplicates().itertuples(index=False, name=None))
        
        site_dict = {}
        site_set = site_dict, set(f["site"].unique()), set(c["site"].unique())
        
        url_dict = {}
        url_set = url_dict , set(f["url"].unique()), set(c["url"].unique())
        
        urlb_dict = {}
        urlb_set = urlb_dict, set(f["url_base"].unique()), set(c["url_base"].unique())
        
        for (dic, fs, cs) in [site_set, url_set, urlb_set, leak_url_set, leak_channel_set]:
            dic["both"] = list(fs & cs)
            dic["combined"] = list(fs | cs)
            dic["only_one"] = list(fs ^ cs)
        
        leak_urls_browser = group.groupby(["url", "inc_method", "browser"]).ngroups
        #print(len(leak_url_dict["combined"]), len(leak_url_dict["both"]), len(leak_url_dict["only_one"]), len(leak_url_set[1]), len(leak_url_set[2]))
        #print(len(leak_channel_dict["combined"]), len(leak_channel_dict["both"]), len(leak_channel_dict["only_one"]), len(leak_channel_set[1]), len(leak_channel_set[2]))

        info_frame.loc[len(info_frame)] = [info, key, len(leak_url_dict["combined"]), len(c), len(f), c["site"].nunique(), f["site"].nunique(), group["site"].nunique()]
        info_frame_new.loc[len(info_frame_new)] = [info, key, len(leak_url_dict["combined"]), len(leak_url_dict["both"]), len(leak_url_dict["only_one"]), len(leak_url_set[1]), len(leak_url_set[2]), len(url_dict["combined"]), len(url_dict["both"]), len(url_dict["only_one"]), len(url_set[1]), len(url_set[2]), len(urlb_dict["combined"]), len(urlb_dict["both"]), len(urlb_dict["only_one"]), len(urlb_set[1]), len(urlb_set[2]), len(site_dict["combined"]), len(site_dict["both"]), len(site_dict["only_one"]), len(site_set[1]), len(site_set[2]), len(leak_channel_dict["combined"]), len(leak_channel_dict["both"]), len(leak_channel_dict["only_one"]), len(leak_channel_set[1]), len(leak_channel_set[2])] 
        
        # Look at manual anlaysis.ipynb: 
        # e.g., check if the inc method was even tested/retested for the specific URL
        # was the inc_method excluded from tree pruning or from the retest (or from the second retest)
        # if inc_method was not tested in browser -> edge cases that does only work in one browser (according to our trees/R1)
        # if inc_method was tested in chrome, but not retested -> might be due to SameSite
        # if inc_method was tested and retested in other browser, but did not work -> might be either that leak is unstable in general (pM?) or in one browser (load on embed and co in chrome?)
        
    return info_frame, info_frame_new

        
def row_sym(row):
    """Calculates the simmilarity between the value_cookies and value_no_cookies."""
    return textdistance.jaro.normalized_similarity(row["value_cookies"], row["value_no_cookies"])


def get_distances(df):
    """Shows the edits between two postMessages."""
    for _, row in df.loc[df["method"] == "gp_window_postMessage"].iterrows():
        cases = [(row["value_cookies"], row["value_no_cookies"])]
        for a, b in cases:     
            print('{} => {}'.format(a,b))  
            for i,s in enumerate(difflib.ndiff(a, b)):
                if s[0]==' ': continue
                elif s[0]=='-':
                    print(u'Delete "{}" from position {}'.format(s[-1],i))
                elif s[0]=='+':
                    print(u'Add "{}" to position {}'.format(s[-1],i))    
            print()
            
def get_conf_dfs(df, log=False):
    """Df is info df, return the collection of dfs in the confirmed_df_dict column with some extra information."""
    df_all = pd.DataFrame()
    for _, row in df.iterrows():
        site = row["site"]
        try:
            df_frame = pd.DataFrame(row["confirmed_df_dict"])
            # Fix old data, that has no confirmed_df_dict
            if len(df_frame) == 0:
                print(site)  # technologyreview is not vulnerable according to our new definition of "same"
                df_frame, _, _ = get_working_urls_channels(get_dyn_results(site))
            df_frame["site"] = site
            df_frame["url_len"] = df_frame["url"].str.len()
            df_frame["url_query"] = df_frame["url"].apply(get_query)
            df_frame["url_base"] = df_frame["url"].apply(get_query, pos=0) # Only the base of the URL without query parameters (maybe the same URL was found vulnerable several times with different query parameters)
            df_frame["url_query_len"] = df_frame["url_query"].str.len()
            df_frame["jaro"] = df_frame.apply(row_sym, axis=1)
            # display(df_frame.sort_values(["url_len", "url", "inc_method", "method", "browser"]).head())
            df_chrome = df_frame.loc[df_frame["browser"] == "chrome"]
            df_firefox = df_frame.loc[df_frame["browser"] == "firefox"]
            df_all = df_all.append(df_frame)
            if log:
                print(f"{df_frame['url'].nunique()} unique URLs, total vuln: {len(df_frame)}, chrome vuln: {len(df_chrome)}, firefox vuln: {len(df_firefox)}")
        except KeyError as e:
            print(f"Error: {e}")   
            display(site)
    return df_all

def remove_leak_urls(row, dyn_conf_data):
    url = row["url"]
    method = row["inc_method"]
    site = row["site"]
    nogroup = "nogroup"
    
    in_chrome = True if (method, url, "chrome", site, nogroup) in dyn_conf_data else False
    in_firefox = True if (method, url, "firefox", site, nogroup) in dyn_conf_data else False

    if in_chrome and in_firefox:
        return 2
    elif in_chrome or in_firefox:
        return 1
    else:
        assert False, row


def get_info_frames(df_all, leak_set=None, leave=[1, 2], conv_method=False):
    """Get the most important results in two info frames"""
    # Remove rows?!
    df_all = df_all.copy()
    if leak_set is not None:
        df_all["in"] = df_all.apply(remove_leak_urls, dyn_conf_data=leak_set, axis=1)
        df_all = df_all.loc[df_all["in"].isin(leave)]  # Only leave leak channels that were tested in both browsers ([2]), in only one browser ([1]) or do nothing ([1, 2])
        
    # Convert leak method to category
    if conv_method:
        # Remove the ones that are pruned in the attack page already?
        method_cats = CategoricalDtype(categories=["event_set", "event_list", "load_count", "gp_download_bar_height", "gp_securitypolicyviolation", "gp_window_getComputedStyle", "gp_window_hasOwnProperty", "gp_window_onblur", "gp_window_onerror", "op_el_buffered", "op_el_contentDocument", "op_el_duration", "op_el_height", "op_el_media_error", "op_el_naturalHeight", "op_el_naturalWidth", "op_el_networkState", "op_el_paused", "op_el_readyState", "op_el_seekable", "op_el_sheet", "op_el_videoHeight", "op_el_videoWidth", "op_el_width", "op_frame_count", "op_win_CSS2Properties", "op_win_history_length", "op_win_opener", "op_win_origin", "op_win_window"], ordered=True)
        df_all["method"] = df_all["method"].astype(method_cats)
    
    
    inc_methods = df_all.groupby("inc_method")
    leak_methods = df_all.groupby("method")
    df_all["group_key_fake"] = "browsers"
    browsers = df_all.groupby("group_key_fake")
    leak_channels = df_all.groupby(["inc_method", "method"])
    sites = df_all.groupby("site")
    inc_sites = df_all.groupby(["site", "inc_method"])

    info_frame = pd.DataFrame(columns=["type", "subtype", "leak urls", "chrome_channels", "firefox_channels", "chrome_sites", "firefox_sites", "sites"])
    info_frame_new = pd.DataFrame(columns=["type", "subtype", "confirmed leak URLs any browser", "confirmed leak URLs both browsers", "confirmed leak URLs only one browser", "confirmed leak URLs firefox", "confirmed leak URLs chrome", "confirmed URLs any browser", "confirmed URLs both browsers",
                                           "confirmed URLs  only one browser", "confirmed URLs firefox", "confirmed URLs chrome",
                                           "confirmed base URLs browser", "confirmed base URLs both browsers",
                                           "confirmed base URLs only one browser", "confirmed base URLs firefox", "confirmed base URLs chrome",
                                           "confirmed sites any browser", "confirmed sites both browsers", "confirmed sites only one browser",
                                           "confirmed sites firefox", "confirmed sites chrome",
                                           "confirmed channels any browser", "confirmed channels both browser", "confirmed channels only one browser", "confirmed channels firefox", "confirmed channels chrome"])

    info_frame, info_frame_new = info_grouping(browsers, "browsers", info_frame, info_frame_new)
    info_frame, info_frame_new = info_grouping(inc_methods, "inc_methods", info_frame, info_frame_new)
    info_fame, info_frame_new = info_grouping(leak_methods, "leak_methods", info_frame, info_frame_new)
    info_fame, info_frame_new = info_grouping(leak_channels, "leak_channels", info_frame, info_frame_new)
    info_fame, info_frame_new = info_grouping(sites, "sites", info_frame, info_frame_new)
    info_fame, info_frame_new = info_grouping(inc_sites, "inc_sites", info_frame, info_frame_new)

    
    return info_frame, info_frame_new


def get_only_both(df_dict, keys=("chrome", "firefox"), log=False):
    """Get info on entries only in one, in both and combined.
       df_dict: dict with keys chrome and firefox, with list as values."""
    try:
        c_set = set(df_dict[keys[0]].itertuples(index=False, name=None))
    except KeyError:
        c_set = set()
    try:
        f_set = set(df_dict[keys[1]].itertuples(index=False, name=None))
    except KeyError:
        f_set = set()
    
    both = list(c_set & f_set)
    combined = list(c_set | f_set)
    only_one = list(c_set ^  f_set)
    only = {keys[0]: [], keys[1]: []}
    for entry in only_one:
        try:
            key = keys[0] if entry in c_set else keys[1]
        except KeyError:
            key = keys[1]
        only[key].append(entry)
    
    first = len(c_set)
    second = len(f_set)
    combined = len(combined)
    both = len(both)
    only_first = len(only[keys[0]])
    only_second = len(only[keys[1]])
    
    if log:
        print()
        print(f"{keys[0]}: {first}, {keys[1]}: {second}")
        print(f"Combined: {combined}")
        print(f"Both: {both}")
        #display(both)
        print(f"Only in one: {len(only_one)}, {keys[0]}: {only_first}, {keys[1]}: {only_second}")
        # display(only)
        df0 = pd.DataFrame(only[keys[0]])
        df0["key"] = keys[0]
        df1 = pd.DataFrame(only[keys[1]])
        df1["key"] = keys[1]
        return df0.append(df1)
    
    return first, second, combined, both, only_first, only_second



def url_list_to_tuples(l, sites, site_cat=False):
    """Convert a list of leak url dicts to list of tuples."""
    df_list = []
    for apg_dict, site in zip(l, sites):
        if apg_dict is None:
            continue
        for browser in apg_dict:
            for url in apg_dict[browser]:
                method, url, _ = parse_apg_url(url)
                # df_list.append({"method": method, "url": url, "browser": browser})
                df_list.append((method, url, browser, site, "nogroup"))
    # df = pd.DataFrame(df_list)
    # print(df_list[:5])
    df = pd.DataFrame(df_list, columns=["method", "url", "browser", "site", "nogroup"]).sort_values(["browser", "method", "site", "url"])
    method_cats = CategoricalDtype(categories=['audio', 'embed', 'embed-img', 'iframe', 'iframe-csp', 'img', 'link-prefetch', 'link-stylesheet', 'object', 'script', 'video', 'window.open'], ordered=True)
    if site_cat:
        site_cats = CategoricalDtype(categories=['pier1.com-unpruned', 'chartink.com-unpruned', 'pdffiller.com-unpruned', 'staples.ca-unpruned', 'freelogodesign.org-unpruned', 'duplichecker.com-unpruned', 'miro.com-unpruned', 'mnml.la-unpruned', 'redtube.com-unpruned', 'whatfontis.com-unpruned', 'glosbe.com-unpruned', 'wideads.com-unpruned', 'standardmedia.co.ke-unpruned', 'gyazo.com-unpruned', 'megogo.net-unpruned', 'zennioptical.com-unpruned', 'powtoon.com-unpruned', 'italki.com-unpruned', 'themehorse.com-unpruned', 'versobooks.com-unpruned', 'yourstory.com-unpruned', 'korrespondent.net-unpruned', 'transifex.com-unpruned', 'ankiweb.net-unpruned', 'iplocation.net-unpruned', 'youporn.com-unpruned', 'tmj4.com-unpruned', 'nimbusweb.me-unpruned', 'classifiedads.com-unpruned', 'myvidster.com-unpruned', 'cafepress.com-unpruned', 'pakwheels.com-unpruned', 'idntimes.com-unpruned', 'mhthemes.com-unpruned', 'universe.com-unpruned', 'aboutus.com-unpruned'], ordered=True)
        df["site"] = df["site"].astype(site_cats)
        
    browser_cats = CategoricalDtype(categories=["firefox", "chrome"], ordered=True)
    df["method"] = df["method"].astype(method_cats)
    df["browser"] = df["browser"].astype(browser_cats)
    return df


def get_predictions_retroactive(df, methods="limited"):
    """Returns the tree predictions for a every site in a df."""
    init(methods)
    predicted_leak_urls = []
    for site in df["site"].tolist():
        dat = get_url_data(site)
        af, d, poss, results = basic_pruning(dat)
        if af is None:
            urls = {}
        else:
            leaky_endpoints = predict_trees(af)
            if leaky_endpoints == {}:
                urls = {}
            else:
                leaks = reduce_leaky_endpoints(leaky_endpoints)
                incs = get_working_incs(leaks)
                urls = get_dyn_urls(leaks, incs, d, poss)
        predicted_leak_urls.append(urls)
    return predicted_leak_urls


def get_combs_after_basic_pruning(df):
    leak_urls = []
    for site in df["site"].tolist():
        dat = get_url_data(site)
        af, d, poss, results = basic_pruning(dat)
        if af is None:
            urls = {}
        else:
            urls = get_dyn_urls(None, None, poss, None, unpruned=True)
        leak_urls.append(urls)
    return leak_urls 


def get_basic_pruning_reduction(row):
    """Return the size reduction from basic pruning"""
    return save_div(row["num_urls"] - row["num_basic_pruning"], row["num_urls"], ret=None)


def save_div(a, b, ret=0):
    """Division without 0 error, ret is returned instead."""
    if b == 0:
        return ret
    return a/b

def get_stats(ground_truth, predicted_trees, all_combinations, info):
    """Calculate and display the pruning false negative data."""
    res = {}
    for group_key in [["nogroup"], ["method"], ["browser"], ["site"]]:  #, ["browser", "method"]]:    # Not working as not every group exist
        try:
            gts  = ground_truth.groupby(group_key)
            preds = predicted_trees.groupby(group_key)
            all_combs = all_combinations.groupby(group_key) 
            df = pd.DataFrame()
            for (name, gt), (_, pred), (_, all_comb) in zip(gts, preds, all_combs):
                gt_len, pred_len, _, tp_len, fn_len, fp_len  = get_only_both({"ground_truth": gt, "predicted_trees": pred}, ("ground_truth", "predicted_trees"))

                all_comb_len = all_comb.drop_duplicates().shape[0]
                gn_len = all_comb_len - gt_len

                size_red = save_div(all_comb_len, pred_len)
                fnr = save_div(fn_len, gt_len)
                fpr = save_div(fp_len, gn_len)
                tn_len = all_comb_len - pred_len - fn_len

                res_line = [(name, gt_len, all_comb_len, pred_len, size_red, fnr, fpr, tp_len, fn_len, fp_len, tn_len)]
                columns = ["grouping", "gt", "all_comb", "pred", "size_red", "fnr", "fpr", "tp", "fn", "fp", "tn"]
                df = df.append(pd.DataFrame(res_line, columns=columns))
                if len(df) > 1:
                    pass
                    # df.loc["Mean"] = df.mean()

            res[str(group_key)] = df
        except KeyError as e:
            print(e)


    # Get size difference in all_combinations/predicted_trees/predicted_trees_all
    for entry in res:
        print(info)
        with pd.option_context("max_columns", None):
            print(entry)
            display(res[entry])
            # display(res[entry].describe())
    return res

            
def calc_info_frames(site_results_filtered, remove_multiple=None):
    """Return the info frames for the input."""
    dat, conf_both, conf_any = get_pipeline_stats(site_results_filtered, log=False)
    df_all = get_conf_dfs(conf_any)
    if remove_multiple:
        url_by_leak = df_all.groupby(["browser", "url"])[["method", "inc_method"]].nunique()
        only_one_inc = set(url_by_leak.loc[url_by_leak[remove_multiple] == 1].reset_index()[["browser", "url"]].itertuples(name=None, index=False))
        df_all = df_all.loc[df_all[["browser", "url"]].apply(lambda x: (x["browser"], x["url"]) in only_one_inc, axis=1)]
    
    sites = dat["site"].tolist()
    leak_urls = url_list_to_tuples(dat["dyn_conf_urls"].tolist(), sites)
    leak_url_set = set(list(leak_urls.itertuples(name=None, index=None)))
    # Complete frame
    info_frame, info_frame_new = get_info_frames(df_all, None)
    # Prune all leak URLs only tested in one browser
    info_frame_both, info_frame_new_both = get_info_frames(df_all, leak_url_set, leave=[2])
    # Prune all leak URLs tested in both browsers
    info_frame_only, info_frame_new_only = get_info_frames(df_all, leak_url_set, leave=[1])
    return (info_frame, info_frame_new), (info_frame_both, info_frame_new_both), (info_frame_only, info_frame_new_only)