import json
import os

configDir = os.path.expanduser("~/.config/clip-vault")
configPath = os.path.join(configDir, "config.json")
defaultConfigPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.default.json")
dbPath = os.path.join(configDir, "history.sqlite3")
logPath = os.path.join(configDir, "webhook.log")


def loadConfig():
    if not os.path.exists(configPath):
        installDefaultConfig()
    with open(configPath) as configFile:
        return json.load(configFile)


def installDefaultConfig():
    os.makedirs(configDir, exist_ok=True)
    with open(defaultConfigPath) as defaultFile:
        defaultContent = defaultFile.read()
    with open(configPath, "w") as configFile:
        configFile.write(defaultContent)


def saveConfig(config):
    os.makedirs(configDir, exist_ok=True)
    with open(configPath, "w") as configFile:
        json.dump(config, configFile, indent=2)
