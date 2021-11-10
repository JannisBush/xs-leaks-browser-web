import pickle
#import ray
#ray.init(ignore_reinit_error=True)
#import modin.pandas as pd
import pandas as pd
from database_connector import connect, postgresql_to_dataframe



def get_ef(connection=None, log=False):
    if connection is None:
        conn = connect()
    else:
        conn = connection
    column_names = ["events_id", "event_set", "event_list", "load_count",
                    ]
    # Execute the "SELECT *" query
    ef = postgresql_to_dataframe(conn, "select * from dbcon_events", column_names)
    if connection is None:
        conn.close()
    if log:
        display(ef.info())
    return ef


def get_gf(connection=None, log=False, non_cat=None):
    if connection is None:
        conn = connect()
    else:
        conn = connection
    column_names = ["global_properties_id", "gp_window_onerror", "gp_window_onblur", "gp_window_postMessage", "gp_window_getComputedStyle",
                    "gp_window_hasOwnProperty", "gp_download_bar_height", "gp_securitypolicyviolation",
                    ]
    # Execute the "SELECT *" query
    gf = postgresql_to_dataframe(conn, "select * from dbcon_globalproperties", column_names, non_cat=non_cat)
    if connection is None:
        conn.close()
    if log:
        gf.info()
    return gf


def get_of(connection=None, log=False):
    if connection is None:
        conn = connect()
    else:
        conn = connection
    column_names = ["object_properties_id", "op_el_height", "op_el_width", "op_el_naturalHeight", "op_el_naturalWidth",
                    "op_el_videoWidth", "op_el_videoHeight", "op_el_duration", "op_el_networkState",
                    "op_el_readyState", "op_el_buffered", "op_el_paused", "op_el_seekable",
                    "op_el_sheet", "op_el_media_error", "op_el_contentDocument"
                    ]
    # Execute the "SELECT *" query
    of = postgresql_to_dataframe(conn, "select * from dbcon_objectproperties", column_names)
    if connection is None:
        conn.close()
    if log:
        of.info()
    return of


def get_wf(connection=None, log=False):
    if connection is None:
        conn = connect()
    else:
        conn = connection
    column_names = ["window_properties_id", "op_frame_count", "op_win_window", "op_win_CSS2Properties", "op_win_origin",
                    "op_win_opener", "op_win_history_length",
                    ]
    # Execute the "SELECT *" query
    wf = postgresql_to_dataframe(conn, "select * from dbcon_windowproperties", column_names)
    if connection is None:
        conn.close()
    if log:
        wf.info()
    return wf

def get_tf(connection=None, log=False):
    if connection is None:
        conn = connect()
    else:
        conn = connection
    column_names = ["test_id", "test_url", "inc_method", "url_dict_version"
                ]
    # Execute the "SELECT *" query
    tf = postgresql_to_dataframe(conn, "select * from dbcon_test", column_names)
    if connection is None:
        conn.close()
    if log:
        tf.info()
    return tf


def get_url_id(test_url):
    """Get the id from a test_url.
    Example URL: https://172.17.0.1:44300/leaks/24576/noauth/ Example output: 24576"""
    splits = test_url.split("leaks/")
    if len(splits) == 2:
        try:
            return int(splits[1].split("/")[0])
        except ValueError:
            print(splits)
    else:
        return None

    
def get_timed_out_urls(df, log=True):
    """Return all runs that are timed out."""
    tf = df.loc[df["timed_out"] == True].copy()
    tf = tf.drop(tf[tf["retest"] == True].index)

    if log:
        print("All timed out urls:")
        display(tf.groupby(["browser", "version", "headless"])["timed_out"].count().to_frame())
    #tf["missing_url"] = tf.agg(lambda x: f"{x['inc_method']}/{x['url_id']}", axis=1)
    tf["reason"] = "timed_out"
    return tf[["inc_method", "url_id", "browser_id", "reason"]]


def get_duplicates(df):
    """Return all runs that are duplicate (warn if they are not one timed out/one not timed out)"""
    duplicates = df.loc[df.duplicated(subset=["browser_id","test_id", "retest"], keep=False)].copy()
    print("All duplicate urls:")
    display(duplicates[["browser", "version", "headless", "timed_out"]].value_counts().to_frame())    
    # Check that everthing has 1/1!
    duplicates["count"] = duplicates.groupby(["browser_id", "test_id","timed_out"])["timed_out"].transform("count")
    display(duplicates.groupby(["browser_id"])["inc_method"].value_counts())
    duplicates_special = duplicates.loc[duplicates["count"] != 1]
    if not duplicates_special.empty:
        print("WARNING! duplicates which are not timed out/non-timed-out")
        display(duplicates_special[["test_id","timed_out", "browser_id", "count"]])

    print(f"Total duplicates: {len(duplicates)}")
    duplicates = duplicates.loc[duplicates["timed_out"] == True]
    return duplicates


def del_duplicates(df, duplicates):
    """Delete all duplicates from the df only timed out ones."""
    print(f"Dropping {len(duplicates)} duplicates (timed-out)")
    return df.drop(duplicates.index)


def get_missing_urls(df, leak_nums, log):
    """Return all tests that are have no record."""
    # This function is very slow (optimize?)
    # Find missing URLs
    df = df.copy()
    df = df.drop(df[df["retest"] == True].index)
    url_counts = df.groupby(["browser_id"])["url_id"].value_counts().to_frame()
    missing_urls = pd.DataFrame()
    if log:
        print(f"Missing urls:")
    for browser_id, url_id in url_counts.loc[url_counts["url_id"] != leak_nums].index:
        counts = df.loc[(df["browser_id"] == browser_id) & (df["url_id"] == url_id)]["inc_method"].value_counts().reset_index()
        if log:
            print(counts)
        c = counts.loc[counts["inc_method"] == 0]["index"].to_frame()
        c["browser_id"] = browser_id
        c["url_id"] = url_id
        missing_urls = missing_urls.append(c)
    #missing_urls["missing_url"] = missing_urls.agg(lambda x: f"{x['index']}/{x['url_id']}", axis=1)
    if not missing_urls.empty:
        missing_urls["inc_method"] = missing_urls["index"]
        missing_urls["reason"] = "unknown"
        return missing_urls[["inc_method", "url_id", "browser_id", "reason"]]
    else:
        return None

    
def get_missing_urls_new(df, leak_nums, log):
    """Only works if it was working in at least one browser (and not more than once in one browser); + needs some parsing to actually get the needed missing information."""
    df = df.copy()
    counts = df.groupby(["test_id"])["url_id"].value_counts().to_frame()
    c = counts.loc[counts["url_id"] < 3]
    if log:
        display(c)
    return c
    
        
def save_missing_as_dict(missing_urls):
    """Save all missing urls as a dict, such that we can retest these."""
    groups = missing_urls.groupby("browser")
    missing_dict = {}
    for browser, group in groups:
        missing_dict[browser] = group[["inc_method", "url_id"]].to_dict("records")

        with open("missing_urls.pickle", "wb") as f:
            pickle.dump(missing_dict, f)
    return missing_dict            