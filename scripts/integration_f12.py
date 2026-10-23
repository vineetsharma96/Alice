"""CLI for the bounded F12 native-world integration slice."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import integration_f12 as integration


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    attach = sub.add_parser("attach")
    attach.add_argument("source", type=Path)
    attach.add_argument("destination", type=Path)
    attach.add_argument("--declared-value", action="append", default=[])

    for name in ("inspect", "replay", "resume"):
        command = sub.add_parser(name)
        command.add_argument("db", type=Path)

    save = sub.add_parser("save")
    save.add_argument("db", type=Path)
    save.add_argument("destination", type=Path)

    observe = sub.add_parser("observe-current")
    observe.add_argument("db", type=Path)
    observe.add_argument("owner")
    observe.add_argument("--before", type=Path)
    observe.add_argument("--outcome", type=Path)
    observe.add_argument("--operation-id")

    native = sub.add_parser('record-native')
    native.add_argument('db',type=Path)
    native.add_argument('owner')
    native.add_argument('request_id')
    native.add_argument('--operation-id')

    send = sub.add_parser("send-signal")
    send.add_argument("db", type=Path)
    send.add_argument("speaker")
    send.add_argument("meaning")
    send.add_argument("partner")
    send.add_argument("evidence_id")
    send.add_argument("--operation-id")

    receive = sub.add_parser("receive-signal")
    receive.add_argument("db", type=Path)
    receive.add_argument("receiver")
    receive.add_argument("speaker")
    receive.add_argument("token")
    receive.add_argument("evidence_id")
    receive.add_argument("--operation-id")

    feedback = sub.add_parser("feedback-signal")
    feedback.add_argument("db", type=Path)
    feedback.add_argument("receiver")
    feedback.add_argument("token")
    feedback.add_argument("observed_meaning")
    feedback.add_argument("success", choices=("true", "false"))
    feedback.add_argument("evidence_id")
    feedback.add_argument("partner")
    feedback.add_argument("--operation-id")

    social = sub.add_parser("observe-social")
    social.add_argument("db", type=Path)
    social.add_argument("owner")
    social.add_argument("event", type=Path)
    social.add_argument("--operation-id")

    identity = sub.add_parser("revise-identity")
    identity.add_argument("db", type=Path)
    identity.add_argument("owner")
    identity.add_argument("event_or_summary", type=Path)
    identity.add_argument("--operation-id")

    choose = sub.add_parser("choose")
    choose.add_argument("db", type=Path)
    choose.add_argument("owner")
    choose.add_argument("candidates", type=Path)

    manifest = sub.add_parser("manifest")
    manifest.add_argument("db", type=Path)
    manifest.add_argument("--wall-time-s", type=float)

    args = parser.parse_args(argv)
    if args.command == "attach":
        result = integration.attach(args.source, args.destination, args.declared_value)
    elif args.command == "inspect":
        result = integration.inspect(args.db)
    elif args.command == "replay":
        result = integration.replay(args.db)
    elif args.command == "resume":
        result = integration.resume(args.db)
    elif args.command == "save":
        result = integration.save(args.db, args.destination)
    elif args.command == "observe-current":
        before = None if args.before is None else _read(args.before)
        outcome = None if args.outcome is None else _read(args.outcome)
        result = integration.observe_current(args.db, args.owner, before, outcome,
                                             args.operation_id)
    elif args.command=='record-native':
        result=integration.record_native_outcome(args.db,args.owner,args.request_id,args.operation_id)
    elif args.command == "send-signal":
        result = integration.send_signal(args.db, args.speaker, args.meaning,
                                          args.partner, args.evidence_id,
                                          args.operation_id)
    elif args.command == "receive-signal":
        result = integration.receive_signal(args.db, args.receiver, args.speaker,
                                             args.token, args.evidence_id,
                                             args.operation_id)
    elif args.command == "feedback-signal":
        result = integration.feedback_signal(
            args.db, args.receiver, args.token, args.observed_meaning,
            args.success == "true", args.evidence_id, args.partner,
            args.operation_id)
    elif args.command == "observe-social":
        result = integration.observe_social(args.db, args.owner, _read(args.event),
                                            args.operation_id)
    elif args.command == "revise-identity":
        result = integration.revise_identity(
            args.db, args.owner, _read(args.event_or_summary), args.operation_id)
    elif args.command == "choose":
        result = integration.choose(args.db, args.owner, _read(args.candidates))
    else:
        result = integration.manifest(args.db, args.wall_time_s)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
