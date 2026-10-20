"""Private entry point; actual token verification is mandatory, not an environment flag."""
import argparse
import json
import os
from multiprocessing.connection import PipeConnection
from . import runtime
from .supervisor import PipeProvider


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--db",required=True)
    parser.add_argument("--simulated-seconds",required=True,type=float);parser.add_argument("--wall-seconds",required=True,type=float)
    parser.add_argument("--broker-handle",type=int);parser.add_argument("--fault-stage");parser.add_argument("--fault-tick",type=int)
    args=parser.parse_args()
    def fault(stage,tick):
        if args.fault_stage==stage and tick==args.fault_tick:os._exit(77)
    provider=PipeProvider(PipeConnection(args.broker_handle)) if args.broker_handle is not None else None
    result=runtime.run(args.db,args.simulated_seconds,args.wall_seconds,provider,True,fault)
    print(json.dumps(result),flush=True)


if __name__=="__main__":main()
