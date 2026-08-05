#!/usr/bin/env bash
set -euo pipefail

sourceDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
installDir="$HOME/.local/share/notif-vault-src"
binDir="$HOME/.local/bin"
autostartDir="$HOME/.config/autostart"

mkdir -p "$installDir" "$binDir" "$autostartDir"
rsync -a --delete "$sourceDir/notif_vault" "$installDir/"
cp "$sourceDir/config.default.json" "$installDir/config.default.json"

cat > "$binDir/notif-vault" <<EOF
#!/usr/bin/env bash
exec env PYTHONPATH=$installDir python3 -m notif_vault.cli "\$@"
EOF
chmod +x "$binDir/notif-vault"

cat > "$binDir/notif-vault-daemon" <<EOF
#!/usr/bin/env bash
exec env PYTHONPATH=$installDir python3 -m notif_vault.daemon
EOF
chmod +x "$binDir/notif-vault-daemon"

cat > "$autostartDir/notif-vault.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Notif Vault
Exec=$binDir/notif-vault-daemon
X-GNOME-Autostart-enabled=true
EOF

echo "installed."
echo "  notif-vault-daemon &        # starts the background history logger"
echo "  notif-vault list            # search recent notifications"
echo "  notif-vault list --app discord --since 2h"
echo "  notif-vault tail            # live-follow new notifications"
echo "config file: ~/.config/notif-vault/config.json (do-not-disturb window + webhook forwarding rules)"
