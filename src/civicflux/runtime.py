"""Launch-environment helper, reusing the existing notebook OpenMP setup."""
import os,sys
from pathlib import Path


def research_environment():
    env=os.environ.copy()
    if sys.platform=='darwin':
        import sklearn
        library=Path(sklearn.__file__).parent/'.dylibs'
        if (library/'libomp.dylib').exists():
            env['DYLD_LIBRARY_PATH']=str(library)+(os.pathsep+env['DYLD_LIBRARY_PATH'] if env.get('DYLD_LIBRARY_PATH') else '')
    return env
