"""Run the bundled CivicFlux dashboard and FastAPI backend on this Mac."""
from pathlib import Path
import argparse,json,os,socket,subprocess,sys,time,urllib.request
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from src.civicflux.runtime import research_environment


def healthy(url):
    try:
        with urllib.request.urlopen(url+'/api/health',timeout=1) as response:
            if json.load(response).get('status')!='ok':return False
        with urllib.request.urlopen(url+'/',timeout=1) as response:
            return 'text/html' in response.headers.get('Content-Type','') and 'id="root"' in response.read().decode('utf-8')
    except (OSError,ValueError):return False


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-browser',action='store_true');parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args();state_dir=ROOT/'.cache/mac_app';state_dir.mkdir(parents=True,exist_ok=True);state=state_dir/'server.json'
    if state.exists():
        try:
            info=json.loads(state.read_text())
            if info.get('root')==str(ROOT) and healthy(info['url']):
                print('CivicFlux is already running: '+info['url'],flush=True)
                if not args.no_browser:subprocess.run(['open',info['url']],check=True)
                return 0
        except (OSError,ValueError,KeyError):pass
    port=None
    for candidate in range(args.port,args.port+21):
        try:
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                probe.bind(('127.0.0.1',candidate))
            port=candidate;break
        except OSError:continue
    if port is None:raise SystemExit('No available local port; specify --port with another number')
    env=research_environment();env['CIVICFLUX_ROOT']=str(ROOT);env['CIVICFLUX_CHECKS_DIR']=str(ROOT/'reports/macos/inference')
    for name,relative in [('MPLCONFIGDIR','.cache/matplotlib'),('XDG_CACHE_HOME','.cache'),('IPYTHONDIR','.cache/ipython')]:
        path=ROOT/relative;path.mkdir(parents=True,exist_ok=True);env[name]=str(path)
    url=f'http://127.0.0.1:{port}'
    process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env)
    state.write_text(json.dumps({'root':str(ROOT),'url':url,'pid':process.pid},indent=2))
    try:
        print('Starting CivicFlux from '+str(ROOT)+' (first startup may take up to 2 minutes)…',flush=True)
        for _ in range(600):
            if process.poll() is not None:return process.returncode
            if healthy(url):break
            time.sleep(.2)
        else:raise SystemExit('Backend did not become ready; inspect the server output')
        print('CivicFlux is running: '+url,flush=True)
        if not args.no_browser:subprocess.run(['open',url],check=True)
        return process.wait()
    except KeyboardInterrupt:
        process.terminate();process.wait();return 0
    finally:
        if process.poll() is None:process.terminate()
        if state.exists():
            try:
                if json.loads(state.read_text()).get('pid')==process.pid:state.unlink()
            except (OSError,ValueError):pass

if __name__=='__main__':sys.exit(main())
