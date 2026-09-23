import fnmatch
import json
import threading
import time
import urllib.request
from pathlib import Path

logDir = Path.home() / ".local" / "share" / "notif-vault"
logPath = logDir / "webhook.log"


def logLine(line):
    logDir.mkdir(parents=True, exist_ok=True)
    with open(logPath, "a") as logFile:
        logFile.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")


def matchingWebhooks(appName, urgency, config):
    matches = []
    for webhook in config.get("webhooks", []):
        if not webhook.get("enabled"):
            continue
        if not webhook.get("url"):
            logLine(f"webhook '{webhook.get('name')}' skipped: no url")
            continue
        if urgency < webhook.get("minUrgency", 0):
            continue
        patterns = webhook.get("appPatterns", ["*"])
        if any(fnmatch.fnmatch(appName, pattern) for pattern in patterns):
            matches.append(webhook)
    return matches


def sendWebhook(webhook, appName, summary, body):
    payload = {"appName": appName, "summary": summary, "body": body, "timestamp": time.time()}
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    headers.update(webhook.get("headers", {}))
    try:
        request = urllib.request.Request(webhook.get("url", ""), data=data, headers=headers, method=webhook.get("method", "POST"))
        with urllib.request.urlopen(request, timeout=webhook.get("timeoutSeconds", 4)) as response:
            logLine(f"webhook '{webhook.get('name')}' -> {response.status}")
            return True
    except Exception as sendError:
        logLine(f"webhook '{webhook.get('name')}' failed: {sendError}")
        return False


def dispatchAsync(appName, summary, body, urgency, config, onDone=None):
    matches = matchingWebhooks(appName, urgency, config)
    if not matches:
        if onDone:
            onDone([])
        return

    def worker():
        sentNames = []
        for webhook in matches:
            if sendWebhook(webhook, appName, summary, body):
                sentNames.append(webhook.get("name", webhook["url"]))
        if onDone:
            onDone(sentNames)

    threading.Thread(target=worker, daemon=True).start()
