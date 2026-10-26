"""Retrieve a documented subset of the official CC-BY-4.0 benchmark."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parent/'data/raw/battledim';ROOT.mkdir(parents=True,exist_ok=True)
api='https://zenodo.org/api/records/4017659'
if not (ROOT/'record.json').exists():urllib.request.urlretrieve(api,ROOT/'record.json')
record=json.loads((ROOT/'record.json').read_text())
names=['README.txt','dataset_configuration.yaml','L-TOWN.inp','2018_Fixed_Leakages_Report.txt']
names += [f'{year}_{kind}.csv' for year in [2018,2019] for kind in ['SCADA_Pressures','SCADA_Flows','SCADA_Levels','Leakages']]
# Nominal node demands/patterns are read from L-TOWN.inp; AMR CSV is optional.
def download(entry):
 name=entry['key'];path=ROOT/name
 expected=entry['checksum'].removeprefix('md5:')
 if path.exists() and hashlib.md5(path.read_bytes()).hexdigest()==expected:return name+' cached/verified'
 url='https://zenodo.org/records/4017659/files/'+name+'?download=1'
 subprocess.run(['curl','-sSL','--fail','--retry','2','--max-time','1800','-C','-',url,'-o',str(path)],check=True)
 if hashlib.md5(path.read_bytes()).hexdigest()!=expected:raise ValueError('Checksum mismatch: '+name)
 return name+' downloaded/verified'
with ThreadPoolExecutor(max_workers=4) as pool:
 for message in pool.map(download,[x for x in record['files'] if x['key'] in names]):print(message,flush=True)
