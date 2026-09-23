import argparse
import time

from notif_vault import storage


def formatTimestamp(epochSeconds):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epochSeconds))


def truncate(text, length):
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= length else text[: length - 3] + "..."


def printRows(rows):
    if not rows:
        print("(no notifications match)")
        return
    for notificationId, appName, summary, body, urgency, createdAt in rows:
        print(f"[{formatTimestamp(createdAt)}] {appName}: {truncate(summary, 60)} - {truncate(body, 80)}")


def cmdList(args):
    rows = storage.queryNotifications(
        appName=args.app, search=args.search, sinceSeconds=parseSince(args.since), limit=args.limit
    )
    printRows(rows)


def cmdTail(args):
    seenIds = set()
    print("watching for new notifications, ctrl-c to stop")
    try:
        while True:
            rows = storage.queryNotifications(limit=20)
            for row in reversed(rows):
                if row[0] not in seenIds:
                    seenIds.add(row[0])
                    printRows([row])
            time.sleep(1)
    except KeyboardInterrupt:
        print()


def parseSince(sinceText):
    if not sinceText:
        return None
    unit = sinceText[-1]
    amount = float(sinceText[:-1])
    multiplier = {"m": 60, "h": 3600, "d": 86400}.get(unit)
    if multiplier is None:
        raise ValueError("since must look like 30m, 2h or 1d")
    return amount * multiplier


def buildParser():
    parser = argparse.ArgumentParser(prog="notif-vault", description="searchable desktop notification history")
    subparsers = parser.add_subparsers(dest="command", required=True)

    listParser = subparsers.add_parser("list", help="list recent notifications")
    listParser.add_argument("--app", help="filter by app name substring")
    listParser.add_argument("--search", help="filter by text in summary/body")
    listParser.add_argument("--since", help="only show notifications newer than this, e.g. 30m, 2h, 1d")
    listParser.add_argument("--limit", type=int, default=50)
    listParser.set_defaults(func=cmdList)

    tailParser = subparsers.add_parser("tail", help="live-follow new notifications")
    tailParser.set_defaults(func=cmdTail)

    return parser


def main():
    parser = buildParser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
