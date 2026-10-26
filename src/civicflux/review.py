"""Targeted diagnostic utilities. Thresholds accept development labels only."""
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, balanced_accuracy_score
from .research import binary_metrics


def select_score_threshold(y, scores, objective='F1'):
    y=np.asarray(y,dtype=int);p=np.asarray(scores,dtype=float)
    if len(y)!=len(p) or not np.isfinite(p).all() or len(np.unique(y))!=2:
        raise ValueError('Threshold selection requires finite validation scores and both labels')
    # Evaluate actual operating points, including sub-0.05 scores and no-alerts.
    candidates=np.unique(np.r_[0., np.quantile(p,np.linspace(0,1,min(501,len(p)))),np.nextafter(p.max(),np.inf)])
    rows=[]
    for t in candidates:
        a=p>=t;tp=int((a & (y==1)).sum());fp=int((a & (y==0)).sum());fn=int((~a & (y==1)).sum());tn=len(y)-tp-fp-fn
        recall=tp/max(1,tp+fn);fpr=fp/max(1,fp+tn)
        rows.append({'threshold':float(t),'F1':2*tp/max(1,2*tp+fp+fn),'balanced_accuracy':(recall+1-fpr)/2,
                     'precision':tp/max(1,tp+fp),'recall':recall,'false_positive_rate':fpr,'alert_rate':float(a.mean())})
    table=pd.DataFrame(rows)
    key='F1' if objective=='F1' else 'balanced_accuracy'
    chosen=table.sort_values([key,'threshold'],ascending=[False,False]).iloc[0]
    return float(chosen.threshold),table


def event_metrics(times, y, scores, threshold, events):
    """Network-wide alert windows; not leak localization or official challenge scoring.

    A single alert can overlap multiple onsets. Only complete onset windows
    inside the evaluated observation span enter event recovery.
    False alarm episodes are alert runs that never overlap a positive hour.
    """
    ix=pd.DatetimeIndex(times);y=np.asarray(y);alert=np.asarray(scores)>=threshold
    starts=np.r_[True,(np.diff(ix.asi8)>pd.Timedelta(hours=1).value)] | np.r_[True,~alert[:-1]]
    episode_id=np.cumsum(starts & alert)
    false_episodes=0;episodes=0
    for group in np.unique(episode_id[alert]):
        loc=alert & (episode_id==group);episodes+=1;false_episodes+=int(not y[loc].any())
    rows=[]
    for event in events.itertuples():
        onset=pd.Timestamp(event.onset);end=pd.Timestamp(event.window_end)
        if onset<ix.min() or end>ix.max()+pd.Timedelta(hours=1):continue
        mask=(ix>=onset)&(ix<end);hits=ix[mask & alert]
        rows.append({'event_id':event.event_id,'onset':str(onset),'detected':bool(len(hits)),
                     'delay_hours':float((hits[0]-onset).total_seconds()/3600) if len(hits) else None})
    frame=pd.DataFrame(rows,columns=['event_id','onset','detected','delay_hours'])
    negative=int((y==0).sum())
    return {'events':len(frame),'recovered_events':int(frame.detected.sum()),
            'event_recall':float(frame.detected.mean()) if len(frame) else None,
            'median_delay_hours_detected_only':float(frame.delay_hours.dropna().median()) if frame.delay_hours.notna().any() else None,
            'alert_hours':int(alert.sum()),'false_alert_hours':int((alert & (y==0)).sum()),
            'false_alert_hours_per_negative_day':float((alert & (y==0)).sum()/max(1,negative)*24),
            'alert_episodes':episodes,'false_alarm_episodes':false_episodes,
            'false_alarm_episodes_per_30_days':float(false_episodes/(len(ix)/24)*30)},frame


class SeasonalHydraulicRule:
    """Train-only hour-of-week references; directional pressure/flow residuals.

    Output is an empirical training-rank score, not a calibrated leak probability.
    """
    def fit(self,X):
        self.columns=[c for c in X if c.startswith(('pressure__','flow__')) and c.count('__')==1]
        self.center=X[self.columns].median();self.scale=(X[self.columns]-self.center).abs().median().clip(lower=.1)*1.4826
        self.reference=X[self.columns].groupby(X.index.dayofweek*24+X.index.hour).median()
        self.training_scores=np.sort(self._score(X))
        return self
    def _score(self,X):
        ref=self.reference.reindex(X.index.dayofweek*24+X.index.hour).set_axis(X.index).fillna(self.center)
        residual=(X[self.columns]-ref)/self.scale
        for c in self.columns:
            if c.startswith('pressure__'):residual[c]=-residual[c]
        return residual.clip(lower=0).quantile(.75,axis=1).fillna(0).to_numpy()
    def predict_proba(self,X):
        score=np.searchsorted(self.training_scores,self._score(X),side='right')/len(self.training_scores)
        return np.c_[1-score,score]
