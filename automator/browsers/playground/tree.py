import h2o
from h2o.tree import H2OTree    
from h2o.estimators import H2ORandomForestEstimator
h2o.init()
import pandas as pd 


with pd.ExcelFile('img_tag_test_log_adv_edge.xlsx', engine="openpyxl") as excel:
    df = pd.read_excel(excel)
    df["Res_Code_Chain"] = df["Res_Code_Chain"].astype(str)
    print(df.dtypes)
    hf = h2o.H2OFrame(df)
    hf["Res_Code_Chain"] = hf["Res_Code_Chain"].asfactor()

    gbm = H2ORandomForestEstimator(ntrees = 1,  
                                    min_rows = 1, 
                                    sample_rate = 1,            
                                    mtries=-2,
                                    max_depth=0,
                                    categorical_encoding="enum",
                                    )
    gbm.train(x=["Res_Code_Chain",'Res_CTypeOpt_Chain','Res_CType_Chain','Res_XFO_Chain', 'Res_ContDisp_Chain'],
          y="Event_Trigger_Chain",
          training_frame=hf)
    tree = H2OTree(model = gbm, tree_number = 0 , tree_class = None)
    print(tree)
    print(tree.show())
    print(len(tree))
    print(tree.root_node)
    gbm.download_mojo("tree.zip")


   
# java -cp h2o.jar hex.genmodel.tools.PrintMojo --tree 0 -i model.zip -o model.gv -f 20 -d 3
# dot -Tpng model.gv -o model.png
# open model.png