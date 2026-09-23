#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
    "") purge=false ;;
    --purge) purge=true ;;
    *) echo "usage: $0 [--purge]" >&2; exit 1 ;;
esac

installDir="$HOME/.local/share/clip-vault"
binDir="$HOME/.local/bin"
autostartFile="$HOME/.config/autostart/clip-vault.desktop"
userDir="$HOME/.config/clip-vault"

pkill -f "python3 -m clip_vault\.daemon" || true

rm -rf "$installDir"
rm -f "$binDir/clip-vault" "$binDir/clip-vault-daemon" "$autostartFile"

echo "removed clip-vault"
if [ "$purge" = true ]; then
    rm -rf "$userDir"
    echo "removed config, history and log in $userDir"
else
    echo "config, history and log kept in $userDir (run with --purge to delete them)"
fi
