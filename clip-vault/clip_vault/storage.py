import os
import sqlite3
import time

from clip_vault.config import configDir, dbPath


def connect():
    os.makedirs(configDir, exist_ok=True)
    connection = sqlite3.connect(dbPath)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            contentHash TEXT NOT NULL,
            sourceWindow TEXT,
            createdAt REAL NOT NULL,
            pinned INTEGER NOT NULL DEFAULT 0,
            webhookSentTo TEXT
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idxContentHash ON clips(contentHash)")
    return connection


def addClip(content, contentHash, sourceWindow, webhookSentTo=None):
    connection = connect()
    existing = connection.execute(
        "SELECT id FROM clips WHERE contentHash = ? ORDER BY id DESC LIMIT 1", (contentHash,)
    ).fetchone()
    if existing:
        connection.execute(
            "UPDATE clips SET sourceWindow = ?, createdAt = ?, webhookSentTo = ? WHERE id = ?",
            (sourceWindow, time.time(), webhookSentTo, existing[0]),
        )
    else:
        connection.execute(
            "INSERT INTO clips (content, contentHash, sourceWindow, createdAt, pinned, webhookSentTo) VALUES (?, ?, ?, ?, 0, ?)",
            (content, contentHash, sourceWindow, time.time(), webhookSentTo),
        )
    connection.commit()
    connection.close()


def trimHistory(maxHistory):
    connection = connect()
    connection.execute(
        """
        DELETE FROM clips WHERE id IN (
            SELECT id FROM clips WHERE pinned = 0
            ORDER BY createdAt DESC LIMIT -1 OFFSET ?
        )
        """,
        (maxHistory,),
    )
    connection.commit()
    connection.close()


def listClips(limit=50, search=None):
    connection = connect()
    if search:
        rows = connection.execute(
            "SELECT id, content, sourceWindow, createdAt, pinned FROM clips WHERE content LIKE ? ORDER BY createdAt DESC LIMIT ?",
            (f"%{search}%", limit),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id, content, sourceWindow, createdAt, pinned FROM clips ORDER BY createdAt DESC LIMIT ?",
            (limit,),
        ).fetchall()
    connection.close()
    return rows


def getClip(clipId):
    connection = connect()
    row = connection.execute("SELECT id, content, sourceWindow, createdAt, pinned FROM clips WHERE id = ?", (clipId,)).fetchone()
    connection.close()
    return row


def setPinned(clipId, pinned):
    connection = connect()
    connection.execute("UPDATE clips SET pinned = ? WHERE id = ?", (1 if pinned else 0, clipId))
    connection.commit()
    connection.close()


def deleteClip(clipId):
    connection = connect()
    connection.execute("DELETE FROM clips WHERE id = ?", (clipId,))
    connection.commit()
    connection.close()


def clearHistory(keepPinned=True):
    connection = connect()
    if keepPinned:
        connection.execute("DELETE FROM clips WHERE pinned = 0")
    else:
        connection.execute("DELETE FROM clips")
    connection.commit()
    connection.close()
