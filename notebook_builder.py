"""Small source-authoring helper: only writes the explicitly named new notebook."""
from pathlib import Path
import textwrap,sys
import nbformat as nbf
ROOT=Path(__file__).resolve().parent
class ResearchNotebook:
 def __init__(self,name,title):self.name=name;self.cells=[];self.md('# '+title)
 def md(self,text):self.cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(text).strip()))
 def code(self,text):self.cells.append(nbf.v4.new_code_cell(textwrap.dedent(text).strip()))
 def section(self,num,title,text):self.md(f'## {num:02d}. {title}\n\n'+text)
 def step(self,title,text,code):self.md('### '+title+'\n\n'+text);self.code(code)
 def save(self):
  path=ROOT/'notebooks'/self.name
  if path.exists() and '--overwrite' not in sys.argv:raise SystemExit('Preserving executed output; supply --overwrite intentionally')
  n=nbf.v4.new_notebook(cells=self.cells,metadata={'kernelspec':{'name':'civicflux','display_name':'Python (CivicFlux)','language':'python'},'language_info':{'name':'python','version':'3.13'}})
  nbf.write(n,path);print(path.name,len(n.cells),'cells')
SETUP='''
from pathlib import Path
import sys,json,platform,importlib.metadata,time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display
import joblib
ROOT=Path.cwd() if (Path.cwd()/'civicflux_core.py').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
from civicflux_core import sha256
from src.civicflux.research import pipeline,binary_metrics,choose_threshold,write_json
from sklearn.model_selection import cross_validate,RandomizedSearchCV,TimeSeriesSplit,GroupKFold
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.ensemble import RandomForestClassifier,RandomForestRegressor
from sklearn.dummy import DummyClassifier,DummyRegressor
from sklearn.metrics import ConfusionMatrixDisplay,PrecisionRecallDisplay,classification_report,mean_absolute_error,mean_squared_error
from sklearn.calibration import calibration_curve
from sklearn.inspection import permutation_importance
from xgboost import XGBClassifier
from sklearn.base import clone
import networkx as nx
sns.set_theme(style='whitegrid',palette='colorblind')
plt.rcParams.update({'figure.figsize':(11,4),'figure.dpi':110})
SEED=42
'''

def classification_experiment(n,include_rf=True):
 n.step('Declare model candidates','All learned transforms are refitted within CV. The prior baseline is eligible to win; class balance is not altered on evaluation data.', '''
models={'Prior':pipeline(DummyClassifier(strategy='prior'),numeric,categorical),
        'Logistic':pipeline(LogisticRegression(max_iter=2000,class_weight='balanced',random_state=SEED),numeric,categorical,True),
        'XGBoost':pipeline(XGBClassifier(n_estimators=140,max_depth=3,learning_rate=.06,subsample=.85,colsample_bytree=.85,eval_metric='logloss',tree_method='hist',n_jobs=2,random_state=SEED),numeric,categorical)}
'''+("models['Random Forest']=pipeline(RandomForestClassifier(n_estimators=100,max_depth=12,min_samples_leaf=5,class_weight='balanced',random_state=SEED,n_jobs=2),numeric,categorical)\n" if include_rf else '')+"print('Candidates',list(models))")
 n.step('Cross-validated comparisons','Average precision (PR-AUC summary) is primary; fold dispersion is reported. Development scores are selection estimates, not independent final performance.', '''
rows=[]
for name,model in models.items():
    scores=cross_validate(model,Xtrain,ytrain,cv=folds,scoring={'ap':'average_precision','brier':'neg_brier_score'},error_score='raise',n_jobs=1)
    for i in range(len(folds)):rows.append({'model':name,'fold':i,'AP':scores['test_ap'][i],'Brier':-scores['test_brier'][i]})
cv_results=pd.DataFrame(rows)
summary=cv_results.groupby('model').agg(AP=('AP','mean'),AP_std=('AP','std'),Brier=('Brier','mean')).sort_values('AP',ascending=False)
display(summary);cv_results.to_csv(OUT/'candidate_cv.csv',index=False)
summary.AP.plot.barh(xerr=summary.AP_std,title='Development CV average precision');plt.tight_layout();plt.show()
''')
 n.step('Declared hyperparameter searches','Tune Logistic and XGBoost with four sampled settings each. The modest budget is explicit and repeatable; test labels never enter selection.', '''
spaces={'Logistic':{'model__C':[.01,.1,1,10,100],'model__class_weight':[None,'balanced']},
        'XGBoost':{'model__n_estimators':[80,140,220],'model__max_depth':[2,3,5],'model__learning_rate':[.03,.08,.15],'model__min_child_weight':[1,5,10]}}
searches={};ranking=summary.AP.to_dict()
for name,space in spaces.items():
    search=RandomizedSearchCV(models[name],space,n_iter=4,scoring='average_precision',cv=folds,refit=True,n_jobs=1,random_state=SEED,error_score='raise')
    search.fit(Xtrain,ytrain);searches[name]=search;ranking[name+' tuned']=search.best_score_
    trials=pd.DataFrame(search.cv_results_);trials.to_csv(OUT/(name+'_tuning.csv'),index=False)
    display(trials.sort_values('rank_test_score')[['rank_test_score','mean_test_score','std_test_score','params']])
selected=max(ranking,key=ranking.get)
model=searches[selected.removesuffix(' tuned')].best_estimator_ if selected.endswith(' tuned') else clone(models[selected]).fit(Xtrain,ytrain)
print('Locked CV choice:',selected)
''')
 n.step('Choose a validation-only threshold','Choose the highest threshold among tied validation F1 scores. This is a predictive tradeoff, not an authorized intervention policy. Calibration is assessed on final data without retuning.', '''
pval=model.predict_proba(Xval)[:,1]
threshold,threshold_table=choose_threshold(yval,pval)
threshold_table.to_csv(OUT/'threshold_validation.csv',index=False)
threshold_table.plot(x='threshold',y='F1',title='Validation-only decision threshold');plt.axvline(threshold,color='red');plt.show()
print('Locked threshold',threshold)
''')

def classification_evaluation(n):
 n.step('Locked final evaluation','No final-period outcome is used to pick the model or change its threshold.', '''
ptest=model.predict_proba(Xtest)[:,1]
metrics=binary_metrics(ytest,ptest,threshold)
display(pd.Series(metrics));print(classification_report(ytest,ptest>=threshold,zero_division=0))
write_json(OUT/'metrics.json',metrics)
fig,ax=plt.subplots(1,2,figsize=(12,4))
ConfusionMatrixDisplay.from_predictions(ytest,ptest>=threshold,ax=ax[0],display_labels=['Other','Target'])
PrecisionRecallDisplay.from_predictions(ytest,ptest,ax=ax[1]);ax[1].axhline(np.mean(ytest),ls='--',color='grey')
plt.tight_layout();plt.show()
''')
 n.step('Probability reliability and error distribution','Uncalibrated scores may be poorly calibrated under domain shift; a probability-looking number is not proof of real-world validity.', '''
fraction,mean=calibration_curve(ytest,ptest,n_bins=10,strategy='quantile')
fig,ax=plt.subplots(1,2,figsize=(12,4))
ax[0].plot(mean,fraction,marker='o');ax[0].plot([0,1],[0,1],'k--');ax[0].set(title='Final reliability',xlabel='Mean probability',ylabel='Target fraction')
sns.histplot(x=ptest,hue=np.asarray(ytest),bins=30,element='step',ax=ax[1]);ax[1].set_title('Scores by final label')
plt.tight_layout();plt.show()
''')

def explanations(n):
 n.step('Permutation importance of the chosen model','Feature associations are not causal effects. Correlated variables can divide importance; no feature reselection occurs after final evaluation.', '''
sample=Xval.sample(min(160,len(Xval)),random_state=SEED)
y_sample=yval.loc[sample.index]
pi=permutation_importance(model,sample,y_sample,scoring='average_precision',n_repeats=3,random_state=SEED,n_jobs=1)
importance=pd.Series(pi.importances_mean,index=feature_names).sort_values()
importance.tail(15).plot.barh(title='Chosen model: permutation decrease in average precision');plt.tight_layout();plt.show()
importance.to_csv(OUT/'permutation_importance.csv')
''')
 n.step('SHAP global and individual explanation','SHAP explains the fitted raw classifier output. If a prior baseline wins, an auxiliary XGBoost explanation is explicitly identified.', '''
import shap
explained=model
if isinstance(model.named_steps['model'],DummyClassifier):
    explained=searches['XGBoost'].best_estimator_;print('Auxiliary XGBoost, not selected prior baseline')
transformed=explained.named_steps['preprocess'].transform(sample.iloc[:60])
classifier=explained.named_steps['model']
if isinstance(classifier,LogisticRegression):
    background=explained.named_steps['preprocess'].transform(Xtrain.sample(min(100,len(Xtrain)),random_state=SEED))
    ex=shap.LinearExplainer(classifier,background)(transformed)
else:
    ex=shap.TreeExplainer(classifier)(transformed)
    if ex.values.ndim==3:ex=ex[:,:,1]
ex.feature_names=list(explained.named_steps['preprocess'].get_feature_names_out())
shap.plots.beeswarm(ex,max_display=15,show=False);plt.tight_layout();plt.show()
shap.plots.waterfall(ex[0],max_display=12,show=False);plt.tight_layout();plt.show()
''')
