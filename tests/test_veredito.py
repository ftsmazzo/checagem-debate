import unittest

from app.factcheck import parse_json, sanitize_verdict
from app.listener import assert_youtube


class VerdictTests(unittest.TestCase):
    def test_sem_fonte_nao_contradiz(self):
        verdict = sanitize_verdict(
            {"status": "contradito", "confidence": 0.9, "summary": "não achei", "sources": []}
        )
        self.assertEqual(verdict["status"], "sem_evidencia")

    def test_fonte_https_permanece(self):
        verdict = sanitize_verdict(
            {
                "status": "sustentado",
                "confidence": 2,
                "sources": [{"url": "https://www.ibge.gov.br/x", "title": "IBGE", "note": "tabela"}],
            }
        )
        self.assertEqual(verdict["status"], "sustentado")
        self.assertEqual(verdict["confidence"], 1.0)
        self.assertEqual(verdict["sources"][0]["title"], "IBGE")

    def test_http_nao_conta(self):
        verdict = sanitize_verdict(
            {"status": "exagerado", "sources": [{"url": "http://example.com"}]}
        )
        self.assertEqual(verdict["status"], "sem_evidencia")

    def test_json_com_cerca(self):
        self.assertEqual(parse_json('```json\n{"claims":[]}\n```')["claims"], [])

    def test_so_aceita_youtube(self):
        self.assertIn("youtube.com", assert_youtube("https://www.youtube.com/watch?v=Gqc1rQtzWUk"))
        with self.assertRaises(ValueError):
            assert_youtube("https://evil.example/audio")


if __name__ == "__main__":
    unittest.main()
