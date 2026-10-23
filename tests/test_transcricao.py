import unittest
from datetime import datetime, timedelta

from app.transcript import group_turns


class GroupTurnsTests(unittest.TestCase):
    def test_junta_picados_proximos(self):
        start = datetime(2026, 10, 18, 21, 0, 0)
        rows = [
            {"id": 1, "text": "O governo entregou creches.", "created_at": start},
            {"id": 2, "text": "Foram mais de mil unidades.", "created_at": start + timedelta(seconds=12)},
            {"id": 3, "text": "Outro assunto começa aqui.", "created_at": start + timedelta(seconds=50)},
        ]
        turns = group_turns(rows, gap_seconds=18, max_chars=520)
        self.assertEqual(len(turns), 2)
        self.assertIn("creches", turns[0]["text"])
        self.assertIn("mil unidades", turns[0]["text"])
        self.assertEqual(turns[0]["parts"], 2)
        self.assertEqual(turns[1]["parts"], 1)

    def test_corta_fala_longa(self):
        start = datetime(2026, 10, 18, 21, 0, 0)
        rows = [
            {"id": i, "text": "frase " * 40, "created_at": start + timedelta(seconds=i)}
            for i in range(1, 5)
        ]
        turns = group_turns(rows, gap_seconds=18, max_chars=200)
        self.assertGreater(len(turns), 1)


if __name__ == "__main__":
    unittest.main()
