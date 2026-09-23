import fnmatch
from datetime import datetime

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from notif_vault import storage, webhook
from notif_vault.config import ensureUserConfig, loadConfig


def isIgnored(appName, config):
    for pattern in config.get("ignoreApps", []):
        if fnmatch.fnmatch(appName, pattern):
            return True
    return False


def isWithinDnd(config, currentTime=None):
    dnd = config.get("doNotDisturb", {})
    if not dnd.get("enabled"):
        return False
    now = (currentTime or datetime.now()).strftime("%H:%M")
    start, end = dnd.get("start", "23:00"), dnd.get("end", "08:00")
    if start <= end:
        return start <= now < end
    return now >= start or now < end


def shouldForward(urgency, config, currentTime=None):
    if not isWithinDnd(config, currentTime):
        return True
    return config.get("doNotDisturb", {}).get("allowUrgent", True) and urgency == 2


class NotifVaultDaemon:
    def __init__(self):
        self.config = loadConfig()
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self.bus.add_match_string_non_blocking(
            "eavesdrop=true,interface='org.freedesktop.Notifications',member='Notify'"
        )
        self.bus.add_message_filter(self.onMessage)

    def onMessage(self, bus, message):
        if message.get_member() != "Notify" or message.get_interface() != "org.freedesktop.Notifications":
            return
        args = message.get_args_list()
        if len(args) < 8:
            return
        appName, _replacesId, icon, summary, body, _actions, hints, _expireTimeout = args[:8]
        appName = str(appName)
        if isIgnored(appName, self.config):
            return

        urgency = int(hints.get("urgency", 1)) if hasattr(hints, "get") else 1
        storage.addNotification(appName, str(summary), str(body), urgency, str(icon))
        storage.trimHistory(self.config.get("maxHistory", 5000))
        notificationId = storage.lastInsertId()

        if not shouldForward(urgency, self.config):
            return

        def onWebhookDone(sentNames):
            if sentNames and notificationId:
                storage.markWebhookSent(notificationId, sentNames)

        webhook.dispatchAsync(appName, str(summary), str(body), urgency, self.config, onDone=onWebhookDone)


def main():
    ensureUserConfig()
    NotifVaultDaemon()
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
