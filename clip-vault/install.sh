#!/usr/bin/env bash
set -euo pipefail

sourceDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
installDir="$HOME/.local/share/clip-vault"
binDir="$HOME/.local/bin"
autostartFile="$HOME/.config/autostart/clip-vault.desktop"

mkdir -p "$installDir" "$binDir" "$(dirname "$autostartFile")"
rm -rf "$installDir/clip_vault"
cp -r "$sourceDir/clip_vault" "$installDir/"
cp "$sourceDir/config.default.json" "$installDir/config.default.json"

cat > "$binDir/clip-vault" <<EOF
#!/usr/bin/env bash
exec env PYTHONPATH="$installDir" python3 -m clip_vault.cli "\$@"
EOF
chmod +x "$binDir/clip-vault"

cat > "$binDir/clip-vault-daemon" <<EOF
#!/usr/bin/env bash
exec env PYTHONPATH="$installDir" python3 -m clip_vault.daemon
EOF
chmod +x "$binDir/clip-vault-daemon"

cat > "$autostartFile" <<EOF
[Desktop Entry]
Type=Application
Name=Clip Vault
Exec="$binDir/clip-vault-daemon"
X-GNOME-Autostart-enabled=true
EOF

echo "installed clip-vault into $installDir"
echo "commands: $binDir/clip-vault, $binDir/clip-vault-daemon"
echo "autostart entry: $autostartFile"
echo "start now with: clip-vault-daemon &"
echo "config file: ~/.config/clip-vault/config.json"
