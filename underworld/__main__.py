import argparse
import json
from pathlib import Path
import sqlite3
import subprocess

from .config import load


def main():
    parser = argparse.ArgumentParser(description="Underworld Lab bounded unattended experiments (Phase 7)")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="create a new run without overwriting existing files")
    new.add_argument("--db", type=Path, required=True)
    new.add_argument("--config", type=Path, default=Path("config/survival.toml"))
    new.add_argument("--manual", action="store_true", help="disable authored scripted movement")
    inspect = commands.add_parser("inspect", help="read-only state; never advances time")
    inspect.add_argument("--db", type=Path)
    inspect.add_argument("--agent", action="append", default=[])
    inspect.add_argument("--core", type=Path, help="legacy Phase 0 initialization probe")
    inspect.add_argument("--config", type=Path, default=Path("config/baseline.toml"))
    for name in ("advance", "resume"):
        sub = commands.add_parser(name)
        sub.add_argument("--db", type=Path, required=True)
        sub.add_argument("--ticks", type=int, required=(name=="advance"), default=0)
        sub.add_argument("--decisions", type=Path, help="JSONL: at_tick and ActionRequest")
    save = commands.add_parser("save")
    save.add_argument("--db", type=Path, required=True)
    save.add_argument("--name", required=True)
    save.add_argument("--output", type=Path, help="atomic standalone SQLite backup, must not exist")
    replay = commands.add_parser("replay")
    replay.add_argument("--db", type=Path, required=True)
    intervention=commands.add_parser("intervene",help="guided-mode operator mutation from a JSON file")
    intervention.add_argument("--db",type=Path,required=True)
    intervention.add_argument("--request",type=Path,required=True)
    history=commands.add_parser("interventions",help="read-only operator intervention history")
    history.add_argument("--db",type=Path,required=True)
    branch=commands.add_parser("fork",help="create a new branch; parent is read-only")
    branch.add_argument("--db",type=Path,required=True)
    branch.add_argument("--output",type=Path,required=True)
    branch.add_argument("--mode",choices=["closed","guided"])
    branch.add_argument("--hearing-range-m",type=float)
    branch.add_argument("--episodic-memory",choices=["enabled","disabled"],help="explicit new-branch memory ablation")
    recall=commands.add_parser("recall",help="evidence-backed lexical claim lookup, not an engine fact")
    recall.add_argument("--db",type=Path,required=True)
    recall.add_argument("--agent",required=True)
    recall.add_argument("--symbol",required=True)
    procedure=commands.add_parser("procedure",help="read-only own-report procedure recall, never engine truth")
    procedure.add_argument("--db",type=Path,required=True)
    procedure.add_argument("--agent",required=True)
    for name in ("think", "mind"):
        sub = commands.add_parser(name, help="private operator cognition/memory access")
        sub.add_argument("--db", type=Path, required=True)
        sub.add_argument("--agent", required=True)
        if name == "mind":sub.add_argument("--query", default="")
    observer=commands.add_parser("observe",help="local paused observer with explicit time controls")
    observer.add_argument("--db",type=Path,required=True)
    observer.add_argument("--port",type=int,default=8765)
    observer.add_argument('--read-only',action='store_true',help='attach without a simulation writer; suitable for isolated unattended runs')
    runner=commands.add_parser("run",help="bounded AppContainer run; all physics ticks still commit individually")
    runner.add_argument("--db",type=Path,required=True)
    runner.add_argument("--simulated-seconds",type=float,required=True)
    runner.add_argument("--wall-seconds",type=float,required=True)
    runner.add_argument("--local-model",action="store_true",help="explicit inherited-IPC access to the local model adapter")
    runner.add_argument("--model-endpoint",default="http://127.0.0.1:8081")
    living=commands.add_parser("living-world",help="opt-in stabilized living-world controller")
    living_commands=living.add_subparsers(dest="living_command",required=True)
    for name in ("init","attach","run","status"):
        sub=living_commands.add_parser(name)
        sub.add_argument("--db",type=Path,required=True)
        if name=="init":sub.add_argument("--config",type=Path,default=Path("config/living-world.toml"))
        if name in ("init","attach"):sub.add_argument("--model",action="store_true");sub.add_argument("--calls",type=int,default=2)
        if name=="run":
            sub.add_argument("--seconds",type=float,required=True)
            sub.add_argument("--wall-seconds",type=float,default=240)
            sub.add_argument("--model",action="store_true")
            sub.add_argument("--endpoint",default="http://127.0.0.1:8081")
    for name in ("run-status","stop"):
        sub=commands.add_parser(name);sub.add_argument("--db",type=Path,required=True)
    args = parser.parse_args()
    try:
        from . import storage
        if args.command=="observe":
            from .observer import serve
            if not 0<=args.port<=65535:raise ValueError("invalid port")
            serve(args.db,args.port,args.read_only)
            return
        if args.command=="living-world":
            from . import stabilization
            if args.living_command=="init":
                cfg=load(args.config);cfg["agency"]["policy"]="none";storage.create(args.db,cfg,scripted=False)
                value=stabilization.attach(args.db,model=args.model,call_limit=args.calls)
            elif args.living_command=="attach":
                value=stabilization.attach(args.db,model=args.model,call_limit=args.calls)
            elif args.living_command=="run":
                provider=None
                if args.model:
                    from . import cognition
                    provider=cognition.LlamaCpp(args.endpoint)
                value=stabilization.run(args.db,args.seconds,args.wall_seconds,provider=provider)
            else:value=stabilization.status(args.db)
            print(json.dumps(value,indent=2,allow_nan=False));return
        if args.command == "new":
            value = storage.create(args.db, load(args.config), scripted=not args.manual)
        elif args.command=="run":
            from .supervisor import run_isolated
            value=run_isolated(args.db,args.simulated_seconds,args.wall_seconds,args.local_model,args.model_endpoint)
        elif args.command in ("run-status","stop"):
            from .runtime import status,request_stop
            value=status(args.db) if args.command=="run-status" else request_stop(args.db)
        elif args.command=="intervene":
            from .teaching import intervene
            from .wire import loads
            value=intervene(args.db,loads(args.request.read_text(encoding="utf-8"),16384))
        elif args.command=="interventions":
            from .teaching import history
            value=history(args.db)
        elif args.command=="fork":
            from .teaching import fork
            value=fork(args.db,args.output,args.mode,args.hearing_range_m,None if args.episodic_memory is None else args.episodic_memory=="enabled")
        elif args.command=="recall":
            from .teaching import recall
            value=recall(args.db,args.agent,args.symbol)
        elif args.command=="procedure":
            from .culture import recall
            value=recall(args.db,args.agent)
        elif args.command == "think":
            value = storage.think(args.db, args.agent)
        elif args.command == "mind":
            value = storage.mind(args.db, args.agent, args.query)
        elif args.command == "inspect":
            if args.core:
                if args.db or args.agent:
                    raise ValueError("--core is the legacy Phase 0 probe; use --db for Phase 1")
                config = load(args.config)
                w = config["world"]
                command = [str(args.core.resolve()), "--seed", str(config["seed"]),
                           "--population", str(w["population"]), "--width-m", str(w["width_m"]),
                           "--height-m", str(w["height_m"]), "--dt-s", str(w["dt_s"])]
                value = json.loads(subprocess.run(command, check=True, capture_output=True, text=True, timeout=15).stdout)
            elif args.db:
                value = storage.observe(args.db, args.agent) if args.agent else storage.inspect(args.db)
            else:
                raise ValueError("inspect requires --db (or legacy --core)")
        elif args.command in ("advance", "resume"):
            if args.command == "resume":
                storage.recover(args.db)
            if args.ticks == 0 and args.command == "resume" and not args.decisions:
                value = storage.inspect(args.db)
            else:
                decisions = storage.read_decisions(args.decisions) if args.decisions else ()
                value = storage.advance(args.db, args.ticks, decisions)
        elif args.command == "save":
            value = storage.save(args.db, args.name, args.output)
        else:
            value = storage.replay(args.db)
        print(json.dumps(value, indent=2, allow_nan=False))
    except (ValueError, OSError, RuntimeError, OverflowError, TypeError, sqlite3.Error, subprocess.SubprocessError) as error:
        parser.exit(2, f"underworld: {error}\n")


if __name__ == "__main__":
    main()
