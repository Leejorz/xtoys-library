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

if __name__ == "__main__":
    unittest.main()
