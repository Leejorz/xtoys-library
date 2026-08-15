import sqlite3

connection = sqlite3.connect(
    r"storage\library.db"
)

clean_url = "https://discuss.eroscripts.com/t/gee-marie-rose-special-doa/58563"

cursor = connection.cursor()

cursor.execute(
    "UPDATE scripts SET eroscripts_url = ? WHERE id = 1",
    (clean_url,)
)

cursor.execute(
    "UPDATE eroscripts_threads SET thread_url = ? WHERE script_id = 1",
    (clean_url,)
)

connection.commit()

print("Scripts URL:")
print(
    cursor.execute(
        "SELECT eroscripts_url FROM scripts WHERE id = 1"
    ).fetchone()[0]
)

print()
print("Thread URL:")
print(
    cursor.execute(
        "SELECT thread_url FROM eroscripts_threads WHERE script_id = 1"
    ).fetchone()[0]
)

connection.close()