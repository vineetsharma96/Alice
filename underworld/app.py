"""Model-off desktop entry point: one bounded writer and a read-only local viewer."""
import argparse
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import threading
import webbrowser

from . import __version__

ROOT=Path(__file__).resolve().parents[1]


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv[:1]==['--cli']:
        if getattr(sys,'frozen',False) and argv[1:2]==['run']:
            raise SystemExit('AppContainer experiments require the source Python runtime; use the desktop bounded runner here.')
        from .__main__ import main as cli
        sys.argv=[sys.argv[0],*argv[1:]]
        return cli()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version',action='version',version=__version__)
    p.add_argument('--db',type=Path,help='saved world (default: user-local UnderworldLab/world.sqlite)')
    p.add_argument('--config',type=Path,default=ROOT/'config/living-world-d.toml',help='initialization only; existing saves keep their configuration')
    p.add_argument('--seconds',type=float,default=30,help='bounded simulated duration, 0 starts an inspection-only viewer')
    p.add_argument('--wall-seconds',type=float,default=240)
    p.add_argument('--port',type=int,default=8768,help='loopback HTTP port; 0 chooses a free port')
    p.add_argument('--no-browser',action='store_true')
    p.add_argument('--exit-after-run',action='store_true',help='close server when bounded run completes; useful headlessly')
    args=p.parse_args(argv)
    if not math.isfinite(args.seconds) or not 0<=args.seconds<=3600:p.error('--seconds must be in [0,3600]')
    if not math.isfinite(args.wall_seconds) or not 0<args.wall_seconds<=3600:p.error('--wall-seconds must be in (0,3600]')
    if not 0<=args.port<=65535:p.error('invalid port')
    if args.db is None:
        base=Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))
        args.db=base/'UnderworldLab/world.sqlite'
    path=args.db.expanduser().resolve()
    from . import stabilization,storage
    from .config import load
    from .observer import make_server
    stopped=threading.Event();worker=None;server=None;controller=None;outcome={}
    try:
        if path.exists():
            # Validate before starting any thread. Never attach/reset a saved controller.
            state=stabilization.status(path)
            task=(state.get('tasks',{}).get('active') or {})
            if state['model'] or task.get('mode')=='model_assisted':raise ValueError('desktop runner requires model-off survival and tasks; use the explicit source/CLI model workflow')
        else:
            stabilization.initialize(path,load(args.config),model=False,call_limit=0)
        server,controller=make_server(path,args.port,readonly=True)
        url=f'http://127.0.0.1:{server.server_port}/viewer'
        print(json.dumps({'ready':True,'version':__version__,'db':str(path),'url':url,'native_build_id':storage.load_native().build_id,
                          'simulated_seconds_requested':args.seconds,'viewer_read_only':True,'model_calls_enabled':False}),flush=True)
        # Start HTTP handling before the run can finish and request shutdown.
        http=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.1},name='underworld-http',daemon=True)
        http.start()
        def run():
            try:
                outcome.update(stabilization.run(path,args.seconds,args.wall_seconds,stop_requested=stopped.is_set)
                               if args.seconds else {'status':'inspection_only','tick':storage.inspect(path)['tick']})
            except Exception as error:outcome.update(status='error',error=str(error))
            finally:
                print(json.dumps({'run':outcome}),flush=True)
                if args.exit_after_run:stopped.set()
        worker=threading.Thread(target=run,name='underworld-bounded-writer',daemon=False);worker.start()
        if not args.no_browser:webbrowser.open(url)
        try:
            while not stopped.wait(.2):pass
        except KeyboardInterrupt:stopped.set()
        worker.join()  # Stop only between committed ticks; release the real writer lease.
        return 1 if outcome.get('status')=='error' else 0
    except (ValueError,OSError,RuntimeError,sqlite3.Error) as error:
        p.exit(2,f'Underworld Lab: {error}\n')
    finally:
        stopped.set()
        if worker and worker.is_alive():worker.join()
        if server:
            server.shutdown();server.server_close()
        if controller:controller.close()


if __name__=='__main__':raise SystemExit(main())
