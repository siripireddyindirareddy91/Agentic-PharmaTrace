"""Optional synthetic classifier. Rule evidence remains authoritative for demo scoring."""
from pathlib import Path
FEATURES=['duplicate','batch_mismatch','manufacturer_mismatch','expired','unknown','location_anomaly','frequent','custody_gap','temperature_excursion','route_deviation']
def train(output='ml-models/artifacts'):
    import numpy as np, joblib, json
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import precision_score,recall_score,f1_score,confusion_matrix,roc_auc_score
    rng=np.random.default_rng(42);x=rng.binomial(1,.18,(5000,10))
    # Synthetic labels deliberately include noise. Split before fitting.
    weighted=x@np.array([35,25,30,35,40,20,15,15,30,20])+rng.normal(0,15,len(x))
    y=(weighted>=60).astype(int)
    xtrain,xtest,ytrain,ytest=train_test_split(x,y,test_size=.25,random_state=73,stratify=y)
    model=RandomForestClassifier(n_estimators=100,max_depth=7,random_state=42,class_weight='balanced');model.fit(xtrain,ytrain)
    p=model.predict(xtest);prob=model.predict_proba(xtest)[:,1]
    metrics={'precision':precision_score(ytest,p),'recall':recall_score(ytest,p),'f1':f1_score(ytest,p),'confusion_matrix':confusion_matrix(ytest,p).tolist(),'roc_auc':roc_auc_score(ytest,prob),'train_samples':len(xtrain),'test_samples':len(xtest),'disclosure':'Synthetic labels and features only. These metrics do not establish real-world counterfeit detection accuracy.'}
    path=Path(output);path.mkdir(parents=True,exist_ok=True);joblib.dump(model,path/'risk.joblib');(path/'metrics.json').write_text(json.dumps(metrics,indent=2));return metrics
def predict(values):
    path=Path('ml-models/artifacts/risk.joblib')
    if not path.exists():return {'available':False,'mode':'rules','detail':'No trained model. Evidence rules remain operational.'}
    import joblib
    model=joblib.load(path);return {'available':True,'synthetic_model_score':float(model.predict_proba([[int(values.get(k,False)) for k in FEATURES]])[0,1]),'disclosure':'Experimental synthetic-data probability; not clinical or counterfeit confirmation.'}
