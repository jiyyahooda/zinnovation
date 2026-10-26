"""Research integrity tests: leakage, availability, conservation and serialization."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from civicflux_core import *

class IntegrityTests(unittest.TestCase):
 def make_raw(self):
  return pd.DataFrame({'DateTime':pd.date_range('2020-01-01',periods=600,freq='h').strftime('%Y-%m-%d %H:%M:%S'),'Junction':1,'Vehicles':np.arange(600.),'ID':np.arange(600)})
 def test_future_does_not_change_history_features(self):
  h,_=canonicalize(self.make_raw(),CONFIGS['traffic']);b=h.copy();b.loc[400:,'value']=99999
  a=make_features(h,CONFIGS['traffic'],False);c=make_features(b,CONFIGS['traffic'],False)
  pd.testing.assert_frame_equal(a.iloc[:400],c.iloc[:400])
 def test_gap_is_not_next_available_target(self):
  raw=self.make_raw().drop(index=10);h,_=canonicalize(raw,CONFIGS['traffic']);f=make_features(h,CONFIGS['traffic'])
  self.assertTrue(np.isnan(f.iloc[9].target));self.assertTrue(np.isnan(f.iloc[11].lag_1))
 def test_duplicate_conflict_rejected(self):
  raw=self.make_raw();row=raw.iloc[[0]].copy();row['Vehicles']=999
  with self.assertRaises(ValueError):canonicalize(pd.concat([raw,row]),CONFIGS['traffic'])
 def test_folds_purge_labels(self):
  h,_=canonicalize(self.make_raw(),CONFIGS['traffic']);f=make_features(h,CONFIGS['traffic']).dropna(subset=['target'])
  for tr,va in temporal_folds(f):self.assertLess(f.iloc[tr].target_time.max(),f.iloc[va].time.min())
 def test_scenario_groups_never_overlap(self):
  h,_=canonicalize(self.make_raw(),CONFIGS['traffic']);s=generate_scenarios(h)
  for tr,va in temporal_folds(s):self.assertFalse(set(s.iloc[tr].event_id)&set(s.iloc[va].event_id))
 def test_simulator_units(self):
  x=pd.DataFrame([dict(rain_mm=100,duration_h=2,area_m2=10000,runoff_coefficient=.8,drain_mm_h=10,blockage=.5,ponding_fraction=.1,initial_storage_mm=0)])
  # (100*.8 - 10*.5*2) / (1000*.1) = 0.7 m.
  np.testing.assert_allclose(simulate_depth(x),[.7])
 def test_report_availability(self):
  t=pd.Timestamp('2024-01-10');q=pd.DataFrame({'entity':['A'],'time':[t]})
  incidents=pd.DataFrame({'entity':['A','A'],'event_time':[t-pd.Timedelta(days=1)]*2,'reported_at':[t-pd.Timedelta(hours=1),t+pd.Timedelta(days=1)]})
  self.assertEqual(historical_incidents(q,incidents).iloc[0],1)
 def test_flood_reproducibility(self):
  h,_=canonicalize(self.make_raw(),CONFIGS['traffic'])
  pd.testing.assert_frame_equal(generate_scenarios(h),generate_scenarios(h))

if __name__=='__main__':unittest.main()
