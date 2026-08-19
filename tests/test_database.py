import tempfile
import unittest
from pathlib import Path
from storage.database import Database

class DatabaseTests(unittest.TestCase):
    def test_database_initializes(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "library.db")
            db.initialize()
            row = db.connect().execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='scripts'"
            ).fetchone()
            db.close()
            self.assertIsNotNone(row)

    def test_add_script_inserts_four_columns_with_four_values(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "library.db")
            db.initialize()
            db.add_script("example.funscript", "abc123")
            row = db.connect().execute(
                "SELECT filename, content_hash FROM scripts WHERE content_hash=?",
                ("abc123",),
            ).fetchone()
            db.close()
            self.assertIsNotNone(row)
            self.assertEqual(row["filename"], "example.funscript")

if __name__ == "__main__":
    unittest.main()
