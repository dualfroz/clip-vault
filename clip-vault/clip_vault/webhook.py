import json
import os
import re
import threading
import time
import urllib.request

from clip_vault.config import configDir, logPath


def logLine(line):
    os.makedirs(configDir, exist_ok=True)
    with open(logPath, "a") as logFile:
        logFile.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")


def matchingWebhooks(content, config):
    matches = []
    for webhook in config.get("webhooks", []):
        if not webhook.get("enabled"):
            continue
        if not webhook.get("url"):
            logLine(f"webhook '{webhook.get('name')}' skipped: no url")
            continue
        pattern = webhook.get("matchPattern", ".*")
        try:
            if re.search(pattern, content):
                matches.append(webhook)
        except re.error as regexError:
            logLine(f"invalid matchPattern in webhook '{webhook.get('name')}': {regexError}")
    return matches


def sendWebhook(webhook, content, sourceWindow):
    body = {"content": content, "timestamp": time.time()}
    if webhook.get("includeSourceWindow", True):
        body["sourceWindow"] = sourceWindow
    data = json.dumps(body).encode("utf-8")
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


def dispatchAsync(content, sourceWindow, config, onDone=None):
    matches = matchingWebhooks(content, config)
    if not matches:
        if onDone:
            onDone([])
        return

    def worker():
        sentNames = []
        for webhook in matches:
            if sendWebhook(webhook, content, sourceWindow):
                sentNames.append(webhook.get("name", webhook["url"]))
        if onDone:
            onDone(sentNames)

    threading.Thread(target=worker, daemon=True).start()
