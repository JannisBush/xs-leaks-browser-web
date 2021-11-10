import time
import glob
import h2o
import pandas as pd

from dil_preprocess import header_to_header


h2o_columns = list(header_to_header.values()) + ["Status-Code", "body"]
working_methods = [
    ## event_set
    "1/event_set_smooth::audio", "2/event_set_smooth::audio",
    "1/event_set_smooth::embed-img", "2/event_set_smooth::embed-img",
    # embed: same as embed-img for firefox, unstable for chromium
    "1/event_set_smooth::iframe-csp", # chromium always load
    # iframe: (should) always load 
    "1/event_set_smooth::img", # chromiun same as embed-img
    # link-prefetch: unstable
    "1/event_set_smooth::link-stylesheet", "2/event_set_smooth::link-stylesheet",
    "1/event_set_smooth::object", # chromium unstable
    "1/event_set_smooth::script", "2/event_set_smooth::script",
    "1/event_set_smooth::video", "2/event_set_smooth::video", # chromium same as audio?
    ## Global properties
    # Download bar: unstable
    "1/gp_securitypolicyviolation::iframe-csp", "2/gp_securitypolicyviolation::iframe-csp",
    "1/gp_window_getComputedStyle::link-stylesheet", "2/gp_window_getComputedStyle::link-stylesheet",
    "1/gp_window_hasOwnProperty::script", "2/gp_window_hasOwnProperty::script",
    # Window onblur: ustable
    "1/gp_window_onerror::script", "2/gp_window_onerror::script",
    "1/gp_window_postMessage::embed-img", # chromium does not work
    "2/gp_window_postMessage::embed", # firefox same as embed-img
    "1/gp_window_postMessage::iframe", # chromium same as embed, iframe-csp == iframe
    # object identical with embed for both (means different things)
    "1/gp_window_postMessage::window.open", "2/gp_window_postMessage::window.open",
    ## Object properties
    # buffered: same as duration (but less information)
    # contentDocument: unstable?
    "1/op_el_duration::audio", "2/op_el_duration::audio",
    "1/op_el_duration::video", "2/op_el_duration::video", # chromium same as audio?
    # height: use naturalHeight instead
    "1/op_el_media_error::audio", "2/op_el_media_error::audio",
    # mediaError-video: see audio?
    "1/op_el_naturalHeight::img", "2/op_el_naturalHeight::img",
    # naturalWidth: see height
    # networkState: see duration
    # paused: does not work
    # readyState: see duration
    # seekable: see duration
    # sheet: does not work
    "1/op_el_videoHeight::video", "2/op_el_videoHeight::video",
    # videoWidth: see videoHeight
    # width: see height
    ## window property
    "1/op_frame_count::iframe", "2/op_frame_count::iframe", # same as iframe-csp
    "1/op_frame_count::window.open", "2/op_frame_count::window.open",
    "1/op_win_CSS2Properties::window.open", "2/op_win_CSS2Properties::window.open",
    "1/op_win_history_length::window.open", "2/op_win_history_length::window.open",
    "1/op_win_opener::window.open", "2/op_win_opener::window.open", 
    "1/op_win_origin::iframe", "2/op_win_origin::iframe", # same as iframe-csp
    "1/op_win_origin::window.open", "2/op_win_origin::window.open",
    "1/op_win_window::iframe", "2/op_win_window::iframe", # same as iframe-csp
    "1/op_win_window::window.open", "2/op_win_window::window.open",
]
models = None

# Methods that can work even though the trees have the same result for both responses
single_methods = {
    "gp_window_getComputedStyle": ["{'H1': 'rgb(0, 0, 255)'}"],
    "gp_window_hasOwnProperty": ["{'a': 'Var a exist. Value: 5'}"],
    "gp_window_onerror": ["[['Script error.', 0, 0]]"],
    "gp_window_postMessage": ["['Message: mes1 Origin: https://172.17.0.1:44300', 'Message: mes1 Origin: https://172.17.0.1:44300']",
                              "['Message: mes1 Origin: https://172.17.0.1:44300']"],
    "op_el_duration": [1, 2],
    "op_el_naturalHeight": [50],
    "op_el_videoHeight": [100],
    "op_frame_count": [1, 2],
    "gp_securitypolicyviolation": ["js-undefined"],  # Special as we check for not negative instead
}


def init(methods="limited"):
    """Load the models from disk into the h2o cluster."""
    global models
    h2o.init(log_level="FATA")
    h2o.no_progress()  # Disable progress bars of h2o
    if methods == "limited":
        files = [f"../analysis/trees/tenmin/mojo/{method}.mojo" for method in working_methods if not "window.open" in method]
        files_window = [f"../analysis/trees/window-redo/mojo/{method}.mojo" for method in working_methods if "window.open" in method]
        #files_window = [f"../analysis/trees/tenmin/mojo/{method}.mojo" for method in working_methods if "window.open" in method]
        files = files + files_window
    elif methods == "all":
        files = glob.glob("../analysis/trees/tenmin/mojo/1/*")
        files = files + glob.glob("../analysis/trees/tenmin/mojo/2/*")
    else:
        print("Unsupported methods")
        raise ValueError
    files = [file for file in files if "conflicted" not in file]
    print(f"h2o init complete: load {len(files)} mojos now.")
    models = [h2o.import_mojo(file) for file in files]
    print("h2o loading complete")
    # Mojo import not working because no test metric exists.
    # comment out `print(mojo_estimator)` in line 2253 in h2o.py fixes it
    return models


def check_single_method(row_df, method):
    """For 'single_methods' check whether they could work or not."""
    # Possible improvement: check according to method
    # Currently only check if body hash is the same, for most methods
    # However, not too important as we have dynamic confirmation
    # This should not generate any FNs as a different body hash is required for almost all single methods
    # But it might not be enough (e.g., two images of the same size have different hashes but result in the same observation)
    if method == "gp_securitypolicyviolation":
        if row_df["real_location"].nunique() == 1:
            return None
        else:
            return row_df.iloc[0]
    if row_df["resp_body_hash"].nunique() == 1:
        return None
    else:
        return row_df.iloc[0]


def post_process_single(nunique_frame, res, method):
    """Post-process 'single_methods'."""
    unique_pos_values = single_methods[method]        
    # special, check for not negative result (as many positive exist)
    if method == "gp_securitypolicyviolation":
        poss = nunique_frame["unique"].apply(lambda x: True if x != "js-undefined" else False)   
    # Only check the URLs where all observations have the "positive" result (e.g., image height 50)
    else:
        poss = nunique_frame["unique"].apply(lambda x: True if x in unique_pos_values else False)
    poss = poss[poss == True]
    poss = res.loc[res["URL"].isin(poss.index)].groupby(["URL"], group_keys=False).apply(check_single_method, method=method)
    return poss


def predict_trees(af, log=False, conf=False):
    """"Get the predictions for all fitted responses."""
    start = time.time()
    at = af.reset_index()
    if log:
        print(at.shape)

    hf = h2o.H2OFrame(at[h2o_columns])
    leaky_endpoints = {}
    if log:
        print(len(models))

    # Predict for every working method/model/tree
    for model in models:
        model_name = model.actual_params["path"]
        res = h2o.as_list(model.predict(hf))
        # We might miss some cases for single methods,
        # if we only continue if not all values are the same
        # However this should be negligible: these are the results on all responses of a site!
        # (e.g., not every response should be an img)
        if log:
            if "secret" in model_name:
                with pd.option_context('display.max_rows', None):
                    print(model_name)
                    display(pd.concat([at, res], axis=1)[["URL", "predict"]])
        if res["predict"].nunique() > 0:
            res = res.rename(columns={"predict": f"predict_{model_name}"})
            res = pd.concat([at, res[[f"predict_{model_name}"]]], axis=1)
            # FPs possible, if both cookies/non-cookies have the same expanded rows
            # And the result only differs based on our expansion
            # res[[cookies, ind_i]] == res[[no-cookies, ind_i]] (for all i) + res[[cookies, ind_i]] != res[[cookies, ind_j]]
            # Should only happen rarely and will be found by the dynamic confirmation, so it does not matter
            info = res.groupby(["URL"])[f"predict_{model_name}"].agg(["nunique", "unique", "count"])
            valid = info[info["nunique"] > 1]
            for method in single_methods.keys():
                if method in model_name:
                    # For the methods that do not necessarily need two records according to our tree,
                    # also check if they work if only one value was observed
                    new_valids = post_process_single(info[info["nunique"] == 1], res, method)
                    valid = pd.concat([valid, new_valids])
                    break
            leaky = res.loc[res["URL"].isin(valid.index)]
            if len(leaky) != 0:
                leaky_endpoints[model_name] = leaky            
                if log:
                    print(f"{model_name} works for {len(valid)} URLs.") 
                    # display(valid)
    if log:
        print(f"Took {time.time() - start} seconds")
    return leaky_endpoints


def reduce_leaky_endpoints(leaky_endpoints, log=False):
    """Convert leaky_endpoints dict of dfs to a single dataframe."""
    leaky_table = None
    for method in leaky_endpoints:
        df = leaky_endpoints[method]
        if log:
            print(df.shape)
        if leaky_table is None:
            leaky_table = df
        else:
            # Update all rows that already exist
            try:
                leaky_table.loc[leaky_table["index_i"].isin(df["index_i"]),
                                f"predict_{method}"] = df[f"predict_{method}"]
            except ValueError:
                if log:
                    print("Error")
            # Append all rows and then delete duplicates (only add new rows)
            leaky_table = pd.concat([leaky_table, df])
            leaky_table = leaky_table.drop_duplicates(subset=["index_i", "index"])
            if log:
                print(leaky_table.shape)
    leaky_table = leaky_table.sort_values(["URL", "cookies"])
    if log:
        print(leaky_table.columns)
        display(leaky_table)
        display(leaky_table["index"].value_counts())
        display(leaky_table.groupby("URL")["cookies"].value_counts().sort_values())
    leaks = leaky_table.filter(regex="^predict|URL").groupby(["URL"]).nunique()
    leaks["Location_count"] = leaky_table.groupby(["URL"])["real_location"].nunique()
    return leaks

    
    
