import unittest

from app.factcheck import attach_citations, citation_sources, parse_json, sanitize_verdict
from app.listener import explain_audio_error, resolve_stream, youtube_cookie_text


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
        self.assertEqual(verdict["confidence"], 0.65)
        self.assertEqual(verdict["sources"][0]["title"], "IBGE")

    def test_http_nao_conta(self):
        verdict = sanitize_verdict(
            {"status": "exagerado", "sources": [{"url": "http://example.com"}]}
        )
        self.assertEqual(verdict["status"], "sem_evidencia")

    def test_citacao_da_busca_entra_como_fonte(self):
        payload = {
            "citations": ["https://www.ibge.gov.br/tabela"],
            "choices": [
                {
                    "message": {
                        "annotations": [
                            {"url_citation": {"url": "https://www.gov.br/inep/nota"}}
                        ]
                    }
                }
            ],
        }
        verdict = sanitize_verdict(
            attach_citations(
                {"status": "sustentado", "confidence": 0.7, "sources": []},
                citation_sources(payload),
            )
        )
        self.assertEqual(verdict["status"], "sustentado")
        self.assertEqual(len(verdict["sources"]), 2)

    def test_json_com_cerca(self):
        self.assertEqual(parse_json('```json\n{"claims":[]}\n```')["claims"], [])

    def test_erro_de_robo_sem_cookie(self):
        message = explain_audio_error("Sign in to confirm you're not a bot")
        self.assertIn("BandNews FM SP", message)

    def test_erro_de_robo_com_cookie(self):
        message = explain_audio_error("Sign in to confirm you're not a bot", has_cookies=True)
        self.assertIn("BandNews FM SP", message)

    def test_filtra_so_youtube(self):
        raw = "\n".join(
            [
                "# Netscape HTTP Cookie File",
                ".paypal.com\tTRUE\t/\tTRUE\t1\tsegredo\tabc",
                ".youtube.com\tTRUE\t/\tTRUE\t1\tLOGIN_INFO\tabc",
            ]
        )
        kept = youtube_cookie_text(raw)
        self.assertIn("youtube.com", kept)
        self.assertNotIn("paypal.com", kept)

    def test_aceita_quebra_escapada(self):
        raw = ".youtube.com\\tTRUE\\t/\\tTRUE\\t1\\tPREF\\tok\\n.google.com\\tTRUE\\t/\\tTRUE\\t1\\tSID\\tok"
        kept = youtube_cookie_text(raw)
        self.assertIn("PREF", kept)
        self.assertNotIn("google.com", kept)

    def test_aceita_bandnews_e_youtube(self):
        self.assertIn("BANDNEWSFM", resolve_stream("bandnews_sp"))
        self.assertIn("youtube.com", resolve_stream("https://www.youtube.com/watch?v=Gqc1rQtzWUk"))
        with self.assertRaises(ValueError):
            resolve_stream("https://evil.example/audio")


if __name__ == "__main__":
    unittest.main()
