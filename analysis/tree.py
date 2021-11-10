import ray
#ray.init(num_cpus=25, ignore_reinit_error=True)
import os
import json
import subprocess
import time
from pathlib import Path
import h2o
from h2o.tree import H2OTree    
from h2o.estimators import H2ORandomForestEstimator

import warnings
warnings.filterwarnings("ignore", "Dropping bad") # Ignore the warning that some columns are constant (they will just be ignored)
warnings.filterwarnings("ignore", "Sample rate") # Ignore that we do not have a test dataset (this is what we want)


#h2o.init(nthreads=60)
h2o.connect()
default_config = {
    "h2o_jar": "/home/xsleaker/h2o-3.32.1.3/h2o.jar",
    "base_dir": "/home/xsleaker/main/analysis/trees",
    "ntrees": 1,
    "max_depth": 0,
    "min_rows": 1,
    "stopping_rounds": 0,
    "seed": 29,
    "mtries": -2,
    "sample_rate": 1,
    "min_split_improvement": 0,
}


def create_tree(hf, test_property, prediction_properties, config):
    """Create a decision tree for a given frame and test_property."""
    tree_model = H2ORandomForestEstimator(ntrees = config["ntrees"],                                     
                                          max_depth = config["max_depth"], 
                                          min_rows = config["min_rows"], 
                                          stopping_rounds = config["stopping_rounds"],
                                          seed = config["seed"],
                                          mtries = config["mtries"],
                                          sample_rate = config["sample_rate"],  
                                          min_split_improvement = config["min_split_improvement"],


                                    categorical_encoding="enum",
                                    )
    tree_model.train(x=prediction_properties,
          y=test_property,
          training_frame=hf)

    return tree_model


def convert_tree(tree_model, tree_name, config, tree_id=0):
    """Converts a tree to a mojo, dot and png and save everything."""
    mojo_path = f"{config['base_dir']}/mojo/{tree_name}.mojo"
    dot_path = f"{config['base_dir']}/dot/{tree_name}.gv"
    svg_path = f"{config['base_dir']}/svg/{tree_name}.svg"
    if tree_model is not None:
        tree_model.download_mojo(mojo_path)
    result = subprocess.call(["java", "-cp", config["h2o_jar"], "hex.genmodel.tools.PrintMojo", "--tree", str(tree_id), "-i", mojo_path, "-o", dot_path, "-f", "20", "-d", "3"])
    if result:
        print("Error occured!")
        return
    result = subprocess.Popen(["dot", "-Tsvg", dot_path, "-o", svg_path])
    # if result:
    #    print("Error occured!")
    #    return
    return svg_path

def info_tree(tree_model):
    """Print some info about a given tree model."""
    print(tree_model)
    tree = H2OTree(model = tree_model, tree_number = 0 , tree_class = None)
    print(tree)
    print(tree.show())
    print(len(tree))
    print(tree.root_node)

def create_tree_dirs(browser_ids, config=default_config):
    """Create the dirs for the decision trees if not existing already."""
    for browser_id in browser_ids:
        Path(f"{config['base_dir']}/mojo/{browser_id}").mkdir(parents=True, exist_ok=True)
        Path(f"{config['base_dir']}/dot/{browser_id}").mkdir(parents=True, exist_ok=True)
        Path(f"{config['base_dir']}/svg/{browser_id}").mkdir(parents=True, exist_ok=True)
        Path(f"{config['base_dir']}/nuniq/{browser_id}").mkdir(parents=True, exist_ok=True)


def add_unique(df, dic, test_property, condition=None, log=False):
    cont = True
    dic["shape"] = df.shape
    dic["unique_count"] = df[test_property].nunique()
    dic["unique_values"] = df[test_property].unique().tolist()
    df_vals = df[test_property].value_counts().reset_index()
    df_vals = df_vals.loc[df_vals.iloc[:, 1] != 0]
    total = len(df)
    df_vals.loc["Total"] = df_vals.sum()
    df_vals["Percentage"] = df_vals.iloc[:, 1]/total
    dic["value_counts"] = df_vals.to_dict("list")

    if dic["unique_count"] == 1:
        if log:
            print(f"test property: {test_property} for {condition} is constant, value: {dic['unique_values']}")
        cont = False
    else:
        if log:
            print(f"test property: {test_property} for {condition} has {dic['unique_count']} values")
    return cont, dic

def make_tree(df, test_property, prediction_properties, config, inc_method=None, browser_id=None, overwrite=False, log=False):
    return
    if log:
        print(f"{test_property}:{inc_method}:{browser_id}")  
    path = test_property
    if inc_method:
        path = f"{path}::{inc_method}"
    if browser_id:
        path = f"{browser_id}/{path}"
    if not overwrite:
        if os.path.isfile(f"{config['base_dir']}/svg/{path}.svg"):
            if log:
                print("Already exists, skipping")
            return
        elif os.path.isfile(f"{config['base_dir']}/mojo/{path}.mojo"):
            if log:
                print("Mojo exists, only running dot")
            img_path = convert_tree(None, path)
            return
    if log:
        print(f"Create tree for {path}")
    num_colums = len(df.columns)
    hf = h2o.H2OFrame(df, column_types=["enum" for _ in range(num_colums)])
    tree_model = create_tree(hf, test_property, prediction_properties, config)

    img_path = convert_tree(tree_model, path, config)
    #display(Image(img_path))


def check_props(df, test_property, prediction_properties, inc_method, browser_id=None):
    pred_props = prediction_properties.copy()
    pred_props.remove("inc_method")
    if browser_id:
        pred_props.remove("browser_id")
    resp_dict = {}
    for pred_property in pred_props:        
        all_except = pred_props.copy()
        all_except.remove(pred_property)
        grouped = df.groupby(all_except)[test_property].agg("nunique")
        grouped = grouped[grouped != 0]  # Currently needed as we do not cover the complete url space, so we have to remove all which do not occur
        max_resp = grouped.nlargest(1).to_list()[0]
        min_resp = grouped.nsmallest(1).to_list()[0]
        if max_resp < 2:
            #print(f"{pred_property} can be ignored for {inc_method}:{test_property}")
            resp = 0  # never 
        elif min_resp >= 2:
            #print(f"{pred_property} is responsible for {inc_method}:{test_property} outcome in all cases! {min_resp}")
            resp = 2 
        else:
            #print(f"{pred_property} is responsible for {inc_method}:{test_property} outcome in some cases. {min_resp}")
            resp = 1
        resp_dict[pred_property] = {"Responsible": resp, "Max-resp": max_resp, "Min-resp": min_resp}
    return resp_dict

#@ray.remote


def generalize(df, test_properties, prediction_properties, inc_methods, overwrite, log, config=default_config):
    print(f"################################################## Start {test_properties} ########################")
    gen_dict = {}
    check_dict = {}
    df = df.copy()
    df = df.filter(items=[*test_properties, *prediction_properties])
    df = df.apply(lambda x: x.astype('category'))
    for test_property in test_properties:
        est_dict = {}
        check_dict[test_property] = {}
        cont = True
        # cont, est_dict_all = add_unique(df, {}, test_property, "all")
        # est_dict["all"] = {"all": est_dict_all}
        if cont:
            o_path = f"{test_property}"  
            inc_dict = {}
            cont, inc_dict_all = add_unique(df, {}, test_property, log=True)
            if not overwrite:
                if os.path.isfile(f"{config['base_dir']}/nuniq/{o_path}"):
                    if log:
                        print(f"{o_path} is done")
                    continue
            with open(f"{config['base_dir']}/nuniq/{o_path}", "w") as f:
                f.write(json.dumps(inc_dict_all, indent=4))
                if log:
                    print(f"Wrote {config['base_dir']}/nuniq/{o_path}")
            
            # ray_ids.append(make_tree.remote(df, test_property, prediction_properties))
            for inc_method in inc_methods:
                o_path = f"{test_property}::{inc_method}"  
                dinc = df.loc[df["inc_method"] == inc_method]
                inc_dict = {}
                cont, inc_dict_all = add_unique(dinc, {}, test_property, inc_method)
                if not overwrite:
                    if os.path.isfile(f"{config['base_dir']}/nuniq/{o_path}"):
                        if log:
                            print(f"{o_path} is done")
                        continue
                with open(f"{config['base_dir']}/nuniq/{o_path}", "w") as f:
                            f.write(json.dumps(inc_dict_all, indent=4))
                            if log:
                                print(f"Wrote {config['base_dir']}/nuniq/{o_path}")
                if cont:
                    make_tree(dinc, test_property, prediction_properties, config, inc_method=inc_method, overwrite=overwrite, log=log)   
                inc_dict["all"] = inc_dict_all
                if True:
                    check_dict[test_property][inc_method] = {}    
                    # check_dict[test_property][inc_method]["all"] = check_props(dinc, test_property, prediction_properties, inc_method)
                    for browser_id in dinc.browser_id.unique():
                        dbrow = dinc.loc[dinc["browser_id"] == browser_id]
                        path = f"{browser_id}/{o_path}"
                        if not overwrite:
                            if os.path.isfile(f"{config['base_dir']}/nuniq/{path}"):
                                if log:
                                    print(f"{path} is done")
                                continue
                        cont, browser_dict = add_unique(dbrow, {}, test_property, f"{inc_method}:{browser_id}", log=log)
                        with open(f"{config['base_dir']}/nuniq/{path}", "w") as f:
                            f.write(json.dumps(browser_dict, indent=4))
                            if log:
                                print(f"Wrote {config['base_dir']}/nuniq/{path}")
                        # check_dict[test_property][inc_method][browser_id] = check_props(dbrow, test_property, prediction_properties, inc_method, browser_id)
                        if cont:
                            make_tree(dbrow, test_property, prediction_properties, config, inc_method=inc_method, browser_id=browser_id, overwrite=overwrite, log=log)
                        inc_dict[browser_id] = browser_dict
                est_dict[inc_method] = inc_dict

        gen_dict[test_property] = est_dict
    print(f"############################### Finished {test_properties} #############################")
    return gen_dict
