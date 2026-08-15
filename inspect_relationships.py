import sqlite3

c = sqlite3.connect(r"storage\library.db")

print("\n=== VIDEOS ===")
for row in c.execute("""
    SELECT
        vs.id,
        vs.script_id,
        vs.site,
        vs.video_id,
        vs.is_primary,
        vs.url
    FROM video_sources vs
    ORDER BY vs.script_id, vs.id
"):
    print(row)

print("\n=== THREADS ===")
for row in c.execute("""
    SELECT
        et.id,
        et.script_id,
        et.url
    FROM eroscripts_threads et
    ORDER BY et.script_id, et.id
"""):
    print(row)

c.close()
