import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from res.config import load_last_choice, save_last_choice


class TestConfigRoundTrip(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            save_last_choice(path, "8BitDo Ultimate Wireless / Pro 2 Wired Controller")
            self.assertEqual(
                load_last_choice(path), "8BitDo Ultimate Wireless / Pro 2 Wired Controller"
            )

    def test_load_missing_file_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "does-not-exist.json"
            self.assertIsNone(load_last_choice(path))

    def test_load_malformed_json_returns_none(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{not valid json")
            self.assertIsNone(load_last_choice(path))

    def test_save_creates_parent_directories(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "dir" / "config.json"
            save_last_choice(path, "some controller")
            self.assertTrue(path.exists())
            self.assertEqual(load_last_choice(path), "some controller")

    def test_save_overwrites_previous_choice(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            save_last_choice(path, "first")
            save_last_choice(path, "second")
            self.assertEqual(load_last_choice(path), "second")


if __name__ == "__main__":
    unittest.main()
