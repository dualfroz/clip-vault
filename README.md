# clip-vault

Two small background daemons for Linux desktops that keep a searchable local
history of things that normally vanish the moment they happen, and can forward
them to a webhook if you ask them to.

| Tool | Keeps a history of | Interface |
| --- | --- | --- |
| [`clip-vault`](#clip-vault-1) | Everything you copy to the clipboard | Tray icon + CLI |
| [`notif-vault`](#notif-vault) | Every desktop notification you receive | CLI only |

They live in one repository because they are the same idea applied twice: watch
a stream of short-lived desktop events, write them to a local SQLite database,
make them searchable afterwards, and optionally fan them out to HTTP endpoints
with per-rule filters. They share no code and can be installed independently.

Both store everything locally. Nothing is sent anywhere unless you write a
webhook into the config yourself, and every webhook ships disabled by default.

---

## clip-vault

A clipboard manager. It watches the X11 clipboard, stores every distinct thing
you copy, and gives you the history back through a tray menu and a CLI.

### Features

- **History with de-duplication.** Content is hashed with SHA-256; copying the
  same thing twice moves the existing entry to the top instead of duplicating
  it. The history is trimmed to `maxHistory` entries (500 by default).
- **Pinning.** Pinned clips survive both trimming and `clip-vault clear`.
- **Source window.** Each clip records the title of the window that was focused
  when you copied it, so you can tell the password you copied from your browser
  from the one you copied from your terminal.
- **Password-manager blindness.** Clips are dropped, not stored, when the source
  window matches `ignoreWindowPatterns` (KeePassXC, Bitwarden and 1Password out
  of the box) or when the content matches `ignoreContentPatterns` (PEM private
  key headers out of the box).
- **Tray menu.** Pause capture, re-copy any of the last 10 clips with one click,
  reload the config, quit.
- **Webhook fan-out.** Any clip matching a regex can be POSTed to an HTTP
  endpoint in a background thread. Useful for pushing snippets to a note-taking
  service or a chat channel.

### Requirements

- Python 3, X11 (this will not work on a Wayland session)
- PyGObject with GTK 3 and an app-indicator library — either
  `AyatanaAppIndicator3` or the older `AppIndicator3`
- `xdotool` — reads the focused window title
- `xclip` — used by `clip-vault copy` to put a stored clip back on the clipboard

On a Debian or Ubuntu derivative:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 xdotool xclip
```

### Installing

```bash
cd clip-vault
./install.sh
```

This copies the package into `~/.local/share/clip-vault`, drops `clip-vault`
and `clip-vault-daemon` wrappers into `~/.local/bin`, and adds an autostart
entry so the daemon starts with your session.

One rough edge worth knowing: the two wrapper scripts do **not** set
`PYTHONPATH` themselves, so running them by hand from a fresh shell needs it
exported first. The autostart entry sets it for you, so this only affects
manual runs.

```bash
export PYTHONPATH="$HOME/.local/share/clip-vault:$PYTHONPATH"
clip-vault-daemon &
```

### Using it

```bash
clip-vault list                  # 30 most recent clips
clip-vault list --search ssh     # filter by content
clip-vault show 42               # print a clip in full
clip-vault copy 42               # put it back on the clipboard
clip-vault pin 42                # protect it from trimming and clear
clip-vault delete 42
clip-vault clear                 # wipe history, keeping pinned clips
clip-vault clear --all           # wipe everything
clip-vault config                # print config and log file paths
clip-vault test-webhook my-hook  # send a test payload through a webhook
```

### Configuration

`~/.config/clip-vault/config.json`, created from the bundled defaults on first
run. The daemon re-reads it when you pick "Reload config" from the tray menu.

| Key | Default | Meaning |
| --- | --- | --- |
| `maxHistory` | `500` | Unpinned clips to keep |
| `minContentLength` | `2` | Ignore anything shorter |
| `maxContentLength` | `200000` | Ignore anything longer |
| `ignoreWindowPatterns` | KeePassXC, Bitwarden, 1Password | Case-insensitive regexes matched against the source window title |
| `ignoreContentPatterns` | PEM private key header | Regexes matched against the clip content |
| `webhooks` | one disabled example | See below |

`pollFallbackSeconds` also appears in the default config but is not currently
read by any code.

A webhook entry:

```json
{
  "name": "notes",
  "enabled": true,
  "url": "https://example.com/hook",
  "method": "POST",
  "matchPattern": "^TODO:",
  "headers": { "Authorization": "Bearer ..." },
  "timeoutSeconds": 4,
  "includeSourceWindow": true
}
```

`matchPattern` is a regex tested against the clip content — `.*` forwards
everything. The request body is JSON:

```json
{ "content": "...", "timestamp": 1234567890.0, "sourceWindow": "Firefox" }
```

`sourceWindow` is omitted when `includeSourceWindow` is false.

### Files it writes

- `~/.config/clip-vault/config.json` — configuration
- `~/.config/clip-vault/history.sqlite3` — the clipboard history
- `~/.config/clip-vault/webhook.log` — one line per webhook attempt

**The history database is plain, unencrypted SQLite.** The ignore patterns
reduce what ends up in it, but anything you copy that is not filtered out is
readable by anything running as your user. Treat it accordingly.

---

## notif-vault

A searchable archive of your desktop notifications. It listens on the session
D-Bus for `org.freedesktop.Notifications.Notify` calls, records every one, and
lets you search them afterwards from the command line.

This is a *passive recorder*: it does not display, suppress or replace your
notifications, and your normal notification daemon keeps working untouched.

### Features

- **Full history** of app name, summary, body, urgency and icon, with a
  configurable cap (5000 by default).
- **Search and filter** by app, by text, by age.
- **Live tail** of incoming notifications in a terminal.
- **App ignore list** using shell-style globs.
- **Do-not-disturb window** that suppresses *webhook forwarding* during set
  hours, optionally letting critical notifications through. It does not
  suppress the notifications themselves — they are still recorded and still
  appear on screen.
- **Webhook fan-out** filtered by app glob and minimum urgency.

### Requirements

- Python 3
- `python3-dbus` and PyGObject (`GLib`)
- A session D-Bus that permits eavesdropping. The daemon adds a match rule with
  `eavesdrop=true`; on distributions that have tightened D-Bus policy this may
  need to be allowed explicitly before any notifications are captured.

On a Debian or Ubuntu derivative:

```bash
sudo apt install python3-dbus python3-gi
```

### Installing

```bash
cd notif-vault
./install.sh
```

Copies the package into `~/.local/share/notif-vault-src`, installs
`notif-vault` and `notif-vault-daemon` into `~/.local/bin` (these wrappers do
set `PYTHONPATH` correctly), and adds an autostart entry.

```bash
notif-vault-daemon &
```

### Using it

```bash
notif-vault list                            # 50 most recent
notif-vault list --app discord              # filter by app name substring
notif-vault list --search "build failed"    # filter by summary or body text
notif-vault list --since 2h                 # 30m, 2h and 1d are all valid
notif-vault tail                            # follow new notifications live
```

### Configuration

`~/.config/notif-vault/config.json`, created from the bundled defaults the
first time the daemon starts.

| Key | Default | Meaning |
| --- | --- | --- |
| `maxHistory` | `5000` | Notifications to keep |
| `ignoreApps` | `[]` | Glob patterns; matching apps are never recorded |
| `doNotDisturb.enabled` | `false` | Turn the quiet window on |
| `doNotDisturb.start` / `.end` | `23:00` / `08:00` | Quiet window, may wrap past midnight |
| `doNotDisturb.allowUrgent` | `true` | Let critical notifications through the quiet window |
| `webhooks` | one disabled example | See below |

A webhook entry:

```json
{
  "name": "phone",
  "url": "https://example.com/hook",
  "enabled": true,
  "appPatterns": ["Thunderbird", "*Calendar*"],
  "minUrgency": 2,
  "headers": {},
  "timeoutSeconds": 4
}
```

Urgency is the freedesktop scale: `0` low, `1` normal, `2` critical. The
request body is JSON:

```json
{ "appName": "Thunderbird", "summary": "...", "body": "...", "timestamp": 1234567890.0 }
```

### Files it writes

- `~/.config/notif-vault/config.json` — configuration
- `~/.local/share/notif-vault/notifications.db` — the notification history
- `~/.local/share/notif-vault/webhook.log` — one line per webhook attempt

Notification bodies routinely contain message previews, one-time codes and
other things you would not want lying around. The database is unencrypted
SQLite — use `ignoreApps` for anything sensitive.

---

## Tested on

Linux Mint 22.2 with the Cinnamon desktop, on an X11 session. `clip-vault`
depends on X11 outright. `notif-vault` only needs a session D-Bus and should
work on any freedesktop-compliant desktop, but Cinnamon on X11 is the only
place it has actually been run.

## Licence

No licence has been chosen yet.
