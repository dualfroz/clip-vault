import json
import unittest
from unittest import mock

from tests import testHome

from notif_vault import webhook


def hook(**overrides):
    entry = {"name": "phone", "enabled": True, "url": "https://example.invalid/hook"}
    entry.update(overrides)
    return entry


def readLog():
    if not webhook.logPath.exists():
        return ""
    return webhook.logPath.read_text()


class MatchingWebhooksTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(str(webhook.logPath).startswith(testHome))
        webhook.logPath.unlink(missing_ok=True)

    def names(self, appName, urgency, config):
        return [w["name"] for w in webhook.matchingWebhooks(appName, urgency, config)]

    def testDisabledWebhookIsSkipped(self):
        self.assertEqual(self.names("Mail", 2, {"webhooks": [hook(enabled=False)]}), [])

    def testAppPatternsAreGlobs(self):
        config = {"webhooks": [hook(name="calendar", appPatterns=["Thunderbird", "*Calendar*"])]}
        self.assertEqual(self.names("Thunderbird", 1, config), ["calendar"])
        self.assertEqual(self.names("GNOME Calendar", 1, config), ["calendar"])
        self.assertEqual(self.names("Telegram", 1, config), [])

    def testDefaultPatternMatchesEveryApp(self):
        self.assertEqual(self.names("Anything", 0, {"webhooks": [hook()]}), ["phone"])

    def testMinUrgency(self):
        config = {"webhooks": [hook(minUrgency=2)]}
        self.assertEqual(self.names("Mail", 1, config), [])
        self.assertEqual(self.names("Mail", 2, config), ["phone"])

    def testEnabledWebhookWithoutUrlIsSkipped(self):
        config = {"webhooks": [hook(name="empty", url=""), hook(name="missing", url=None)]}
        self.assertEqual(self.names("Mail", 2, config), [])
        self.assertIn("webhook 'empty' skipped: no url", readLog())
        self.assertIn("webhook 'missing' skipped: no url", readLog())


class SendWebhookTest(unittest.TestCase):
    def setUp(self):
        webhook.logPath.unlink(missing_ok=True)

    def testEmptyUrlFailsWithoutRaising(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            self.assertFalse(webhook.sendWebhook(hook(name="empty", url=""), "Mail", "summary", "body"))
        urlopen.assert_not_called()
        self.assertIn("webhook 'empty' failed", readLog())

    def testRequestCarriesJsonBody(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.status = 204
            self.assertTrue(webhook.sendWebhook(hook(headers={"X-Key": "abc"}), "Mail", "New mail", "hello"))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("X-key"), "abc")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 4)
        body = json.loads(request.data)
        self.assertEqual({key: body[key] for key in ("appName", "summary", "body")},
                         {"appName": "Mail", "summary": "New mail", "body": "hello"})
        self.assertIn("timestamp", body)
        self.assertIn("webhook 'phone' -> 204", readLog())


class DispatchAsyncTest(unittest.TestCase):
    def testEnabledWebhookWithoutUrlDoesNotStartSender(self):
        results = []
        with mock.patch("threading.Thread") as thread:
            webhook.dispatchAsync("Mail", "s", "b", 2, {"webhooks": [hook(url="")]}, onDone=results.append)
        thread.assert_not_called()
        self.assertEqual(results, [[]])


if __name__ == "__main__":
    unittest.main()
