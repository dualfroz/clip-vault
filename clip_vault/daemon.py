import hashlib
import re
import subprocess

import gi

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
except ValueError:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3

from gi.repository import GLib, Gtk

from clip_vault import storage, webhook
from clip_vault.config import loadConfig


def activeWindowTitle():
    try:
        output = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=1
        )
        return output.stdout.strip() if output.returncode == 0 else None
    except Exception:
        return None


class ClipVaultDaemon:
    def __init__(self):
        self.config = loadConfig()
        self.paused = False
        self.lastHash = None
        from gi.repository import Gdk
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.connect("owner-change", self.onOwnerChange)
        self.indicator = self.buildIndicator()

    def buildIndicator(self):
        indicator = AppIndicator3.Indicator.new(
            "clip-vault", "edit-copy-symbolic", AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        indicator.set_menu(self.buildMenu())
        return indicator

    def buildMenu(self):
        menu = Gtk.Menu()

        pauseItem = Gtk.CheckMenuItem(label="Pause capture")
        pauseItem.set_active(self.paused)
        pauseItem.connect("toggled", self.onTogglePause)
        menu.append(pauseItem)

        menu.append(Gtk.SeparatorMenuItem())

        recent = storage.listClips(limit=10)
        if recent:
            for clipId, content, sourceWindow, createdAt, pinned in recent:
                preview = content.replace("\n", " ").strip()
                if len(preview) > 60:
                    preview = preview[:57] + "..."
                label = ("* " if pinned else "") + preview
                item = Gtk.MenuItem(label=label or "(empty)")
                item.connect("activate", self.onRecopy, content)
                menu.append(item)
        else:
            emptyItem = Gtk.MenuItem(label="(no history yet)")
            emptyItem.set_sensitive(False)
            menu.append(emptyItem)

        menu.append(Gtk.SeparatorMenuItem())

        reloadItem = Gtk.MenuItem(label="Reload config")
        reloadItem.connect("activate", self.onReloadConfig)
        menu.append(reloadItem)

        quitItem = Gtk.MenuItem(label="Quit")
        quitItem.connect("activate", self.onQuit)
        menu.append(quitItem)

        menu.show_all()
        return menu

    def refreshMenu(self):
        self.indicator.set_menu(self.buildMenu())

    def onTogglePause(self, checkItem):
        self.paused = checkItem.get_active()

    def onRecopy(self, _menuItem, content):
        self.clipboard.set_text(content, -1)
        self.clipboard.store()

    def onReloadConfig(self, _menuItem):
        self.config = loadConfig()

    def onQuit(self, _menuItem):
        Gtk.main_quit()

    def isIgnored(self, content, sourceWindow):
        if sourceWindow:
            for pattern in self.config.get("ignoreWindowPatterns", []):
                if re.search(pattern, sourceWindow, re.IGNORECASE):
                    return True
        for pattern in self.config.get("ignoreContentPatterns", []):
            if re.search(pattern, content):
                return True
        return False

    def onOwnerChange(self, clipboard, _event):
        if self.paused:
            return
        GLib.idle_add(self.captureCurrentClipboard)

    def captureCurrentClipboard(self):
        text = self.clipboard.wait_for_text()
        if not text:
            return False
        content = text
        minLength = self.config.get("minContentLength", 2)
        maxLength = self.config.get("maxContentLength", 200000)
        if len(content) < minLength or len(content) > maxLength:
            return False

        contentHash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if contentHash == self.lastHash:
            return False
        self.lastHash = contentHash

        sourceWindow = activeWindowTitle()
        if self.isIgnored(content, sourceWindow):
            return False

        storage.addClip(content, contentHash, sourceWindow)
        storage.trimHistory(self.config.get("maxHistory", 500))

        def onWebhookDone(sentNames):
            if sentNames:
                GLib.idle_add(self.markWebhookSent, contentHash, sentNames)

        webhook.dispatchAsync(content, sourceWindow, self.config, onDone=onWebhookDone)

        GLib.idle_add(self.refreshMenu)
        return False

    def markWebhookSent(self, contentHash, sentNames):
        connection = storage.connect()
        connection.execute(
            "UPDATE clips SET webhookSentTo = ? WHERE id = (SELECT id FROM clips WHERE contentHash = ? ORDER BY id DESC LIMIT 1)",
            (",".join(sentNames), contentHash),
        )
        connection.commit()
        connection.close()
        return False


def main():
    daemon = ClipVaultDaemon()
    Gtk.main()


if __name__ == "__main__":
    main()
