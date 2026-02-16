import datetime as dt
import importlib
import os
import tempfile
import unittest


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = os.path.join(self.tmp.name, "test.db")
        os.environ["ADMIN_TOKEN"] = "changeme"
        import app

        self.app = importlib.reload(app)
        self.app.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_daily_target_deterministic(self):
        day = dt.date(2025, 1, 1)
        target1 = self.app.daily_target(self.app.WORDS, day)
        target2 = self.app.daily_target(self.app.WORDS, day)
        self.assertEqual(target1, target2)

    def test_similarity_exact_word(self):
        self.assertEqual(self.app.similarity_score("chat", "chat"), 100)

    def test_stats_after_save_guess(self):
        self.app.save_guess("bob", "chat", 42, "chien", False)
        stats = self.app.admin_stats()
        self.assertGreaterEqual(stats["total_guesses"], 1)
        self.assertEqual(stats["top_players"][0]["player"], "bob")


if __name__ == "__main__":
    unittest.main()
