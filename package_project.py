"""Package portable source, executed notebooks and artifacts; exclude local runtimes."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parent
output=ROOT.parent/'CivicFlux_Research_Pipelines.zip'
excluded={'.venv','.cache','.jupyter','__pycache__','.ipynb_checkpoints'}
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for path in sorted(ROOT.rglob('*')):
  rel=path.relative_to(ROOT)
  if not path.is_file() or any(part in excluded for part in rel.parts):continue
  if path.suffix=='.zip' or 'figure_checks' in rel.parts:continue
  z.write(path,Path('civicflux_ml')/rel)
print(output,round(output.stat().st_size/1024**2,1),'MiB')
