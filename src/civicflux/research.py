"""Shared research utilities, not a backend dispatcher."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.metrics import precision_score,recall_score,f1_score,average_precision_score,roc_auc_score,brier_score_loss,confusion_matrix

def pipeline(model,numeric,categorical=(),scale=False):
    steps=[('imputer',SimpleImputer(strategy='median',keep_empty_features=True))]
    if scale:steps.append(('scale',StandardScaler()))
    transformers=[('numeric',Pipeline(steps),list(numeric))]
    if categorical:transformers.append(('categorical',OneHotEncoder(handle_unknown='ignore',sparse_output=False),list(categorical)))
    return Pipeline([('preprocess',ColumnTransformer(transformers)),('model',model)])

def binary_metrics(y,p,threshold=.5):
    y=np.asarray(y);p=np.asarray(p);h=p>=threshold
    tn,fp,fn,tp=confusion_matrix(y,h,labels=[0,1]).ravel()
    return {'precision':float(precision_score(y,h,zero_division=0)),'recall':float(recall_score(y,h,zero_division=0)),
            'F1':float(f1_score(y,h,zero_division=0)),
            'PR_AUC_average_precision':float(average_precision_score(y,p)) if y.sum() else None,
            'ROC_AUC':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
            'Brier':float(brier_score_loss(y,p)),'false_positive_rate':float(fp/max(1,fp+tn)),
            'false_positives':int(fp),'false_negatives':int(fn),'n':len(y),'prevalence':float(y.mean())}

def choose_threshold(y,p):
    rows=[]
    for t in np.linspace(.05,.95,37):rows.append({'threshold':float(t),'F1':float(f1_score(y,np.asarray(p)>=t,zero_division=0))})
    table=pd.DataFrame(rows)
    return float(table.sort_values(['F1','threshold'],ascending=[False,False]).iloc[0].threshold),table

def write_json(path,data):
    Path(path).write_text(json.dumps(data,indent=2,default=str,allow_nan=False))
