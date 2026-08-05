import json
import os
from pathlib import Path

configDir = Path.home() / ".config" / "notif-vault"
configPath = configDir / "config.json"
defaultConfigPath = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "config.default.json"


def loadConfig():
    if configPath.exists():
        with open(configPath) as f:
            return json.load(f)
    with open(defaultConfigPath) as f:
        return json.load(f)


def ensureUserConfig():
    if configPath.exists():
        return
    configDir.mkdir(parents=True, exist_ok=True)
    with open(defaultConfigPath) as f:
        default = f.read()
    with open(configPath, "w") as f:
        f.write(default)
