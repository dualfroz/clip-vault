import hashlib
import itertools
import os
import unittest
from unittest import mock

from tests import testHome

from clip_vault import storage
from clip_vault.config import dbPath


def addText(text, sourceWindow="Terminal"):
    storage.addClip(text, hashlib.sha256(text.encode("utf-8")).hexdigest(), sourceWindow)


def contents(rows):
    return [row[1] for row in rows]


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(dbPath.startswith(testHome))
        if os.path.exists(dbPath):
            os.remove(dbPath)
        clock = itertools.count(1000)
        patcher = mock.patch("time.time", side_effect=lambda: float(next(clock)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def idOf(self, text):
        return next(row[0] for row in storage.listClips(limit=1000) if row[1] == text)

    def testNewestFirst(self):
        addText("first")
        addText("second")
        self.assertEqual(contents(storage.listClips()), ["second", "first"])

    def testRecopyMovesExistingEntryToTop(self):
        addText("alpha")
        alphaId = self.idOf("alpha")
        addText("beta")
        addText("alpha", sourceWindow="Browser")
        rows = storage.listClips()
        self.assertEqual(contents(rows), ["alpha", "beta"])
        self.assertEqual(rows[0][0], alphaId)
        self.assertEqual(rows[0][2], "Browser")

    def testRecopyKeepsPinnedClipPinned(self):
        addText("alpha")
        alphaId = self.idOf("alpha")
        storage.setPinned(alphaId, True)
        addText("beta")
        addText("alpha")
        self.assertEqual(storage.getClip(alphaId)[4], 1)
        self.assertEqual(contents(storage.listClips()), ["alpha", "beta"])

    def testTrimKeepsPinnedAndNewest(self):
        for text in ["one", "two", "three", "four", "five"]:
            addText(text)
        storage.setPinned(self.idOf("one"), True)
        storage.trimHistory(2)
        self.assertEqual(contents(storage.listClips()), ["five", "four", "one"])

    def testClearKeepsPinned(self):
        addText("keep")
        addText("drop")
        storage.setPinned(self.idOf("keep"), True)
        storage.clearHistory()
        self.assertEqual(contents(storage.listClips()), ["keep"])

    def testClearAllRemovesPinned(self):
        addText("keep")
        storage.setPinned(self.idOf("keep"), True)
        storage.clearHistory(keepPinned=False)
        self.assertEqual(storage.listClips(), [])

    def testUnpin(self):
        addText("alpha")
        alphaId = self.idOf("alpha")
        storage.setPinned(alphaId, True)
        storage.setPinned(alphaId, False)
        self.assertEqual(storage.getClip(alphaId)[4], 0)

    def testSearchIsSubstringMatch(self):
        addText("ssh user@host")
        addText("git status")
        addText("Copy SSH key")
        self.assertEqual(contents(storage.listClips(search="ssh")), ["Copy SSH key", "ssh user@host"])

    def testListLimit(self):
        for text in ["one", "two", "three"]:
            addText(text)
        self.assertEqual(contents(storage.listClips(limit=2)), ["three", "two"])

    def testDeleteAndMissingClip(self):
        addText("alpha")
        alphaId = self.idOf("alpha")
        storage.deleteClip(alphaId)
        self.assertIsNone(storage.getClip(alphaId))


if __name__ == "__main__":
    unittest.main()
