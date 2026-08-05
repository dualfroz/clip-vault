#!/usr/bin/env bash
set -euo pipefail

sourceDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
installDir="$HOME/.local/share/clip-vault"
binDir="$HOME/.local/bin"
autostartDir="$HOME/.config/autostart"

mkdir -p "$installDir" "$binDir" "$autostartDir"
rsync -a --delete "$sourceDir/clip_vault" "$installDir/"
cp "$sourceDir/config.default.json" "$installDir/config.default.json"

cat > "$binDir/clip-vault" <<EOF
#!/usr/bin/env bash
exec python3 -m clip_vault.cli "\$@"
EOF
chmod +x "$binDir/clip-vault"

cat > "$binDir/clip-vault-daemon" <<EOF
#!/usr/bin/env bash
exec python3 -m clip_vault.daemon
EOF
chmod +x "$binDir/clip-vault-daemon"

cat > "$autostartDir/clip-vault.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Clip Vault
Exec=env PYTHONPATH=$installDir $binDir/clip-vault-daemon
X-GNOME-Autostart-enabled=true
EOF

echo "installed. PYTHONPATH must include $installDir when running clip-vault/clip-vault-daemon by hand:"
echo "  export PYTHONPATH=$installDir:\$PYTHONPATH"
echo "  clip-vault-daemon &   # starts tray + clipboard watcher"
echo "  clip-vault list       # view history from the CLI"
echo "config file: ~/.config/clip-vault/config.json (edit webhooks there)"
