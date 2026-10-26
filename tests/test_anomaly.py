"""Anomaly-specific temporal, serving, robustness and evidence-contract tests."""
import sys,unittest,tempfile,json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.civicflux.anomaly import *

class AnomalyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.spec=SensorSpec('fixture:A','fixture','A','arbitrary test unit','h','Asia/Kolkata','synthetic test only','local fixture')
  rng=np.random.default_rng(42)
  cls.h=pd.DataFrame({'sensor':'fixture:A','time':pd.date_range('2024-01-01',periods=600,freq='h'),'value':20+5*np.sin(np.arange(600)*2*np.pi/24)+rng.normal(size=600),'invalid':0})
  cls.f=causal_features(cls.h,cls.spec)
  cls.suite=DetectorSuite(cls.spec,n_estimators=32).fit(cls.f.iloc[:300])
  cls.service=AnomalyService({'fixture:A':cls.suite},{'fixture:A':cls.spec})
 def test_future_feature_invariance(self):
  changed=self.h.copy();changed.loc[450:,'value']=99999
  pd.testing.assert_frame_equal(self.f.iloc[:450],causal_features(changed,self.spec).iloc[:450])
 def test_current_excluded_from_reference(self):
  changed=self.h.copy();changed.loc[400,'value']=99999
  f=causal_features(changed,self.spec)
  for col in ['rolling_mean','rolling_std','rolling_median','rolling_mad','rolling_min','rolling_max','seasonal_expected','previous_unusual_count']:
   self.assertAlmostEqual(self.f.loc[400,col],f.loc[400,col])
 def test_missing_uses_quality_flag(self):
  h=self.h.copy();h.loc[599,'value']=np.nan
  row=self.suite.score(causal_features(h,self.spec).tail(1)).iloc[0]
  self.assertTrue(row.quality_alert);self.assertIn('missing_reading',row.violated_rules)
 def test_invalid_negative_and_infinity(self):
  for value in [-1,np.inf,'bad']:
   h=self.h.astype({'value':object});h.loc[599,'value']=value
   row=causal_features(h,self.spec).iloc[-1]
   self.assertEqual(row.invalid,1);self.assertEqual(row.missing,1)
 def test_gap_is_materialized(self):
  f=causal_features(self.h.drop(index=400),self.spec)
  self.assertEqual(len(f),600);self.assertEqual(f.iloc[400].missing,1)
 def test_trailing_gap(self):
  f=causal_features(self.h.iloc[:-5],self.spec,end=self.h.time.max())
  self.assertTrue(f.tail(5).missing.all());self.assertEqual(f.iloc[-1].hours_since_valid,5)
 def test_constant_series(self):
  h=self.h.copy();h.value=20
  f=causal_features(h,self.spec)
  self.assertTrue(np.isfinite(f.loc[f.ready,'robust_z']).all())
  model=DetectorSuite(self.spec,n_estimators=16).fit(f.iloc[:300])
  s=model.score(f.tail(1)).iloc[0]
  self.assertTrue(s.quality_alert);self.assertTrue(np.isfinite(s.isolation_score))
 def test_dry_rain_not_flatline_fault(self):
  spec=SensorSpec('rainfall:X','rainfall','X','mm/day','D','Asia/Kolkata','synthetic test','local',30,5,.1,48)
  h=pd.DataFrame({'sensor':spec.sensor,'time':pd.date_range('2020-01-01',periods=400),'value':0.})
  f=causal_features(h,spec);m=DetectorSuite(spec,n_estimators=16).fit(f.iloc[:250])
  self.assertFalse(m.score(f.tail(1)).iloc[0].quality_alert)
 def test_unknown_sensor_abstains(self):
  p=self.service.predict('unmapped',self.h,self.h.time.max())
  self.assertFalse(p['supported_sensor']);self.assertIsNone(p['anomaly_score']);self.assertIsNone(p['alert'])
 def test_stale_input(self):
  p=self.service.predict('fixture:A',self.h,self.h.time.max(),pd.Timestamp('2025-01-01',tz='UTC'))
  self.assertEqual(p['input_freshness']['status'],'stale')
 def test_future_observation_rejected(self):
  with self.assertRaises(ValueError):self.service.predict('fixture:A',self.h,self.h.time.max(),pd.Timestamp('2020-01-01',tz='UTC'))
 def test_naive_detection_time_rejected(self):
  with self.assertRaises(ValueError):self.service.predict('fixture:A',self.h,self.h.time.max(),pd.Timestamp('2025-01-01'))
 def test_no_retrospective_serving(self):
  with self.assertRaises(ValueError):self.suite.score(self.f.iloc[:1])
 def test_serialization_and_json(self):
  now=pd.Timestamp('2025-01-01',tz='UTC')
  expected=self.service.predict('fixture:A',self.h,self.h.time.max(),now)
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'suite.joblib';joblib.dump(self.service,path)
   actual=joblib.load(path).predict('fixture:A',self.h,self.h.time.max(),now)
  self.assertEqual(expected,actual);json.dumps(actual,allow_nan=False)
 def test_reproducibility(self):
  other=DetectorSuite(self.spec,n_estimators=32).fit(self.f.iloc[:300])
  np.testing.assert_array_equal(self.suite.score(self.f.iloc[300:]).isolation_score,other.score(self.f.iloc[300:]).isolation_score)
 def test_threshold_strict_comparison(self):
  threshold=self.suite.isolation_threshold_
  try:
   score=self.suite.score(self.f.tail(1)).iloc[0].isolation_score
   self.suite.isolation_threshold_=score
   self.assertFalse(self.suite.score(self.f.tail(1)).iloc[0].isolation_alert)
   self.suite.isolation_threshold_=score-1e-6
   self.assertTrue(self.suite.score(self.f.tail(1)).iloc[0].isolation_alert)
  finally:self.suite.isolation_threshold_=threshold
 def test_invalid_contamination(self):
  with self.assertRaises(ValueError):DetectorSuite(self.spec,contamination=0).fit(self.f.iloc[:300])
 def test_fixture_does_not_mutate_input(self):
  before=self.h.copy(deep=True)
  for name in ['missing','spike','persistent_shift','drift','flatline','seasonal_shift','invalid','data_gap']:
   fixture,manifest=inject_fixture(self.h,self.spec,name)
   self.assertTrue(fixture.attrs['synthetic_fixture']);self.assertEqual(int(fixture.injected.sum()),manifest['injected_points'])
  pd.testing.assert_frame_equal(self.h,before)
 def test_adapter_blocks_dispatch_even_if_input_tampered(self):
  p=self.service.predict('fixture:A',self.h,self.h.time.max());p['dispatch_allowed']=True;p['confirmed_failure']=True
  envelope=evidence_adapter(p)
  self.assertFalse(envelope['automatic_dispatch_allowed']);self.assertFalse(envelope['confirmed_failure'])
  self.assertFalse(envelope['eligible_for_operational_risk_fusion']);self.assertIsNone(envelope['asset_id'])
 def test_duplicate_conflict(self):
  row=self.h.iloc[[0]].copy();row.value=88
  with self.assertRaises(ValueError):causal_features(pd.concat([self.h,row]),self.spec)
 def test_mixed_identity_rejected(self):
  h=self.h.copy();h.loc[0,'sensor']='OTHER'
  with self.assertRaises(ValueError):causal_features(h,self.spec)
 def test_insufficient_context_abstains(self):
  p=self.service.predict('fixture:A',self.h.tail(5),self.h.time.max())
  self.assertIsNone(p['alert']);self.assertIsNone(p['anomaly_score'])

if __name__=='__main__':unittest.main()
