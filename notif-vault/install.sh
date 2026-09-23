#!/usr/bin/env bash
set -euo pipefail

sourceDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
installDir="$HOME/.local/share/notif-vault-src"
binDir="$HOME/.local/bin"
autostartFile="$HOME/.config/autostart/notif-vault.desktop"

mkdir -p "$installDir" "$binDir" "$(dirname "$autostartFile")"
rm -rf "$installDir/notif_vault"
cp -r "$sourceDir/notif_vault" "$installDir/"
cp "$sourceDir/config.default.json" "$installDir/config.default.json"

cat > "$binDir/notif-vault" <<EOF
#!/usr/bin/env bash
exec env PYTHONPATH="$installDir" python3 -m notif_vault.cli "\$@"
EOF
chmod +x "$binDir/notif-vault"

cat > "$binDir/notif-vault-daemon" <<EOF
#!/usr/bin/env bash
exec env PYTHONPATH="$installDir" python3 -m notif_vault.daemon
EOF
chmod +x "$binDir/notif-vault-daemon"

cat > "$autostartFile" <<EOF
[Desktop Entry]
Type=Application
Name=Notif Vault
Exec="$binDir/notif-vault-daemon"
X-GNOME-Autostart-enabled=true
EOF

echo "installed notif-vault into $installDir"
echo "commands: $binDir/notif-vault, $binDir/notif-vault-daemon"
echo "autostart entry: $autostartFile"
echo "start now with: notif-vault-daemon &"
echo "config file: ~/.config/notif-vault/config.json"
