import datetime
import sqlite3
import urllib.parse

PROTOCOL_FILE = "file://"

def banshee_get_songs(db):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    c = conn.cursor()

    for song in c.execute("SELECT `Uri`, `DateAddedStamp` FROM `CoreTracks`"):
        uri = song["Uri"]
        date_added = datetime.datetime.fromtimestamp(song["DateAddedStamp"])

        if not uri.startswith(PROTOCOL_FILE):
            continue

        path = urllib.parse.unquote(uri[len(PROTOCOL_FILE):])
        yield {"path": path, "date_added": date_added}
