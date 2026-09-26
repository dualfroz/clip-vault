import contextlib
import io
import unittest
from unittest import mock

from notif_vault import cli


class ParseSinceTest(unittest.TestCase):
    def testUnits(self):
        self.assertEqual(cli.parseSince("30m"), 1800)
        self.assertEqual(cli.parseSince("2h"), 7200)
        self.assertEqual(cli.parseSince("1d"), 86400)

    def testFractionalAmount(self):
        self.assertEqual(cli.parseSince("1.5h"), 5400)

    def testEmptyMeansNoLimit(self):
        self.assertIsNone(cli.parseSince(None))
        self.assertIsNone(cli.parseSince(""))

    def testUnknownUnitIsRejected(self):
        with self.assertRaises(ValueError):
            cli.parseSince("5x")


class TailTest(unittest.TestCase):
    def testCtrlCExitsCleanly(self):
        rows = [(2, "Mail", "Second", "body two", 1, 1000.0), (1, "Mail", "First", "body one", 1, 900.0)]
        output = io.StringIO()
        with mock.patch.object(cli.storage, "queryNotifications", return_value=rows), \
                mock.patch.object(cli.time, "sleep", side_effect=KeyboardInterrupt), \
                contextlib.redirect_stdout(output):
            cli.cmdTail(None)
        lines = output.getvalue().splitlines()
        self.assertIn("Mail: First - body one", lines[1])
        self.assertIn("Mail: Second - body two", lines[2])


class PrintRowsTest(unittest.TestCase):
    def testLongTextIsTruncated(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cli.printRows([(1, "App", "s" * 100, "line one\nline two", 1, 0.0)])
        line = output.getvalue().strip()
        self.assertIn("App: " + "s" * 57 + "... - line one line two", line)

    def testNoRows(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cli.printRows([])
        self.assertEqual(output.getvalue().strip(), "(no notifications match)")


if __name__ == "__main__":
    unittest.main()
