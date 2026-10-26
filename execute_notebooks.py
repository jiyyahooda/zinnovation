"""Execute notebooks in the project-local Python environment and retain outputs."""
from pathlib import Path
import os, sys, json, time
ROOT=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache'/'matplotlib')
os.environ['XDG_CACHE_HOME']=str(ROOT/'.cache')
os.environ['IPYTHONDIR']=str(ROOT/'.cache'/'ipython')
os.environ['JUPYTER_RUNTIME_DIR']=str(ROOT/'.cache'/'jupyter_runtime')
os.environ['JUPYTER_PATH']=str(ROOT/'.jupyter')
for p in ['.cache/matplotlib','.cache/ipython','.cache/jupyter_runtime','.jupyter/kernels/civicflux']:
 (ROOT/p).mkdir(parents=True,exist_ok=True)
(ROOT/'.jupyter/kernels/civicflux/kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Python (CivicFlux)','language':'python'}))
# Reuse scikit-learn's bundled OpenMP on macOS; no global installation is modified.
if sys.platform == 'darwin':
 import sklearn
 omp = Path(sklearn.__file__).parent / '.dylibs'
 if (omp/'libomp.dylib').exists():
  os.environ['DYLD_LIBRARY_PATH'] = str(omp) + (':' + os.environ['DYLD_LIBRARY_PATH'] if os.environ.get('DYLD_LIBRARY_PATH') else '')
import nbformat
from nbclient import NotebookClient
paths=sorted((ROOT/'notebooks').glob('*.ipynb'))
if len(sys.argv)>1: paths=[p for p in paths if p.name.startswith(tuple(sys.argv[1:]))]
for path in paths:
 n=nbformat.read(path,as_version=4)
 start=time.time()
 print('START',path.name,flush=True)
 try:
  NotebookClient(n,timeout=1800,kernel_name='civicflux',resources={'metadata':{'path':str(ROOT/'notebooks')}},allow_errors=False).execute()
 except Exception:
  nbformat.write(n,path)
  print('FAILED',path.name,flush=True)
  raise
 nbformat.write(n,path)
 print('DONE',path.name,round(time.time()-start,1),'seconds',flush=True)
