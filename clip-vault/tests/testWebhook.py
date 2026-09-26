import json
import os
import unittest
from unittest import mock

from tests import testHome

from clip_vault import webhook
from clip_vault.config import logPath


def hook(**overrides):
    entry = {"name": "notes", "enabled": True, "url": "https://example.invalid/hook", "matchPattern": ".*"}
    entry.update(overrides)
    return entry


def readLog():
    if not os.path.exists(logPath):
        return ""
    with open(logPath) as logFile:
        return logFile.read()


class MatchingWebhooksTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(logPath.startswith(testHome))
        if os.path.exists(logPath):
            os.remove(logPath)

    def testDisabledWebhookIsSkipped(self):
        config = {"webhooks": [hook(enabled=False)]}
        self.assertEqual(webhook.matchingWebhooks("anything", config), [])

    def testPatternDecidesMatch(self):
        todo = hook(name="todo", matchPattern="^TODO:")
        config = {"webhooks": [todo, hook(name="all")]}
        self.assertEqual([w["name"] for w in webhook.matchingWebhooks("TODO: call", config)], ["todo", "all"])
        self.assertEqual([w["name"] for w in webhook.matchingWebhooks("note", config)], ["all"])

    def testInvalidPatternIsLoggedAndSkipped(self):
        config = {"webhooks": [hook(name="broken", matchPattern="(")]}
        self.assertEqual(webhook.matchingWebhooks("text", config), [])
        self.assertIn("invalid matchPattern in webhook 'broken'", readLog())

    def testEnabledWebhookWithoutUrlIsSkipped(self):
        config = {"webhooks": [hook(name="empty", url=""), hook(name="missing", url=None)]}
        self.assertEqual(webhook.matchingWebhooks("text", config), [])
        self.assertIn("webhook 'empty' skipped: no url", readLog())
        self.assertIn("webhook 'missing' skipped: no url", readLog())


class SendWebhookTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(logPath):
            os.remove(logPath)

    def testEmptyUrlFailsWithoutRaising(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            self.assertFalse(webhook.sendWebhook(hook(name="empty", url=""), "text", "Terminal"))
        urlopen.assert_not_called()
        self.assertIn("webhook 'empty' failed", readLog())

    def testRequestCarriesJsonBodyHeadersAndMethod(self):
        target = hook(method="PUT", headers={"Authorization": "Bearer test"}, timeoutSeconds=2)
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.status = 200
            self.assertTrue(webhook.sendWebhook(target, "hello", "Terminal"))
        request = urlopen.call_args.args[0]
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 2)
        self.assertEqual(request.get_method(), "PUT")
        self.assertEqual(request.full_url, "https://example.invalid/hook")
        self.assertEqual(request.get_header("Authorization"), "Bearer test")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        body = json.loads(request.data)
        self.assertEqual(body["content"], "hello")
        self.assertEqual(body["sourceWindow"], "Terminal")
        self.assertIn("timestamp", body)
        self.assertIn("webhook 'notes' -> 200", readLog())

    def testSourceWindowCanBeLeftOut(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.status = 200
            webhook.sendWebhook(hook(includeSourceWindow=False), "hello", "Terminal")
        self.assertNotIn("sourceWindow", json.loads(urlopen.call_args.args[0].data))

    def testNetworkErrorIsLoggedAsFailure(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("unreachable")):
            self.assertFalse(webhook.sendWebhook(hook(), "hello", "Terminal"))
        self.assertIn("webhook 'notes' failed: unreachable", readLog())


class DispatchAsyncTest(unittest.TestCase):
    def testNoMatchReportsEmptyListImmediately(self):
        results = []
        webhook.dispatchAsync("text", "Terminal", {"webhooks": [hook(url="")]}, onDone=results.append)
        self.assertEqual(results, [[]])


if __name__ == "__main__":
    unittest.main()
