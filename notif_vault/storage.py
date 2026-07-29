import sqlite3
import time
from pathlib import Path

dbDir = Path.home() / ".local" / "share" / "notif-vault"
dbPath = dbDir / "notifications.db"


def connect():
    dbDir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(dbPath)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appName TEXT,
            summary TEXT,
            body TEXT,
            urgency INTEGER,
            icon TEXT,
            createdAt REAL,
            webhookSentTo TEXT
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idxCreatedAt ON notifications(createdAt)")
    connection.execute("CREATE INDEX IF NOT EXISTS idxAppName ON notifications(appName)")
    return connection


def addNotification(appName, summary, body, urgency, icon):
    connection = connect()
    connection.execute(
        "INSERT INTO notifications (appName, summary, body, urgency, icon, createdAt) VALUES (?, ?, ?, ?, ?, ?)",
        (appName, summary, body, urgency, icon, time.time()),
    )
    connection.commit()
    connection.close()


def markWebhookSent(notificationId, sentNames):
    connection = connect()
    connection.execute(
        "UPDATE notifications SET webhookSentTo = ? WHERE id = ?",
        (",".join(sentNames), notificationId),
    )
    connection.commit()
    connection.close()


def trimHistory(maxHistory):
    connection = connect()
    connection.execute(
        "DELETE FROM notifications WHERE id NOT IN (SELECT id FROM notifications ORDER BY id DESC LIMIT ?)",
        (maxHistory,),
    )
    connection.commit()
    connection.close()


def lastInsertId():
    connection = connect()
    row = connection.execute("SELECT id FROM notifications ORDER BY id DESC LIMIT 1").fetchone()
    connection.close()
    return row[0] if row else None


def queryNotifications(appName=None, search=None, sinceSeconds=None, limit=50):
    connection = connect()
    clauses = []
    params = []
    if appName:
        clauses.append("appName LIKE ?")
        params.append(f"%{appName}%")
    if search:
        clauses.append("(summary LIKE ? OR body LIKE ?)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    if sinceSeconds:
        clauses.append("createdAt >= ?")
        params.append(time.time() - sinceSeconds)
    whereClause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"SELECT id, appName, summary, body, urgency, createdAt FROM notifications {whereClause} ORDER BY id DESC LIMIT ?",
        (*params, limit),
    ).fetchall()
    connection.close()
    return rows
