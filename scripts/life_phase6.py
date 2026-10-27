"""Persist optional ALICE-LIFE-2 social events and cultural artifacts."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import life_phase6 as phase6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    attach = sub.add_parser('attach'); attach.add_argument('--source', type=Path, required=True); attach.add_argument('--db', type=Path, required=True)
    event = sub.add_parser('event'); event.add_argument('--db', type=Path, required=True); event.add_argument('--event-id', required=True); event.add_argument('--kind', required=True); event.add_argument('--actor', required=True); event.add_argument('--other'); event.add_argument('--payload', type=json.loads, default={}); event.add_argument('--source-ref', action='append', required=True)
    artifact = sub.add_parser('artifact'); artifact.add_argument('--db', type=Path, required=True); artifact.add_argument('--artifact-id', required=True); artifact.add_argument('--owner', required=True); artifact.add_argument('--kind', required=True); artifact.add_argument('--content', type=json.loads, required=True); artifact.add_argument('--source-ref', action='append', required=True)
    read = sub.add_parser('read'); read.add_argument('--db', type=Path, required=True); read.add_argument('--artifact-id', required=True); read.add_argument('--reader', required=True); read.add_argument('--source-ref', action='append', required=True)
    for name in ('inspect', 'replay'):
        command = sub.add_parser(name); command.add_argument('--db', type=Path, required=True)
    events = sub.add_parser('events'); events.add_argument('--db', type=Path, required=True); events.add_argument('--actor')
    artifacts = sub.add_parser('artifacts'); artifacts.add_argument('--db', type=Path, required=True); artifacts.add_argument('--owner'); artifacts.add_argument('--reader')
    save = sub.add_parser('save'); save.add_argument('--db', type=Path, required=True); save.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'attach': result = phase6.attach(args.source, args.db)
    elif args.command == 'event': result = phase6.record_event(args.db, event_id=args.event_id, event_kind=args.kind, actor_id=args.actor, other_actor_id=args.other, payload=args.payload, source_refs=args.source_ref)
    elif args.command == 'artifact': result = phase6.write_artifact(args.db, artifact_id=args.artifact_id, owner_id=args.owner, artifact_kind=args.kind, content=args.content, source_refs=args.source_ref)
    elif args.command == 'read': result = phase6.read_artifact(args.db, artifact_id=args.artifact_id, reader_id=args.reader, source_refs=args.source_ref)
    elif args.command == 'inspect': result = phase6.inspect(args.db)
    elif args.command == 'replay': result = phase6.replay(args.db)
    elif args.command == 'events': result = phase6.events(args.db, actor_id=args.actor)
    elif args.command == 'artifacts': result = phase6.artifacts(args.db, owner_id=args.owner, reader_id=args.reader)
    else: result = phase6.save(args.db, args.destination)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__': main()
