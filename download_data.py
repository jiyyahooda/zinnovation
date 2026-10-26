"""Download the exact requested public sources; no credential prompts or substitutes."""
from pathlib import Path
import urllib.request, zipfile, json
from civicflux_core import SOURCES, sha256
ROOT=Path(__file__).resolve().parent
for name,slug in SOURCES.items():
    target=ROOT/'data'/'raw'/name
    target.mkdir(parents=True,exist_ok=True)
    archive=target.with_suffix('.zip')
    url='https://www.kaggle.com/api/v1/datasets/download/'+slug
    if not archive.exists():
        print('Downloading',url)
        try:
            urllib.request.urlretrieve(url,archive)
        except Exception as error:
            raise RuntimeError('Public API download failed. Use the manual or authenticated CLI instructions in DATASET_GUIDE.md.') from error
    if not zipfile.is_zipfile(archive):
        raise ValueError(f'{archive} is not a valid ZIP; check authentication or failed download')
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            destination=(target/member.filename).resolve()
            if not destination.is_relative_to(target.resolve()):
                raise ValueError('Unsafe archive path')
        z.extractall(target)
    try:
        metadata=urllib.request.urlopen('https://www.kaggle.com/api/v1/datasets/view/'+slug).read()
        (ROOT/'data'/f'{name}_source.json').write_bytes(metadata)
    except Exception as error:
        print('Metadata refresh failed; retain existing snapshot:',type(error).__name__)
    print(name,[(p.name,sha256(p)) for p in target.glob('*.csv')])
