import unittest
from datetime import datetime

from notif_vault.daemon import isIgnored, isWithinDnd, shouldForward


def at(clockTime):
    hour, minute = map(int, clockTime.split(":"))
    return datetime(2000, 1, 1, hour, minute)


def dndConfig(start, end, **extra):
    return {"doNotDisturb": {"enabled": True, "start": start, "end": end, **extra}}


class DoNotDisturbTest(unittest.TestCase):
    def testDisabledWindowNeverApplies(self):
        config = {"doNotDisturb": {"enabled": False, "start": "00:00", "end": "23:59"}}
        self.assertFalse(isWithinDnd(config, at("12:00")))
        self.assertFalse(isWithinDnd({}, at("12:00")))

    def testSameDayWindow(self):
        config = dndConfig("09:00", "17:00")
        self.assertTrue(isWithinDnd(config, at("09:00")))
        self.assertTrue(isWithinDnd(config, at("16:59")))
        self.assertFalse(isWithinDnd(config, at("17:00")))
        self.assertFalse(isWithinDnd(config, at("08:59")))

    def testWindowWrappingPastMidnight(self):
        config = dndConfig("23:00", "08:00")
        self.assertTrue(isWithinDnd(config, at("23:30")))
        self.assertTrue(isWithinDnd(config, at("00:00")))
        self.assertTrue(isWithinDnd(config, at("07:59")))
        self.assertFalse(isWithinDnd(config, at("08:00")))
        self.assertFalse(isWithinDnd(config, at("12:00")))


class ShouldForwardTest(unittest.TestCase):
    def testOutsideWindowEverythingIsForwarded(self):
        self.assertTrue(shouldForward(0, dndConfig("23:00", "08:00"), at("12:00")))

    def testInsideWindowOnlyCriticalIsForwarded(self):
        config = dndConfig("23:00", "08:00")
        self.assertFalse(shouldForward(1, config, at("02:00")))
        self.assertTrue(shouldForward(2, config, at("02:00")))

    def testAllowUrgentOffBlocksCritical(self):
        self.assertFalse(shouldForward(2, dndConfig("23:00", "08:00", allowUrgent=False), at("02:00")))


class IgnoreAppsTest(unittest.TestCase):
    def testGlobPatterns(self):
        config = {"ignoreApps": ["Spotify", "*Updater*"]}
        self.assertTrue(isIgnored("Spotify", config))
        self.assertTrue(isIgnored("Software Updater Tool", config))
        self.assertFalse(isIgnored("Thunderbird", config))
        self.assertFalse(isIgnored("Thunderbird", {}))


if __name__ == "__main__":
    unittest.main()
