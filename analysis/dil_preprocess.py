import pandas as pd
import redis
import json

from database_connector import connect, postgresql_to_dataframe


r = redis.Redis()
sec_rel_headers = [
    "location",
    "content-type",
    "x-frame-options",
    "content-disposition",
    "cross-origin-opener-policy",
    "x-content-type-options",
    "cross-origin-resource-policy"
    ]
header_to_header = {
    "location": "Location",
    "content-type": "Content-Type",
    "x-frame-options": "X-Frame-Options",
    "content-disposition": "Content-Disposition",
    "cross-origin-opener-policy": "Cross-Origin-Opener-Policy",
    "x-content-type-options": "X-Content-Type-Options",
    "cross-origin-resource-policy": "Cross-Origin-Resource-Policy",
}
tree_headers = list(header_to_header.values()) + ["Status-Code", "resp_body_hash"]
known_cts = ["text/html", "text/css", "application/javascript",
             "video/mp4", "audio/wav", "image/png", "application/pdf", "empty"]
known_mismatches = set()
known_unhandled_bodies = set()

def redis_add(redis_key, new_value):
    redis_dict = r.get(redis_key)
    if redis_dict is None:
        redis_dict = {new_value: 1}
    else:
        redis_dict = json.loads(redis_dict)
        try:
            redis_dict[new_value] += 1
        except KeyError:
            redis_dict[new_value] = 1
    r.set(redis_key, json.dumps(redis_dict))


def get_url_data(site, conn=None, close=True):
    """Get the URL data for a given site."""
    # Connect to the database if no connection is given
    if conn is None:
        conn = connect()

    column_names = ["id", "req_url", "req_method", "req_headers", "req_body_hash", "req_body_info",
                    "resp_version", "resp_code", "resp_headers", "resp_body_hash", "resp_body_info",
                    "cookies", "site", "hash_uniq", "count", "real_site", "resp_body_tika_info",
                    ]
    # Execute the "SELECT" query
    # Do not reduce_leaky_endpoints everything to category? (req_url or hash_uniq are not suited for categories)
    # SQL injection possible, only use for trusted code
    if not site is None:
        df = postgresql_to_dataframe(conn, f"select * from db_url_data WHERE site = '{site}'", column_names,
                                 non_cat=["req_url", "hash_uniq", "resp_headers",
                                          "req_headers", "resp_body_tika_info"])
        dat = df.loc[(df["site"] == site) & (df["real_site"] == site) & (df["req_method"] == "GET")]
    else:
        dat = postgresql_to_dataframe(conn, f"select * from db_url_data", column_names,
                                 non_cat=["req_url", "hash_uniq", "resp_headers",
                                          "req_headers", "resp_body_tika_info"])
    if close:
        conn.close()

    return dat


def fit_header(header, value):
    """Convert headers to fit to our trees."""
    if header == "content-type":
        value = value.split(";")[0]  # Remove charset and stuff
        # All audio/video/javascript/image cts should behave the same
        # (this is not completly correct, e.g., unsupported cts, but should be good enough)
        # Thus change them to the ct we used for building the trees
        if "audio" in value:
            value = "audio/wav"
        elif "video" in value:
            value = "video/mp4"
        elif "javascript" in value:
            value = "application/javascript"
        elif "image" in value:
            value = "image/png"
    elif header == "x-frame-options":
        if value in ["deny", "sameorigin"]:
            value = "deny"  # if xfo is set, it cannot be framed by an attacker
        else:
            value = "empty"  # invalid values are interpreted as not set by (most?) browsers
    elif header == "location":
        value = "http://172.17.0.1:8000"  # if location is set, set it to our location
        # Problem no distinction between same-origin/cross-origin redirect! + if both cookie/no-cookie redirect, we might not see any difference
        # This special case is handeled in dil_predict.py check_single_methods
    elif header == "content-disposition":
        value = value.split(";")[0]  # Remove filename
        if value == "inline":
            value = "empty"  # inline behaves the same as not set
        else:
            value = "attachment"  # everything else behaves like attachment
    elif header == "x-content-type-options":
        if value == "nosniff":
            value = "nosniff"
        else:
            value = "empty"  # only nosniff should be accepted
    elif header == "cross-origin-opener-policy":
        if value == "unsafe-none":  # unsafe-none should be the same as not set
            value = "empty"
        else:
            value = "same-origin"
    elif header == "cross-origin-resource-policy":
        if value == "cross-origin":  # cross-origin should be the same as not set
            value = "empty"
        else:
            value = "same-origin"
    return value


def fit_data(data):
    """Process response data to fit to our trees"""
    res = {}
    res["URL"] = data["req_url"]
    res["cookies"] = data["cookies"]
    res["Status-Code"] = data["resp_code"]
    res["real_location"] = ""
    resp_headers = {k.lower(): v.lower() for k, v in data["resp_headers"].items()}
    for header in sec_rel_headers:
        try:
            # Better processing of headers to fit to our trees!
            tree_header = header_to_header[header]
            if tree_header == "Location":
                res["real_location"] = resp_headers[header].lower()
            res[tree_header] = fit_header(header, resp_headers[header].lower())
        # If header is not in the response, set it to empty
        except KeyError:
            res[header_to_header[header]] = "empty"
    # Get the content-tpye according to the tika parse (tika also has additonal information)
    try:
        tika_info = data["resp_body_tika_info"]["Content-Type"]
        if type(tika_info) == list:
            # print(f"Tika-Content-Type is list: {tika_info}")  # probably html with images
            tika_info = tika_info[0]
        if type(tika_info) == str:
            res["tika_content_type"] = tika_info.split(";")[0]
        else:
            print(f"Tika-Content-Type is {type(tika_info)}: {tika_info}")
            res["tika_content_type"] = "empty"
    except (TypeError, KeyError):
        # If tika had the null byte error, we have no info and only save an empty string
        res["tika_content_type"] = "empty"
    # Parse the body information (just content-type) from the information, we got from the `file` program
    res["body"] = data["resp_body_info"].split(":", 1)[1].split(",", 1)[0]
    res["resp_body_hash"] = data["resp_body_hash"]
    return res


def expand_body(row_df):
    """Duplicate rows if response cannot be fit to a single response of our training data due to the body content."""
    # Body according to the file info (not tika)
    # also look at tika to get closer match?
    body = row_df["body"].values[0]
    if "empty" in body:
        row_df["body"] = "empty"
        return row_df
    # When the content is HTML, all HTML body based leaks might work
    elif "HTML" in body:
        row_df = row_df.loc[row_df.index.repeat(4)]
        row_df["body"].iloc[0] = "ecocnt_html=num_frames=1,input_id=test1"
        row_df["index_i"].iloc[0] = "0"
        row_df["body"].iloc[1] = "ecocnt_html=num_frames=2"
        row_df["index_i"].iloc[1] = "1"
        row_df["body"].iloc[2] = "ecocnt_html=post_message=mes1"
        row_df["index_i"].iloc[2] = "2"
        row_df["body"].iloc[3] = "ecocnt_html=meta_refresh=0;http://172.17.0.1:8000"
        row_df["index_i"].iloc[3] = "3"
        return row_df
    # When the body is text, it could be javascript, or css
    elif "ASCII" in body or "UTF-8" in body:
        # ASCII could be script, or css (or json, ...), look at content-type + tika_content_type to infer more info?
        # use some more info when processing?, also compare cookies vs. non-cookies?
        # Depending on that info decide what content to use `ecocnt_css=h1 {color: blue}` for getComputedStyle,
        # `ecocnt_js=.,,.` for onError, `ecocnt_js=var a=5;` for hasOwnProperty, ...
        row_df = row_df.loc[row_df.index.repeat(3)]
        row_df["body"].iloc[0] = "ecocnt_js=var a=5;"
        row_df["index_i"].iloc[0] = "0"
        row_df["body"].iloc[1] = "ecocnt_js=.,,."
        row_df["index_i"].iloc[1] = "1"
        row_df["body"].iloc[2] = "ecocnt_css=h1 {color: blue}"
        row_df["index_i"].iloc[2] = "2"
    elif "image" in body.lower():
        row_df["body"] = "ecocnt_img=width=50,height=50,type=png"
    elif "audio" in body.lower():
        row_df["body"] = "ecocnt_audio=duration=1"
    elif "video" in body.lower():
        row_df["body"] = "ecocnt_vid=width=100,height=100,duration=2"
    elif "pdf" in body.lower():
        row_df["body"] = "ecocnt_pdf=a=a"
    elif "media" in body.lower():
        row_df = row_df.loc[row_df.index.repeat(2)]
        row_df["body"].iloc[0] = "ecocnt_vid=width=100,height=100,duration=2"
        row_df["index_i"].iloc[0] = "0"
        row_df["body"].iloc[1] = "ecocnt_audio=duration=1"
        row_df["index_i"].iloc[1] = "1"
    else:
        row_df["body"] = "empty"  # Set to empty as a default
        if body not in known_unhandled_bodies:
            known_unhandled_bodies.add(body)
            warning_text = f"Warning: unhandled body: according to file {body}, according to tika: {row_df['tika_content_type'].values[0]}"
            redis_add("known_unhandled_bodies", warning_text)
            print(warning_text)
        else:
            pass
    return row_df


def expand_ct(row_df):
    """Duplicate/change rows due to unknown/unclear content-types."""
    # return several rows for content-type that fit several cases/are unknown?
    ct = row_df["Content-Type"].values[0]
    ct_tika = row_df["tika_content_type"].values[0]
    if ct != ct_tika:
        # Tika thinks the real content type is not the specified content-type
        if f"{ct}-{ct_tika}" not in known_mismatches:
            print(f"Tika content-type mismatch: given ct: {ct}, ct acc to tika {ct_tika}")
        known_mismatches.add(f"{ct}-{ct_tika}")

    # Do nothing if the ct is one of the cts used in our tests
    if ct in known_cts:
        return row_df

    # Otherwise convert some of them
    # If we have no smart conversion rule, treat as ct empty (browser will guess, if xcto is set, result between reality and tree might differ)
    if ct == "application/json":
        row_df["Content-Type"] = "text/html"  # Kinda adhoc? both have CORB protection enabled, so better than empty
    elif ct == "text/plain":
        row_df["Content-Type"] = "empty"
    elif ct == "application/octet-stream":
        row_df["Content-Type"] = "empty"
    else:
        redis_add("untreated_cts", ct)
        row_df["Content-Type"] = "empty"

    return row_df


def expand_input_rows(df):
    """Expand body and content-type for all responses."""
    df["index"] = df.index
    df["index_i"] = "-1"
    # process unknown bodies
    df = df.groupby(["URL", "cookies"], group_keys=False).apply(expand_body)
    # process unknown headers
    df = df.groupby(["URL", "cookies"], group_keys=False).apply(expand_ct)
    return df


def basic_pruning(df, log=False):
    """Perform the basic pruning, i.e. remove all URLs where both responses are the same."""
    # Get all URLs that occurred twice (once with cookies, once without)
    ind = df.groupby(["req_url"])["cookies"].agg(["nunique", "count"]).sort_values("nunique")
    ind = ind.loc[(ind["nunique"] == 2) & (ind["count"] == 2)]
    if log:
        display(ind.index)

    # Get the relevant properties from the data, and fit everything to our trees
    d = df.loc[df["req_url"].isin(ind.index)][["req_url", "cookies", "resp_headers",
                                               "resp_code", "resp_body_tika_info",
                                               "resp_body_info", "resp_body_hash"]].apply(
                                                   func=fit_data, axis=1).to_dict()
    d = pd.DataFrame.from_dict(d, orient="index")

    # Count the number of unique URLs
    try:
        num_urls = d["URL"].nunique()
    except KeyError:
        return None, None, None, {"num_urls": 0, "num_basic_pruning": 0}
    if log:
        print("Total Dataframe size:", d.shape, num_urls)

    # Only use the ones where at least one header, status-code or body-hash is different
    d_poss = d.groupby(["URL"])[tree_headers + ["real_location"]].agg(["nunique"])
    poss = d_poss[d_poss.isin([2]).any(axis=1)].index
    poss = d.loc[d["URL"].isin(poss)].sort_values(["URL", "cookies"])
    num_basic_pruning = poss["URL"].nunique()
    if log:
        print("Basic pruning:", poss.shape, num_basic_pruning)
    if poss["URL"].nunique() == 0:
        return None, d, poss, {"num_urls": num_urls, "num_basic_pruning": num_basic_pruning, "num_input_rows": 0}

    # process body + unknown content-types! (we need the index, so we can only do it now?)
    af = expand_input_rows(poss)
    num_input_rows = af.shape[0]
    if log:
        print("Input rows for trees after expanding:", af.shape, af["URL"].nunique())

    return af, d, poss, {"num_urls": num_urls, "num_basic_pruning": num_basic_pruning,
                         "num_input_rows": num_input_rows}
