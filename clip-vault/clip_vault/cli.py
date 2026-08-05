import argparse
import subprocess
import sys
import time

from clip_vault import storage, webhook
from clip_vault.config import loadConfig, configPath, logPath


def formatRow(row):
    clipId, content, sourceWindow, createdAt, pinned = row
    preview = content.replace("\n", " ").strip()
    if len(preview) > 80:
        preview = preview[:77] + "..."
    when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(createdAt))
    pinMark = "*" if pinned else " "
    source = f" [{sourceWindow}]" if sourceWindow else ""
    return f"{clipId:>5} {pinMark} {when}{source} {preview}"


def commandList(args):
    rows = storage.listClips(limit=args.limit, search=args.search)
    for row in rows:
        print(formatRow(row))


def commandShow(args):
    row = storage.getClip(args.id)
    if not row:
        print(f"no clip with id {args.id}", file=sys.stderr)
        sys.exit(1)
    print(row[1])


def commandCopy(args):
    row = storage.getClip(args.id)
    if not row:
        print(f"no clip with id {args.id}", file=sys.stderr)
        sys.exit(1)
    subprocess.run(["xclip", "-selection", "clipboard"], input=row[1].encode("utf-8"))
    print(f"copied clip {args.id} to clipboard")


def commandPin(args):
    storage.setPinned(args.id, True)
    print(f"pinned {args.id}")


def commandUnpin(args):
    storage.setPinned(args.id, False)
    print(f"unpinned {args.id}")


def commandDelete(args):
    storage.deleteClip(args.id)
    print(f"deleted {args.id}")


def commandClear(args):
    storage.clearHistory(keepPinned=not args.all)
    print("history cleared" + ("" if args.all else " (pinned items kept)"))


def commandConfig(args):
    print(f"config: {configPath}")
    print(f"log: {logPath}")


def commandTestWebhook(args):
    config = loadConfig()
    target = next((w for w in config.get("webhooks", []) if w.get("name") == args.name), None)
    if not target:
        print(f"no webhook named '{args.name}' in config", file=sys.stderr)
        sys.exit(1)
    ok = webhook.sendWebhook(target, args.content or "clip-vault test payload", "clip-vault-cli")
    print("sent ok" if ok else "send failed, check " + logPath)


def buildParser():
    parser = argparse.ArgumentParser(prog="clip-vault", description="Clipboard history manager with configurable webhook forwarding")
    subparsers = parser.add_subparsers(dest="command", required=True)

    listParser = subparsers.add_parser("list", help="show recent clipboard history")
    listParser.add_argument("--limit", type=int, default=30)
    listParser.add_argument("--search", type=str, default=None)
    listParser.set_defaults(func=commandList)

    showParser = subparsers.add_parser("show", help="print full content of a clip")
    showParser.add_argument("id", type=int)
    showParser.set_defaults(func=commandShow)

    copyParser = subparsers.add_parser("copy", help="copy a stored clip back to the clipboard")
    copyParser.add_argument("id", type=int)
    copyParser.set_defaults(func=commandCopy)

    pinParser = subparsers.add_parser("pin", help="pin a clip so it survives trimming/clear")
    pinParser.add_argument("id", type=int)
    pinParser.set_defaults(func=commandPin)

    unpinParser = subparsers.add_parser("unpin", help="unpin a clip")
    unpinParser.add_argument("id", type=int)
    unpinParser.set_defaults(func=commandUnpin)

    deleteParser = subparsers.add_parser("delete", help="delete a clip")
    deleteParser.add_argument("id", type=int)
    deleteParser.set_defaults(func=commandDelete)

    clearParser = subparsers.add_parser("clear", help="clear history")
    clearParser.add_argument("--all", action="store_true", help="also delete pinned clips")
    clearParser.set_defaults(func=commandClear)

    configParser = subparsers.add_parser("config", help="show config and log file paths")
    configParser.set_defaults(func=commandConfig)

    testWebhookParser = subparsers.add_parser("test-webhook", help="send a test payload through a configured webhook")
    testWebhookParser.add_argument("name", type=str)
    testWebhookParser.add_argument("--content", type=str, default=None)
    testWebhookParser.set_defaults(func=commandTestWebhook)

    return parser


def main():
    parser = buildParser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
