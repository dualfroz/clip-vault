import itertools
import sqlite3
import unittest
from unittest import mock

from tests import testHome

from notif_vault import storage


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(str(storage.dbPath).startswith(testHome))
        storage.dbPath.unlink(missing_ok=True)
        self.clock = itertools.count(1000)
        patcher = mock.patch("time.time", side_effect=lambda: float(next(self.clock)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def add(self, appName, summary, body="", urgency=1):
        storage.addNotification(appName, summary, body, urgency, "icon")
        return storage.lastInsertId()

    def summaries(self, rows):
        return [row[2] for row in rows]

    def testNewestFirstWithAllColumns(self):
        self.add("Mail", "first", "body", 2)
        self.add("Chat", "second")
        rows = storage.queryNotifications()
        self.assertEqual(self.summaries(rows), ["second", "first"])
        self.assertEqual(rows[1][1:5], ("Mail", "first", "body", 2))

    def testFilterByAppSubstring(self):
        self.add("Thunderbird", "mail")
        self.add("Telegram", "chat")
        self.assertEqual(self.summaries(storage.queryNotifications(appName="thunder")), ["mail"])

    def testSearchInSummaryAndBody(self):
        self.add("CI", "build failed", "job 12")
        self.add("CI", "deploy", "build failed on step 3")
        self.add("CI", "all green")
        self.assertEqual(self.summaries(storage.queryNotifications(search="build failed")), ["deploy", "build failed"])

    def testSinceFilter(self):
        self.add("App", "old")
        self.clock = itertools.count(5000)
        self.add("App", "new")
        self.assertEqual(self.summaries(storage.queryNotifications(sinceSeconds=100)), ["new"])

    def testCombinedFiltersAndLimit(self):
        for index in range(5):
            self.add("Mail", f"mail {index}")
        self.add("Chat", "mail from chat")
        rows = storage.queryNotifications(appName="Mail", search="mail", limit=2)
        self.assertEqual(self.summaries(rows), ["mail 4", "mail 3"])

    def testTrimKeepsNewest(self):
        for index in range(5):
            self.add("App", f"n{index}")
        storage.trimHistory(2)
        self.assertEqual(self.summaries(storage.queryNotifications()), ["n4", "n3"])

    def testMarkWebhookSent(self):
        notificationId = self.add("App", "hello")
        storage.markWebhookSent(notificationId, ["phone", "desk"])
        connection = sqlite3.connect(storage.dbPath)
        sentTo = connection.execute("SELECT webhookSentTo FROM notifications WHERE id = ?", (notificationId,)).fetchone()[0]
        connection.close()
        self.assertEqual(sentTo, "phone,desk")

    def testLastInsertIdOnEmptyDatabase(self):
        self.assertIsNone(storage.lastInsertId())


if __name__ == "__main__":
    unittest.main()
