# clip-vault

Two small background daemons for Linux desktops that keep a searchable local
history of things that normally disappear the moment they happen: `clip-vault`
records what you copy to the clipboard, `notif-vault` records the desktop
notifications you receive. Both write to a local SQLite database, let you
search it afterwards from the command line, and can optionally forward events
to HTTP webhooks with per-webhook filters. They share no code and install
independently. Nothing leaves the machine unless you enable a webhook yourself;
the bundled example webhooks are disabled.

| Tool | Keeps a history of | Interface |
| --- | --- | --- |
| [`clip-vault`](#clip-vault-1) | Text copied to the clipboard | Tray icon and CLI |
| [`notif-vault`](#notif-vault) | Desktop notifications | CLI |

## clip-vault

A clipboard manager. It watches the X11 clipboard, stores every distinct piece
of text you copy, and gives the history back through a tray menu and a CLI.

### Features

- **History with de-duplication.** Each clip is identified by the SHA-256 of
  its content. Copying something already in the history moves the existing
  entry to the top (same id, updated time and source window) instead of
  storing it twice. Unpinned clips are trimmed to `maxHistory`.
- **Pinning.** Pinned clips are never trimmed, stay pinned when copied again,
  and survive `clip-vault clear` (but not `clear --all`).
- **Source window.** Each clip records the title of the window that was focused
  when it was copied (read with `xdotool`).
- **Filtering before storage.** A clip is dropped, not stored, when the source
  window title matches one of `ignoreWindowPatterns` (case-insensitive; KeePassXC,
  Bitwarden and 1Password by default), when the content matches one of
  `ignoreContentPatterns` (PEM private key headers by default), or when its
  length is outside `minContentLength`..`maxContentLength`.
- **Tray menu.** Pause and resume capture, copy any of the 10 most recent clips
  back to the clipboard (pinned ones are marked with `*`), reload the config,
  quit. The menu updates after every new clip.
- **CLI** to list, search, show, copy back, pin, unpin and delete clips, and to
  clear the history.
- **Webhooks.** Every stored clip whose content matches a webhook's
  `matchPattern` regex is sent to that webhook as JSON from a background
  thread. Each delivery result is logged, and the names of the webhooks that
  accepted a clip are saved with it in the database. An enabled webhook
  without a `url` is skipped and logged. `clip-vault test-webhook` sends a
  test payload through a named webhook, whether it is enabled or not.

### Requirements

- Python 3 and an X11 desktop (Wayland is not supported)
- PyGObject with GTK 3 and an app-indicator library, either
  `AyatanaAppIndicator3` or the older `AppIndicator3`
- `xdotool` to read the focused window title (without it clips are stored with
  no source window and window patterns never match)
- `xclip` for `clip-vault copy`

On Debian, Ubuntu and Linux Mint:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 xdotool xclip
```

### Usage

```bash
clip-vault-daemon &                     # tray icon and clipboard watcher
clip-vault list                         # 30 most recent clips
clip-vault list --search ssh --limit 100
clip-vault show 42                      # print a clip in full
clip-vault copy 42                      # put it back on the clipboard
clip-vault pin 42                       # protect it from trimming and clear
clip-vault unpin 42
clip-vault delete 42
clip-vault clear                        # delete history, keep pinned clips
clip-vault clear --all                  # delete everything
clip-vault config                       # print the config and log file paths
clip-vault test-webhook notes --content "hello"
```

`list` prints one line per clip: id, `*` for pinned, time, source window in
brackets and the first 80 characters of the content. `--search` is a substring
match.

### Configuration

`~/.config/clip-vault/config.json` is created from `config.default.json` the
first time the daemon starts. The daemon re-reads it when you choose "Reload
config" in the tray menu.

| Key | Default | Meaning |
| --- | --- | --- |
| `maxHistory` | `500` | Unpinned clips to keep |
| `minContentLength` | `2` | Shorter clips are ignored |
| `maxContentLength` | `200000` | Longer clips are ignored |
| `ignoreWindowPatterns` | KeePassXC, Bitwarden, 1Password | Case-insensitive regexes matched against the source window title |
| `ignoreContentPatterns` | PEM private key header | Regexes matched against the content |
| `webhooks` | one disabled example | See below |

A webhook entry:

```json
{
  "name": "notes",
  "enabled": true,
  "url": "https://example.com/hook",
  "method": "POST",
  "matchPattern": "^TODO:",
  "headers": { "Authorization": "Bearer <token>" },
  "timeoutSeconds": 4,
  "includeSourceWindow": true
}
```

`matchPattern` defaults to `.*` (every clip), `method` to `POST`,
`timeoutSeconds` to `4` and `includeSourceWindow` to `true`. The request body:

```json
{ "content": "...", "timestamp": 1234567890.0, "sourceWindow": "Firefox" }
```

`sourceWindow` is left out when `includeSourceWindow` is `false`.

### Files

| Path | Contents |
| --- | --- |
| `~/.config/clip-vault/config.json` | Configuration |
| `~/.config/clip-vault/history.sqlite3` | Clipboard history |
| `~/.config/clip-vault/webhook.log` | One line per webhook delivery result |

## notif-vault

A searchable archive of desktop notifications. It listens on the per-user
D-Bus bus for `org.freedesktop.Notifications.Notify` calls, records each one
and lets you search them from the command line. It is a passive recorder: it
does not display, hide or replace notifications, and the normal notification
daemon keeps working as before.

### Features

- **History** of app name, summary, body, urgency and icon for every
  notification, capped at `maxHistory` (oldest entries are removed first).
- **Search** by app name, by text in the summary or body, and by age.
- **Live tail** that prints the 20 most recent notifications and then every new
  one as it arrives.
- **App ignore list.** Apps matching a shell-style glob in `ignoreApps` are
  never recorded.
- **Webhooks**, filtered per webhook by app glob and minimum urgency. Each
  delivery result is logged, and the names of the webhooks that accepted a
  notification are saved with it in the database.
- **Do-not-disturb window** that pauses webhook forwarding during set hours,
  optionally still letting critical notifications through. Notifications are
  still recorded during the window and still appear on screen.

### Requirements

- Python 3
- `python3-dbus` and PyGObject (`GLib`)
- A D-Bus policy that allows eavesdropping. The daemon adds a match rule with
  `eavesdrop=true`; where the bus policy forbids it, nothing is captured until
  it is allowed.

On Debian, Ubuntu and Linux Mint:

```bash
sudo apt install python3-dbus python3-gi
```

### Usage

```bash
notif-vault-daemon &                          # background recorder
notif-vault list                              # 50 most recent
notif-vault list --app thunderbird            # app name substring
notif-vault list --search "build failed"      # text in summary or body
notif-vault list --since 2h --limit 200       # age as <number>m, h or d
notif-vault tail                              # follow new notifications
```

`list` prints one line per notification: time, app name, the summary (up to 60
characters) and the body (up to 80 characters).

### Configuration

`~/.config/notif-vault/config.json` is created from `config.default.json` the
first time the daemon starts. The daemon reads it once at startup; restart it
after editing.

| Key | Default | Meaning |
| --- | --- | --- |
| `maxHistory` | `5000` | Notifications to keep |
| `ignoreApps` | `[]` | Glob patterns; matching apps are never recorded |
| `doNotDisturb.enabled` | `false` | Turn the quiet window on |
| `doNotDisturb.start` / `doNotDisturb.end` | `23:00` / `08:00` | Quiet window in local time, may wrap past midnight |
| `doNotDisturb.allowUrgent` | `true` | Forward critical notifications during the quiet window |
| `webhooks` | one disabled example | See below |

A webhook entry:

```json
{
  "name": "phone",
  "enabled": true,
  "url": "https://example.com/hook",
  "method": "POST",
  "appPatterns": ["Thunderbird", "*Calendar*"],
  "minUrgency": 2,
  "headers": {},
  "timeoutSeconds": 4
}
```

`appPatterns` defaults to `["*"]`, `minUrgency` to `0`, `method` to `POST` and
`timeoutSeconds` to `4`. An enabled webhook without a `url` is skipped and
logged. Urgency follows the freedesktop scale: `0` low, `1`
normal, `2` critical; a notification without an urgency hint counts as `1`.
The request body:

```json
{ "appName": "Thunderbird", "summary": "...", "body": "...", "timestamp": 1234567890.0 }
```

### Files

| Path | Contents |
| --- | --- |
| `~/.config/notif-vault/config.json` | Configuration |
| `~/.local/share/notif-vault/notifications.db` | Notification history |
| `~/.local/share/notif-vault/webhook.log` | One line per webhook delivery result |

## Install and run

Each tool has its own `install.sh` and `uninstall.sh`. Installing copies the
package into `~/.local/share/`, puts two wrapper commands into `~/.local/bin`
(they set `PYTHONPATH` themselves) and adds an autostart entry so the daemon
starts when you log in:

```bash
./clip-vault/install.sh     # clip-vault, clip-vault-daemon; package in ~/.local/share/clip-vault
./notif-vault/install.sh    # notif-vault, notif-vault-daemon; package in ~/.local/share/notif-vault-src
```

Uninstalling stops the running daemon and removes the package, the wrappers
and the autostart entry. Configuration, history and logs are kept unless you
pass `--purge`:

```bash
./clip-vault/uninstall.sh [--purge]
./notif-vault/uninstall.sh [--purge]
```

Both tools also run from a checkout without installing:

```bash
PYTHONPATH=clip-vault python3 -m clip_vault.daemon &
PYTHONPATH=clip-vault python3 -m clip_vault.cli list
PYTHONPATH=notif-vault python3 -m notif_vault.daemon &
PYTHONPATH=notif-vault python3 -m notif_vault.cli list
```

There is nothing to build.

## Tests

Each tool has unit tests written with the standard library `unittest` module,
so they need nothing beyond the runtime requirements. Run them from the
repository root:

```bash
python3 -m unittest discover -s clip-vault/tests -t clip-vault
python3 -m unittest discover -s notif-vault/tests -t notif-vault
```

The tests point `HOME` at a temporary directory, so they never touch your real
config or history, and they make no network calls: HTTP delivery is checked
against a mocked `urlopen`.

- `clip-vault`: storage (ordering, de-duplication, pins surviving re-copy,
  trimming, clear with and without pinned clips, search, limit, delete) and
  webhooks (pattern matching, invalid patterns, missing `url`, request body,
  headers and method, failure logging).
- `notif-vault`: `--since` parsing, clean exit of `tail` on Ctrl-C, output
  formatting, the do-not-disturb window including windows that wrap past
  midnight, the forwarding decision for critical notifications, the app ignore
  list, storage filters and trimming, and webhook matching by app glob,
  urgency and missing `url`.

The tray icon and the D-Bus listener are checked by hand. Static checks:

```bash
python3 -m py_compile clip-vault/clip_vault/*.py notif-vault/notif_vault/*.py
bash -n clip-vault/*.sh notif-vault/*.sh
```

## Project layout

```
clip-vault/
  clip_vault/
    daemon.py           clipboard watcher and tray menu
    cli.py              clip-vault command
    storage.py          SQLite history
    webhook.py          webhook matching, sending and logging
    config.py           config and data paths, default config install
  tests/                unit tests
  config.default.json
  install.sh
  uninstall.sh
notif-vault/
  notif_vault/
    daemon.py           D-Bus listener, ignore list, do-not-disturb
    cli.py              notif-vault command
    storage.py          SQLite history
    webhook.py          webhook matching, sending and logging
    config.py           config paths and default config install
  tests/                unit tests
  config.default.json
  install.sh
  uninstall.sh
```

## Limitations

- **Both databases are plain, unencrypted SQLite**, readable by anything that
  runs as your user. Clipboard history and notification bodies routinely hold
  passwords, message previews and one-time codes. The ignore lists reduce what
  is stored; use them for anything sensitive.
- `clip-vault` needs X11 and watches only the `CLIPBOARD` selection (not the
  middle-click `PRIMARY` selection). Only text is recorded; images and files
  are ignored.
- The tray pause state is not remembered across restarts.
- `notif-vault` relies on D-Bus eavesdropping, which newer bus configurations
  may restrict.
- `notif-vault` reads its config only at startup, and `tail` polls the
  database once per second.
- Tested on Linux Mint 22.2 with Cinnamon on X11. `notif-vault` should work on
  any freedesktop-compliant desktop but has only been run there.

## License

MIT. See [LICENSE](LICENSE).
