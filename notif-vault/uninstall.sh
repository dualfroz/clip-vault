#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
    "") purge=false ;;
    --purge) purge=true ;;
    *) echo "usage: $0 [--purge]" >&2; exit 1 ;;
esac

installDir="$HOME/.local/share/notif-vault-src"
binDir="$HOME/.local/bin"
autostartFile="$HOME/.config/autostart/notif-vault.desktop"
configDir="$HOME/.config/notif-vault"
dataDir="$HOME/.local/share/notif-vault"

pkill -f "python3 -m notif_vault\.daemon" || true

rm -rf "$installDir"
rm -f "$binDir/notif-vault" "$binDir/notif-vault-daemon" "$autostartFile"

echo "removed notif-vault"
if [ "$purge" = true ]; then
    rm -rf "$configDir" "$dataDir"
    echo "removed $configDir and $dataDir"
else
    echo "config kept in $configDir, history and log kept in $dataDir (run with --purge to delete them)"
fi
