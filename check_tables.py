import sqlite3

c = sqlite3.connect(r"storage\library.db")

rows = c.execute(
    "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
).fetchall()

print(rows)

c.close()
